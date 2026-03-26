"""Number platform for Jackery."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, NUMBER_DESCRIPTIONS
from .entity_helpers import JackeryControllableEntity
from .features import supported_keys_for_platform


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jackery numbers."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators: dict[str, DataUpdateCoordinator] = entry_data["coordinators"]
    devices: list[dict] = entry_data["devices"]
    api = entry_data["api"]

    entities = []
    for device in devices:
        device_id = device["devId"]
        if device_id not in coordinators:
            continue
        coordinator = coordinators[device_id]
        supported_keys = set(supported_keys_for_platform(coordinator.data, "number"))
        for description in NUMBER_DESCRIPTIONS:
            if description.key not in supported_keys:
                continue
            entities.append(JackeryNumber(coordinator, api, description, device))

    async_add_entities(entities)


class JackeryNumber(JackeryControllableEntity, NumberEntity):
    """A Jackery number entity."""

    entity_description: NumberEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api,
        description: NumberEntityDescription,
        device: dict,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, api, description.key, device)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the current numeric value."""
        value = self.property_value
        if value is None:
            return None
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Set a numeric Jackery property."""
        await self.async_set_jackery_value(int(value))
