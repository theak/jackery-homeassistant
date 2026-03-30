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
from .entity_helpers import JackeryCoordinatorEntity
from .features import supported_keys_for_platform


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
            supported_keys = set(
                supported_keys_for_platform(coordinator.data, "binary_sensor")
            )
            for description in BINARY_SENSOR_DESCRIPTIONS:
                if description.key not in supported_keys:
                    continue
                entities.append(JackeryBinarySensor(coordinator, description, device))

    async_add_entities(entities)


class JackeryBinarySensor(JackeryCoordinatorEntity, BinarySensorEntity):
    """Implementation of a Jackery binary sensor."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: BinarySensorEntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key, device_info)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        value = self.property_value
        if value is None:
            return None
        return value == 1
