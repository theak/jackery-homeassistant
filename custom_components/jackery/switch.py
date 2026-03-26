"""Switch platform for Jackery."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, SWITCH_DESCRIPTIONS
from .entity_helpers import JackeryControllableEntity
from .features import supported_keys_for_platform


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jackery switches."""
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
        supported_keys = set(supported_keys_for_platform(coordinator.data, "switch"))
        for description in SWITCH_DESCRIPTIONS:
            if description.key not in supported_keys:
                continue
            entities.append(JackerySwitch(coordinator, api, description, device))

    async_add_entities(entities)


class JackerySwitch(JackeryControllableEntity, SwitchEntity):
    """A Jackery switch entity."""

    entity_description: SwitchEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api,
        description: SwitchEntityDescription,
        device: dict,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, api, description.key, device)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the current switch state."""
        value = self.property_value
        if value is None:
            return None
        return value == 1

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.async_set_jackery_value("on")

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.async_set_jackery_value("off")
