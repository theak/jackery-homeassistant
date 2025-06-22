"""Sensor platform for Jackery."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, SENSOR_DESCRIPTIONS, JackerySensorEntityDescription


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Jackery sensor entities."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: dict[str, DataUpdateCoordinator] = entry_data["coordinators"]
    devices: list[dict] = entry_data["devices"]

    entities = []
    for device in devices:
        device_id = device["devId"]
        if device_id in coordinators:
            coordinator = coordinators[device_id]
            # Create entities for all sensor descriptions
            for description in SENSOR_DESCRIPTIONS:
                entities.append(JackerySensor(coordinator, description, device))

    async_add_entities(entities)


class JackerySensor(CoordinatorEntity, SensorEntity):
    """Implementation of a Jackery sensor."""

    entity_description: JackerySensorEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: JackerySensorEntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> str | int | float | None:
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        if self.entity_description.value:
            return self.entity_description.value(value)
        return value
