"""Select platform for Jackery."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, JackerySelectEntityDescription, SELECT_DESCRIPTIONS
from .entity_helpers import JackeryControllableEntity
from .features import supported_keys_for_platform


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jackery selects."""
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
        supported_keys = set(supported_keys_for_platform(coordinator.data, "select"))
        for description in SELECT_DESCRIPTIONS:
            if description.key not in supported_keys:
                continue
            entities.append(JackerySelect(coordinator, api, description, device))

    async_add_entities(entities)


class JackerySelect(JackeryControllableEntity, SelectEntity):
    """A Jackery select entity."""

    entity_description: JackerySelectEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api,
        description: JackerySelectEntityDescription,
        device: dict,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator, api, description.key, device)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        value = self.property_value
        if value is None:
            return None
        try:
            return self.entity_description.options[int(value)]
        except (IndexError, TypeError, ValueError):
            return None

    async def async_select_option(self, option: str) -> None:
        """Select a Jackery option."""
        await self.async_set_jackery_value(option)
