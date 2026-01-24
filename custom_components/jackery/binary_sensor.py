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
    for device in devices:
        device_id = device["devId"]
        if device_id in coordinators:
            coordinator = coordinators[device_id]
            # Create entities for all binary sensor descriptions
            for description in BINARY_SENSOR_DESCRIPTIONS:
                entities.append(JackeryBinarySensor(coordinator, description, device))

    async_add_entities(entities)


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
