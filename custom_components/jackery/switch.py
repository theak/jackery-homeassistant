"""Switch platform for Jackery."""

from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .api import JackeryAPI
from .const import CHARGING_PLAN_SWITCH, DOMAIN, ENTITY_HELP_TEXT
from homeassistant.const import EVENT_CORE_CONFIG_UPDATE, EntityCategory
from .protocol import (
    CloudOnlineAvailabilityMixin,
    control_spec,
    has_charging_plan_switch_support,
    is_transfer_switch_device,
    supported_keys,
    timezone_command,
)
from .plan import JackeryPlanSwitch, _get_plans, has_plans
from .circuit import JackeryCircuitSwitch, has_circuits, _get_circuits, get_logical_circuits

_LOGGER = logging.getLogger(__name__)

# Seconds to wait before re-checking after a timezone resync.
TZ_FOLLOW_RETRY_AFTER_SUCCESS = 60
TZ_FOLLOW_RETRY_AFTER_FAILURE = 300

SWITCH_KEYS = (
    "oac",
    "odc",
    "odcu",
    "odcc",
    "sfc",
    "outPrio",
    "odcPrio",
    "dhg_recall",
    "pss",
    "ups",
    "rc",
    "wps",
)

# Transfer Switch commands: key -> (action_id, cmd)
TRANSFER_SWITCH_COMMANDS: dict[str, tuple[int, int]] = {
    "pss": (4, 4),
    "ups": (6, 6),
    "rc": (3, 5),
    "wps": (22, 26),
}

def _switch_desc(key: str, **kwargs) -> EntityDescription:
    spec = control_spec(key)
    return EntityDescription(key=spec.key, name=spec.name, icon=spec.icon, **kwargs)

SWITCH_DESCRIPTIONS: dict[str, EntityDescription] = {
    "oac": _switch_desc("oac", entity_category=None),
    "odc": _switch_desc("odc", entity_category=None),
    "odcu": _switch_desc("odcu", entity_category=None),
    "odcc": _switch_desc("odcc", entity_category=None),
    "sfc": _switch_desc("sfc", entity_category=EntityCategory.CONFIG),
    "outPrio": _switch_desc("outPrio", entity_category=EntityCategory.CONFIG),
    "odcPrio": _switch_desc("odcPrio", entity_category=EntityCategory.CONFIG),
    "dhg_recall": _switch_desc("dhg_recall", entity_category=EntityCategory.CONFIG),
    "pss": _switch_desc("pss", entity_category=None),
    "ups": _switch_desc("ups", entity_category=None),
    "rc": _switch_desc("rc", entity_category=None),
    "wps": _switch_desc("wps", entity_category=EntityCategory.CONFIG),
}
CHARGING_PLAN_SWITCH_DESCRIPTION = EntityDescription(
    key=CHARGING_PLAN_SWITCH,
    name="Charging Plan",
    icon="mdi:calendar-clock",
    entity_category=None,
)


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
    tz_follow: dict[str, bool] = entry_data.setdefault("tz_follow", {})

    entities = []
    for device in devices:
        device_id = device["devId"]
        coordinator = coordinators.get(device_id)
        device_sn = device.get("devSn")
        if coordinator is None or not device_sn:
            continue

        if supported_keys(coordinator.data, ("uo",)):
            entities.append(
                JackeryFollowTimezoneSwitch(
                    api=api,
                    coordinator=coordinator,
                    device_info=device,
                    follow_state=tz_follow,
                )
            )

        for key in supported_keys(coordinator.data, SWITCH_KEYS):
            entities.append(
                JackerySwitchEntity(
                    api=api,
                    coordinator=coordinator,
                    description=SWITCH_DESCRIPTIONS[key],
                    device_info=device,
                )
            )
        if has_charging_plan_switch_support(coordinator.data, device):
            entities.append(
                JackeryChargingPlanSwitchEntity(
                    api=api,
                    coordinator=coordinator,
                    description=CHARGING_PLAN_SWITCH_DESCRIPTION,
                    device_info=device,
                )
            )

    # Add plan toggle switches for Transfer Switch devices
    for device in devices:
        device_id = device["devId"]
        coordinator = coordinators.get(device_id)
        if coordinator is None or not has_plans(coordinator):
            continue
        for plan in _get_plans(coordinator):
            pid = plan.get("pid")
            if pid:
                entities.append(
                    JackeryPlanSwitch(
                        api=api,
                        coordinator=coordinator,
                        device_info=device,
                        pid=pid,
                    )
                )

    # Add circuit switches for Transfer Switch devices
    for device in devices:
        device_id = device["devId"]
        coordinator = coordinators.get(device_id)
        if coordinator is None or not has_circuits(coordinator):
            continue
        for logical in get_logical_circuits(_get_circuits(coordinator)):
            entities.append(
                JackeryCircuitSwitch(
                    api=api,
                    coordinator=coordinator,
                    device_info=device,
                    logical=logical,
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
            if entity_added or not has_charging_plan_switch_support(
                device_coordinator.data,
                device_info,
            ):
                return

            entity_added = True
            async_add_entities(
                [
                    JackeryChargingPlanSwitchEntity(
                        api=api,
                        coordinator=device_coordinator,
                        description=CHARGING_PLAN_SWITCH_DESCRIPTION,
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

        if has_charging_plan_switch_support(coordinator.data, device):
            continue

        unsubscribe = coordinator.async_add_listener(
            _build_charging_plan_listener(device, coordinator)
        )
        if hasattr(config_entry, "async_on_unload"):
            config_entry.async_on_unload(unsubscribe)


class JackeryFollowTimezoneSwitch(
    CloudOnlineAvailabilityMixin, CoordinatorEntity, SwitchEntity, RestoreEntity
):
    """Keep the device's UTC offset in step with Home Assistant's (DST included)."""

    _attr_name = "Follow Home Assistant Timezone"
    _attr_icon = "mdi:map-clock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        device_info: dict,
        follow_state: dict[str, bool],
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._device_info = device_info
        self._follow_state = follow_state
        self._attr_is_on = False
        self._syncing = False
        self._retry_at = 0.0
        self._attr_unique_id = f"{self._device_id}_follow_ha_timezone"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_info.get("devName", f"Jackery Device {self._device_id}"),
            manufacturer="Jackery",
            model=device_info.get("productType"),
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        self._attr_is_on = last_state is not None and last_state.state == "on"
        self._follow_state[self._device_id] = self._attr_is_on
        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_CORE_CONFIG_UPDATE, lambda _event: self._sync_if_needed()
            )
        )
        self._sync_if_needed()

    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        self._sync_if_needed()

    async def async_turn_on(self, **kwargs) -> None:
        self._set_following(True)

    async def async_turn_off(self, **kwargs) -> None:
        self._set_following(False)

    def _set_following(self, following: bool) -> None:
        self._attr_is_on = following
        self._follow_state[self._device_id] = following
        self._retry_at = 0.0
        self.async_write_ha_state()
        # Lets the UTC Offset number update its availability.
        self.coordinator.async_update_listeners()
        self._sync_if_needed()

    def _sync_if_needed(self) -> None:
        if not self._attr_is_on or self._syncing or time.monotonic() < self._retry_at:
            return
        data = self.coordinator.data or {}
        current = data.get("uo")
        if not isinstance(current, (int, float)) or isinstance(current, bool):
            return
        if data.get("cloud_online") is False:
            return
        target = round(dt_util.now().utcoffset().total_seconds())
        if current == target:
            return
        self._syncing = True
        self.hass.async_create_task(self._async_sync(current, target))

    async def _async_sync(self, current: float, target: int) -> None:
        action_id, body, ack_cmd = timezone_command(
            is_transfer_switch_device(self._device_info, self.coordinator.data),
            target / 3600,
            self.hass.config.time_zone,
        )
        acked = False
        try:
            _LOGGER.info(
                "Following Home Assistant timezone on %s: uo %s -> %s",
                self._device_sn,
                current,
                target,
            )
            ack = await self._api.async_send_device_command(
                self._device_id, self._device_sn, action_id, body, ack_cmd=ack_cmd
            )
            acked = ack is not None
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Timezone resync failed for %s", self._device_sn)
        finally:
            self._syncing = False
            self._retry_at = time.monotonic() + (
                TZ_FOLLOW_RETRY_AFTER_SUCCESS if acked else TZ_FOLLOW_RETRY_AFTER_FAILURE
            )
        if not acked:
            _LOGGER.warning("No acknowledgement for timezone resync on %s", self._device_sn)
            return
        updated_data = dict(self.coordinator.data or {})
        updated_data["uo"] = body["uo"]
        self.coordinator.async_set_updated_data(updated_data)


class JackerySwitchEntity(CloudOnlineAvailabilityMixin, CoordinatorEntity, SwitchEntity):
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
        self._device_info = device_info
        self._attr_unique_id = f"{self._device_id}_switch_{description.key}"
        self._attr_name = description.name
        self._attr_icon = description.icon
        if description.entity_category is not None:
            self._attr_entity_category = description.entity_category
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

    @property
    def extra_state_attributes(self) -> dict | None:
        text = ENTITY_HELP_TEXT.get(self.entity_description.key)
        return {"description": text} if text else None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the device setting on."""
        await self._async_set_value(1)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device setting off."""
        await self._async_set_value(0)

    async def _async_set_value(self, raw_state: int) -> None:
        """Set the underlying Jackery property."""
        key = self.entity_description.key
        try:
            box_cmd = TRANSFER_SWITCH_COMMANDS.get(key)
            if box_cmd is not None:
                action_id, cmd = box_cmd
                await self._api.async_send_device_command(
                    self._device_id,
                    self._device_sn,
                    action_id,
                    {"cmd": cmd, key: raw_state},
                )
            else:
                await self._api.async_set_device_property(
                    self._device_id,
                    self._device_sn,
                    self._slug,
                    raw_state,
                )
        except asyncio.CancelledError:
            raise
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.name}: {err}"
            ) from err

        updated_data = dict(self.coordinator.data or {})
        updated_data[key] = raw_state
        self.coordinator.async_set_updated_data(updated_data)
        await self.coordinator.async_request_refresh()


class JackeryChargingPlanSwitchEntity(CloudOnlineAvailabilityMixin, CoordinatorEntity, SwitchEntity):
    """Implementation of the charging-plan master switch."""

    entity_description: EntityDescription

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        description: EntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the charging-plan switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._device_info = device_info
        self._attr_unique_id = f"{self._device_id}_switch_{description.key}"
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_entity_category = description.entity_category
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_info.get("devName", f"Jackery Device {self._device_id}"),
            manufacturer="Jackery",
            model=device_info.get("productType"),
        )

    @property
    def available(self) -> bool:
        """Return whether the charging-plan switch is currently supported."""
        try:
            parent_available = super().available
        except AttributeError:
            parent_available = True
        return parent_available and has_charging_plan_switch_support(
            self.coordinator.data,
            self._device_info,
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the charging-plan switch is on."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "on"}
        return bool(value)

    async def async_turn_on(self, **kwargs) -> None:
        """Enable the charging plan."""
        await self._async_set_value(1)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the charging plan."""
        await self._async_set_value(0)

    async def _async_set_value(self, raw_state: int) -> None:
        """Set the charging-plan master switch."""
        try:
            await self._api.async_set_device_dp(
                self._device_id,
                self._device_sn,
                self.entity_description.key,
                raw_state,
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
