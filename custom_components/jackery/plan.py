"""Scheduled plan entities for Jackery Transfer Switch.

Plan data is fetched by the coordinator (via MQTT QueryElectricityStrategy)
and stored in ``coordinator.data["_plans"]`` alongside regular HTTP properties.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time as dt_time

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import JackeryAPI
from .const import DOMAIN
from .protocol import CloudOnlineAvailabilityMixin

_LOGGER = logging.getLogger(__name__)

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

DAY_MASK_LABELS: dict[str, str] = {
    "1111111": "Daily",
    "1111100": "Weekdays",
    "0000011": "Weekends",
}


def _format_day_mask(mask: str) -> str:
    """Convert a 7-char binary day mask to a human-readable label."""
    if mask in DAY_MASK_LABELS:
        return DAY_MASK_LABELS[mask]
    days = [DAY_NAMES[i] for i, c in enumerate(mask) if c == "1"]
    return ", ".join(days) if days else "Never"


def _plan_display_name(plan: dict) -> str:
    """Build a display name like 'Discharge 14:00-19:00 Weekdays'."""
    tt = plan.get("tt", 0)
    task_type = "Charge" if tt == 1 else "Discharge" if tt == 2 else f"Type {tt}"
    st = plan.get("st", "??:??")
    et = plan.get("et", "??:??")
    days = _format_day_mask(plan.get("lps", "0000000"))
    return f"{task_type} {st}\u2013{et} {days}"


def _get_plans(coordinator: DataUpdateCoordinator) -> list[dict]:
    """Read plans from coordinator data, returning [] if absent."""
    data = coordinator.data
    if not isinstance(data, dict):
        return []
    return data.get("_plans") or []


def _find_plan(coordinator: DataUpdateCoordinator, pid: str) -> dict | None:
    """Find a specific plan by pid in coordinator data."""
    for plan in _get_plans(coordinator):
        if plan.get("pid") == pid:
            return plan
    return None


def _active_plan(plans: list[dict]) -> dict | None:
    """Return the plan currently executing based on day and time, or None."""
    now = datetime.now()
    day_index = now.weekday()
    current_time = now.time()
    for plan in plans:
        if plan.get("sw") != 1:
            continue
        mask = plan.get("lps", "0000000")
        if len(mask) != 7 or mask[day_index] != "1":
            continue
        try:
            st = dt_time.fromisoformat(plan["st"])
            et = dt_time.fromisoformat(plan["et"])
        except (KeyError, ValueError):
            continue
        if st <= current_time <= et:
            return plan
    return None


def has_plans(coordinator: DataUpdateCoordinator) -> bool:
    """Return True if coordinator data contains plan data."""
    data = coordinator.data
    return isinstance(data, dict) and "_plans" in data


def _device_info(device: dict) -> DeviceInfo:
    """Build DeviceInfo from the device dict."""
    dev_id = device["devId"]
    return DeviceInfo(
        identifiers={(DOMAIN, dev_id)},
        name=device.get("devName", f"Jackery Device {dev_id}"),
        manufacturer="Jackery",
        model=device.get("productType"),
    )


class JackeryPlanSensor(CloudOnlineAvailabilityMixin, CoordinatorEntity, SensorEntity):
    """Sensor showing plan overview for the Transfer Switch."""

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        device_info: dict,
    ) -> None:
        """Initialize the plan sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_info['devId']}_plan_overview"
        self._attr_name = "Scheduled Plans"
        self._attr_icon = "mdi:calendar-clock"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = _device_info(device_info)

    @property
    def native_value(self) -> str:
        """Return plan summary string."""
        plans = _get_plans(self.coordinator)
        if not plans:
            return "No plans"
        active = sum(1 for p in plans if p.get("sw") == 1)
        total = len(plans)
        if active == 0:
            return f"{total} plan{'s' if total != 1 else ''} (all disabled)"
        return f"{active}/{total} active"

    @property
    def extra_state_attributes(self) -> dict:
        """Return all plans as attributes."""
        plans = _get_plans(self.coordinator)
        attrs: dict[str, object] = {}
        for i, plan in enumerate(plans):
            prefix = f"plan_{i + 1}"
            attrs[f"{prefix}_name"] = _plan_display_name(plan)
            attrs[f"{prefix}_enabled"] = plan.get("sw") == 1
            attrs[f"{prefix}_type"] = (
                "Charge" if plan.get("tt") == 1 else "Discharge"
            )
            attrs[f"{prefix}_start"] = plan.get("st", "")
            attrs[f"{prefix}_end"] = plan.get("et", "")
            attrs[f"{prefix}_days"] = _format_day_mask(plan.get("lps", "0000000"))
            attrs[f"{prefix}_day_mask"] = plan.get("lps", "0000000")
            attrs[f"{prefix}_pid"] = plan.get("pid", "")
        attrs["plan_count"] = len(plans)
        return attrs


class JackeryActivePlanSensor(CloudOnlineAvailabilityMixin, CoordinatorEntity, SensorEntity):
    """Sensor showing the currently executing plan, if any."""

    def __init__(self, coordinator: DataUpdateCoordinator, device_info: dict) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{device_info['devId']}_active_plan"
        self._attr_name = "Active Plan"
        self._attr_icon = "mdi:calendar-check"
        self._attr_entity_category = None
        self._attr_device_info = _device_info(device_info)

    @property
    def native_value(self) -> str:
        plan = _active_plan(_get_plans(self.coordinator))
        return _plan_display_name(plan) if plan else "Idle"

    @property
    def extra_state_attributes(self) -> dict:
        plan = _active_plan(_get_plans(self.coordinator))
        if not plan:
            return {"active": False}
        return {
            "active": True,
            "type": "Charge" if plan.get("tt") == 1 else "Discharge",
            "start_time": plan.get("st", ""),
            "end_time": plan.get("et", ""),
        }


class JackeryPlanSwitch(CloudOnlineAvailabilityMixin, CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable a single scheduled plan."""

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        device_info: dict,
        pid: str,
    ) -> None:
        """Initialize the plan switch."""
        super().__init__(coordinator)
        self._api = api
        self._pid = pid
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._attr_unique_id = f"{self._device_id}_plan_{pid}"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = _device_info(device_info)
        # Set initial name from current plan data so HA caches a good name
        plan = _find_plan(coordinator, pid)
        self._attr_name = _plan_display_name(plan) if plan else f"Plan {pid}"

    @property
    def _plan(self) -> dict:
        """Resolve current plan data from coordinator."""
        return _find_plan(self.coordinator, self._pid) or {}

    @property
    def name(self) -> str:
        """Return display name derived from current plan data."""
        plan = self._plan
        if plan:
            return _plan_display_name(plan)
        # Fall back to the cached name set in __init__, not the pid
        return self._attr_name

    @property
    def icon(self) -> str:
        """Return icon based on plan type."""
        return (
            "mdi:battery-charging"
            if self._plan.get("tt") == 1
            else "mdi:battery-arrow-down"
        )

    @property
    def is_on(self) -> bool:
        """Return whether the plan is enabled."""
        return self._plan.get("sw") == 1

    @property
    def extra_state_attributes(self) -> dict:
        """Return plan details as attributes."""
        plan = self._plan
        return {
            "plan_id": plan.get("pid", ""),
            "type": "Charge" if plan.get("tt") == 1 else "Discharge",
            "start_time": plan.get("st", ""),
            "end_time": plan.get("et", ""),
            "days": _format_day_mask(plan.get("lps", "0000000")),
        }

    async def async_turn_on(self, **kwargs) -> None:
        """Enable the plan."""
        await self._async_toggle(1)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the plan."""
        await self._async_toggle(0)

    async def _async_toggle(self, sw: int) -> None:
        """Update the plan's enabled state on the device."""
        plan = self._plan
        if not plan:
            raise HomeAssistantError(f"Plan {self._pid} not found in device data")

        updated_plan = dict(plan)
        updated_plan["sw"] = sw

        try:
            await self._api.async_update_transfer_switch_plan(
                self._device_id,
                self._device_sn,
                updated_plan,
            )
        except asyncio.CancelledError:
            raise
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to toggle plan: {err}"
            ) from err

        # Optimistic update: patch coordinator data in place
        for p in _get_plans(self.coordinator):
            if p.get("pid") == self._pid:
                p["sw"] = sw
                break
        self.coordinator.async_set_updated_data(self.coordinator.data)
