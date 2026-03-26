"""Sensor platform for Jackery."""

from __future__ import annotations

from datetime import datetime

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
from .entity_helpers import JackeryCoordinatorEntity
from .features import supported_keys_for_platform


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
            supported_keys = set(supported_keys_for_platform(coordinator.data, "sensor"))
            for description in SENSOR_DESCRIPTIONS:
                if description.key not in supported_keys:
                    continue
                entities.append(JackerySensor(coordinator, description, device))

    async_add_entities(entities)


class JackerySensor(JackeryCoordinatorEntity, SensorEntity):
    """Implementation of a Jackery sensor."""

    entity_description: JackerySensorEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: JackerySensorEntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key, device_info)
        self.entity_description = description

    @property
    def native_value(self) -> str | int | float | datetime | None:
        """Return the state of the sensor."""
        value = self.property_value
        if value is None:
            return None
        if self.entity_description.value:
            return self.entity_description.value(value)
        return value
