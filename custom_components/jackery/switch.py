"""Switch platform for Jackery."""

from __future__ import annotations

import asyncio

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .api import JackeryAPI
from .const import DOMAIN
from .protocol import control_spec, supported_keys

SWITCH_KEYS = ("oac", "odc", "odcu", "odcc", "sfc")
SWITCH_DESCRIPTIONS: dict[str, EntityDescription] = {
    key: EntityDescription(
        key=spec.key,
        name=spec.name,
        icon=spec.icon,
    )
    for key in SWITCH_KEYS
    for spec in (control_spec(key),)
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jackery switch entities."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    api: JackeryAPI = entry_data["api"]
    coordinators: dict[str, DataUpdateCoordinator] = entry_data["coordinators"]
    devices: list[dict] = entry_data["devices"]

    entities = []
    for device in devices:
        device_id = device["devId"]
        coordinator = coordinators.get(device_id)
        device_sn = device.get("devSn")
        if coordinator is None or not device_sn:
            continue

        for key in supported_keys(coordinator.data, SWITCH_KEYS):
            entities.append(
                JackerySwitchEntity(
                    api=api,
                    coordinator=coordinator,
                    description=SWITCH_DESCRIPTIONS[key],
                    device_info=device,
                )
            )

    async_add_entities(entities)


class JackerySwitchEntity(CoordinatorEntity, SwitchEntity):
    """Implementation of a Jackery switch."""

    entity_description: EntityDescription

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        description: EntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._slug = control_spec(description.key).slug
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._attr_unique_id = f"{self._device_id}_switch_{description.key}"
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_info.get("devName", f"Jackery Device {self._device_id}"),
            manufacturer="Jackery",
            model=device_info.get("productType"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the switch is on."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return value == 1

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the device setting on."""
        await self._async_set_value("on", 1)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device setting off."""
        await self._async_set_value("off", 0)

    async def _async_set_value(self, value: str, raw_state: int) -> None:
        """Set the underlying Jackery property."""
        try:
            await self._api.async_set_device_property(
                self._device_id,
                self._device_sn,
                self._slug,
                value,
            )
        except asyncio.CancelledError:
            raise
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.name}: {err}"
            ) from err

        updated_data = dict(self.coordinator.data or {})
        updated_data[self.entity_description.key] = raw_state
        self.coordinator.async_set_updated_data(updated_data)
        await self.coordinator.async_request_refresh()
