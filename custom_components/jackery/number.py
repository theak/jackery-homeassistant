"""Number platform for Jackery."""

from __future__ import annotations

import asyncio

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .api import JackeryAPI
from .const import DOMAIN
from .protocol import control_spec, supported_keys

NUMBER_KEYS = ("ast", "pm", "sltb")
NUMBER_DESCRIPTIONS: dict[str, EntityDescription] = {
    key: EntityDescription(
        key=spec.key,
        name=spec.name,
        icon=spec.icon,
    )
    for key in NUMBER_KEYS
    for spec in (control_spec(key),)
}
NUMBER_RANGES: dict[str, tuple[float, float, float]] = {
    key: (0, 1440, 1) for key in NUMBER_KEYS
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jackery number entities."""
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

        for key in supported_keys(coordinator.data, NUMBER_KEYS):
            entities.append(
                JackeryNumberEntity(
                    api=api,
                    coordinator=coordinator,
                    description=NUMBER_DESCRIPTIONS[key],
                    device_info=device,
                )
            )

    async_add_entities(entities)


class JackeryNumberEntity(CoordinatorEntity, NumberEntity):
    """Implementation of a Jackery number."""

    entity_description: EntityDescription

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        description: EntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._slug = control_spec(description.key).slug
        min_value, max_value, step = NUMBER_RANGES[description.key]
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._attr_unique_id = f"{self._device_id}_{description.key}"
        self._attr_icon = description.icon
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_info.get("devName", f"Jackery Device {self._device_id}"),
            manufacturer="Jackery",
            model=device_info.get("productType"),
        )

    @property
    def name(self) -> str:
        """Return the entity name."""
        return self.entity_description.name

    @property
    def native_value(self) -> float | None:
        """Return the current numeric value."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None and self.entity_description.key == "sltb":
            value = self.coordinator.data.get("slt")
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set a new numeric value."""
        int_value = int(value)

        try:
            await self._api.async_set_device_property(
                self._device_id,
                self._device_sn,
                self._slug,
                int_value,
            )
        except asyncio.CancelledError:
            raise
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.name}: {err}"
            ) from err

        updated_data = dict(self.coordinator.data or {})
        updated_data[self.entity_description.key] = int_value
        self.coordinator.async_set_updated_data(updated_data)
        await self.coordinator.async_request_refresh()
