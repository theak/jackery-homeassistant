"""Binary sensor platform for Jackery."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, BINARY_SENSOR_DESCRIPTIONS
from .protocol import is_supported_property


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Jackery binary sensor entities."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: dict[str, DataUpdateCoordinator] = entry_data["coordinators"]
    devices: list[dict] = entry_data["devices"]

    entities = []
    registered_keys_by_device: dict[str, set[str]] = {}
    for device in devices:
        device_id = device["devId"]
        if device_id in coordinators:
            coordinator = coordinators[device_id]
            registered_keys = registered_keys_by_device.setdefault(device_id, set())
            # Create entities for all binary sensor descriptions
            for description in BINARY_SENSOR_DESCRIPTIONS:
                if is_supported_property(coordinator.data, description.key):
                    registered_keys.add(description.key)
                    entities.append(
                        JackeryBinarySensor(coordinator, description, device)
                    )

    async_add_entities(entities)

    def _build_binary_sensor_listener(
        device_info: dict,
        device_coordinator: DataUpdateCoordinator,
        registered_keys: set[str],
    ):
        def _async_add_supported_binary_sensors() -> None:
            new_entities = []
            for description in BINARY_SENSOR_DESCRIPTIONS:
                if description.key in registered_keys:
                    continue
                if not is_supported_property(device_coordinator.data, description.key):
                    continue

                registered_keys.add(description.key)
                new_entities.append(
                    JackeryBinarySensor(device_coordinator, description, device_info)
                )

            if new_entities:
                async_add_entities(new_entities)

        return _async_add_supported_binary_sensors

    for device in devices:
        device_id = device["devId"]
        coordinator = coordinators.get(device_id)
        if coordinator is None:
            continue

        registered_keys = registered_keys_by_device.setdefault(device_id, set())
        unsubscribe = coordinator.async_add_listener(
            _build_binary_sensor_listener(device, coordinator, registered_keys)
        )
        if hasattr(config_entry, "async_on_unload"):
            config_entry.async_on_unload(unsubscribe)


class JackeryBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Implementation of a Jackery binary sensor."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: BinarySensorEntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_info["devId"]

        # Set a unique ID for this entity
        self._attr_unique_id = f"{self._device_id}_{description.key}"

        # Set the device info for this entity
        # This groups all sensors under a single device in Home Assistant
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": device_info.get("devName", f"Jackery Device {self._device_id}"),
            "manufacturer": "Jackery",
            "model": device_info.get("productType"),
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on.
        
        Different Jackery models emit different DC output parameters:
        - odc: DC Output (models with combined USB + Car toggle)
        - odcc: DC Car Output (models with separate toggles)
        - odcu: USB Output (models with separate toggles)
        """
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return value == 1
