"""Text platform for Jackery."""

from __future__ import annotations

import asyncio

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import JackeryAPI
from .const import CHARGING_PLAN_DATA, DOMAIN
from .protocol import (
    compose_charging_plan,
    has_charging_plan_data_support,
    parse_charging_plan,
)

CHARGING_PLAN_TIME_DESCRIPTION = EntityDescription(
    key=CHARGING_PLAN_DATA,
    name="Charging Plan Time",
    icon="mdi:clock-outline",
)
CHARGING_PLAN_TIME_PATTERN = (
    r"^(?:[01]\d|2[0-3]):[0-5]\d-(?:[01]\d|2[0-3]):[0-5]\d$"
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jackery text entities."""
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

        if has_charging_plan_data_support(coordinator.data):
            entities.append(
                JackeryChargingPlanTimeEntity(
                    api=api,
                    coordinator=coordinator,
                    description=CHARGING_PLAN_TIME_DESCRIPTION,
                    device_info=device,
                )
            )

    async_add_entities(entities)

    def _build_charging_plan_listener(
        device_info: dict,
        device_coordinator: DataUpdateCoordinator,
    ):
        entity_added = False

        def _async_add_charging_plan_entity() -> None:
            nonlocal entity_added
            if entity_added or not has_charging_plan_data_support(
                device_coordinator.data
            ):
                return

            entity_added = True
            async_add_entities(
                [
                    JackeryChargingPlanTimeEntity(
                        api=api,
                        coordinator=device_coordinator,
                        description=CHARGING_PLAN_TIME_DESCRIPTION,
                        device_info=device_info,
                    )
                ]
            )

        return _async_add_charging_plan_entity

    for device in devices:
        device_id = device["devId"]
        coordinator = coordinators.get(device_id)
        device_sn = device.get("devSn")
        if coordinator is None or not device_sn:
            continue

        if has_charging_plan_data_support(coordinator.data):
            continue

        unsubscribe = coordinator.async_add_listener(
            _build_charging_plan_listener(device, coordinator)
        )
        if hasattr(config_entry, "async_on_unload"):
            config_entry.async_on_unload(unsubscribe)


class JackeryChargingPlanTimeEntity(CoordinatorEntity, TextEntity):
    """Text entity for the charging-plan time-range segment."""

    entity_description: EntityDescription

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        description: EntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the charging-plan time entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._attr_unique_id = f"{self._device_id}_charging_plan_time"
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_mode = TextMode.TEXT
        self._attr_pattern = CHARGING_PLAN_TIME_PATTERN
        self._attr_native_min = 11
        self._attr_native_max = 11
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_info.get("devName", f"Jackery Device {self._device_id}"),
            manufacturer="Jackery",
            model=device_info.get("productType"),
        )

    @property
    def available(self) -> bool:
        """Return whether the time entity is currently usable."""
        try:
            parent_available = super().available
        except AttributeError:
            parent_available = True
        return (
            parent_available
            and has_charging_plan_data_support(self.coordinator.data)
            and self._parsed_value() is not None
        )

    @property
    def native_value(self) -> str | None:
        """Return the current time-range segment."""
        parsed_value = self._parsed_value()
        if parsed_value is None:
            return None

        return parsed_value[0]

    async def async_set_value(self, value: str) -> None:
        """Update only the time-range segment of the charging-plan payload."""
        parsed_value = self._parsed_value()
        if parsed_value is None:
            raise HomeAssistantError("Charging plan data is unavailable or malformed.")

        _time_range, repeat_mask = parsed_value
        try:
            combined_value = compose_charging_plan(value, repeat_mask)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

        try:
            await self._api.async_set_device_dp(
                self._device_id,
                self._device_sn,
                self.entity_description.key,
                combined_value,
            )
        except asyncio.CancelledError:
            raise
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.name}: {err}"
            ) from err

        updated_data = dict(self.coordinator.data or {})
        updated_data[self.entity_description.key] = combined_value
        self.coordinator.async_set_updated_data(updated_data)
        await self.coordinator.async_request_refresh()

    def _parsed_value(self) -> tuple[str, str] | None:
        """Return the parsed charging-plan payload, if valid."""
        return parse_charging_plan(self.coordinator.data.get(self.entity_description.key))
