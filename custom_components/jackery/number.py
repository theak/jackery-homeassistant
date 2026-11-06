"""Number platform for Jackery."""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal, ROUND_HALF_UP

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import JackeryAPI
from .const import DOMAIN, ENTITY_HELP_TEXT
from homeassistant.const import EntityCategory
from .protocol import (
    CloudOnlineAvailabilityMixin,
    control_spec,
    is_transfer_switch_device,
    supported_keys,
    timezone_command,
)

NUMBER_KEYS = ("ast", "pm", "sltb", "ddt", "autoDt", "cdsDt", "selfDt")

_LOGGER = logging.getLogger(__name__)

# Wait for the arrow clicks to stop before sending the UTC offset.
UTC_OFFSET_SEND_DELAY = 3

# Transfer Switch commands: key -> (action_id, cmd)
TRANSFER_SWITCH_NUMBER_COMMANDS: dict[str, tuple[int, int]] = {
    "ddt": (16, 19),
    "autoDt": (5, 7),
    "cdsDt": (5, 7),
    "selfDt": (5, 7),
}

def _number_desc(key: str, **kwargs) -> EntityDescription:
    spec = control_spec(key)
    return EntityDescription(key=spec.key, name=spec.name, icon=spec.icon, **kwargs)

NUMBER_DESCRIPTIONS: dict[str, EntityDescription] = {
    "ast": _number_desc("ast", entity_category=EntityCategory.CONFIG),
    "pm": _number_desc("pm", entity_category=EntityCategory.CONFIG),
    "sltb": _number_desc("sltb", entity_category=EntityCategory.CONFIG),
    "ddt": _number_desc("ddt", entity_category=None),
    "autoDt": _number_desc("autoDt", entity_category=EntityCategory.CONFIG),
    "cdsDt": _number_desc("cdsDt", entity_category=EntityCategory.CONFIG),
    "selfDt": _number_desc("selfDt", entity_category=EntityCategory.CONFIG),
}
NUMBER_RANGES: dict[str, tuple[float, float, float]] = {
    key: (0, 1440, 1) for key in ("ast", "pm", "sltb")
}
NUMBER_RANGES["ddt"] = (1, 90, 1)
NUMBER_RANGES["autoDt"] = (1, 90, 1)
NUMBER_RANGES["cdsDt"] = (1, 90, 1)
NUMBER_RANGES["selfDt"] = (1, 90, 1)

NUMBER_UNITS: dict[str, str | None] = {
    "ddt": "%",
    "autoDt": "%",
    "cdsDt": "%",
    "selfDt": "%",
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
    tz_follow: dict[str, bool] = entry_data.setdefault("tz_follow", {})
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

        if supported_keys(coordinator.data, ("uo",)):
            entities.append(
                JackeryUtcOffsetNumber(
                    api=api,
                    coordinator=coordinator,
                    device_info=device,
                    follow_state=tz_follow,
                )
            )

    async_add_entities(entities)


class JackeryUtcOffsetNumber(CloudOnlineAvailabilityMixin, CoordinatorEntity, NumberEntity):
    """UTC offset the device uses for its clock and schedules, in decimal hours."""

    _attr_name = "UTC Offset"
    _attr_icon = "mdi:clock-time-four-outline"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_native_min_value = -12
    _attr_native_max_value = 14
    _attr_native_step = 0.25

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        device_info: dict,
        follow_state: dict[str, bool],
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._follow_state = follow_state
        self._device = device_info
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._attr_unique_id = f"{self._device_id}_uo"
        self._pending: float | None = None
        self._cancel_send = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_info.get("devName", f"Jackery Device {self._device_id}"),
            manufacturer="Jackery",
            model=device_info.get("productType"),
        )

    @property
    def native_value(self) -> float | None:
        if self._pending is not None:
            return self._pending
        seconds = (self.coordinator.data or {}).get("uo")
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
            return None
        return seconds / 3600

    @property
    def extra_state_attributes(self) -> dict | None:
        return {"description": ENTITY_HELP_TEXT["uo"]}

    async def async_will_remove_from_hass(self) -> None:
        if self._cancel_send is not None:
            self._cancel_send()
            self._cancel_send = None

    async def async_set_native_value(self, value: float) -> None:
        """Hold the value and send it once the arrows stop being clicked."""
        if self._follow_state.get(self._device_id, False):
            raise HomeAssistantError(
                "Turn off Follow Home Assistant Timezone to set the UTC offset"
            )
        self._pending = float(value)
        self.async_write_ha_state()
        if self._cancel_send is not None:
            self._cancel_send()
        self._cancel_send = async_call_later(
            self.hass, UTC_OFFSET_SEND_DELAY, self._async_send_pending
        )

    async def _async_send_pending(self, _now) -> None:
        self._cancel_send = None
        value = self._pending
        if value is None:
            return
        if self._follow_state.get(self._device_id, False):
            self._pending = None
            self.async_write_ha_state()
            return
        action_id, body, ack_cmd = timezone_command(
            is_transfer_switch_device(self._device, self.coordinator.data),
            value,
            self.hass.config.time_zone,
        )
        try:
            ack = await self._api.async_send_device_command(
                self._device_id, self._device_sn, action_id, body, ack_cmd=ack_cmd
            )
            if ack is None:
                raise HomeAssistantError("Device did not acknowledge the change")
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.error("Failed to set UTC offset on %s: %s", self._device_sn, err)
            if self._pending == value:
                self._pending = None
            self.async_write_ha_state()
            return

        updated_data = dict(self.coordinator.data or {})
        updated_data["uo"] = body["uo"]
        # A newer click during the send keeps its own pending value.
        if self._pending == value:
            self._pending = None
        self.coordinator.async_set_updated_data(updated_data)
        await self.coordinator.async_request_refresh()


class JackeryNumberEntity(CloudOnlineAvailabilityMixin, CoordinatorEntity, NumberEntity):
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
        self._attr_name = description.name
        self._attr_icon = description.icon
        if description.entity_category is not None:
            self._attr_entity_category = description.entity_category
        unit = NUMBER_UNITS.get(description.key)
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES if unit is None else unit
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

    @property
    def extra_state_attributes(self) -> dict | None:
        text = ENTITY_HELP_TEXT.get(self.entity_description.key)
        return {"description": text} if text else None

    async def async_set_native_value(self, value: float) -> None:
        """Set a new numeric value."""
        int_value = self._normalize_value(value)
        key = self.entity_description.key

        try:
            box_cmd = TRANSFER_SWITCH_NUMBER_COMMANDS.get(key)
            if box_cmd is not None:
                action_id, cmd = box_cmd
                await self._api.async_send_device_command(
                    self._device_id,
                    self._device_sn,
                    action_id,
                    {"cmd": cmd, key: int_value},
                )
            else:
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

    def _normalize_value(self, value: float) -> int:
        """Clamp a requested value and snap it to the nearest configured step."""
        min_value = Decimal(str(self._attr_native_min_value))
        max_value = Decimal(str(self._attr_native_max_value))
        step = Decimal(str(self._attr_native_step or 1))
        requested = Decimal(str(value))
        clamped = min(max(requested, min_value), max_value)
        steps = ((clamped - min_value) / step).to_integral_value(
            rounding=ROUND_HALF_UP
        )
        normalized = min_value + (steps * step)
        normalized = min(max(normalized, min_value), max_value)
        return int(normalized)
