"""Select platform for Jackery."""

from __future__ import annotations

import asyncio

from homeassistant.components.select import SelectEntity
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
from .const import CHARGING_PLAN_DATA, DOMAIN, ENTITY_HELP_TEXT
from homeassistant.const import EntityCategory
from .protocol import (
    CHARGING_PLAN_REPEAT_TO_MASK,
    CloudOnlineAvailabilityMixin,
    charging_plan_repeat_mask,
    charging_plan_repeat_option,
    compose_charging_plan,
    control_spec,
    has_charging_plan_data_support,
    parse_charging_plan,
    supported_keys,
)

# Transfer Switch commands for select-like properties (key -> (action_id, cmd))
TRANSFER_SWITCH_SELECT_COMMANDS: dict[str, tuple[int, int]] = {
    "en": (20, 20),
}
SELECT_KEYS = ("lm", "cs", "lps", "en")

def _select_desc(key: str, **kwargs) -> EntityDescription:
    spec = control_spec(key)
    return EntityDescription(key=spec.key, name=spec.name, icon=spec.icon, **kwargs)

SELECT_DESCRIPTIONS: dict[str, EntityDescription] = {
    "lm": _select_desc("lm", entity_category=EntityCategory.CONFIG),
    "cs": _select_desc("cs", entity_category=EntityCategory.CONFIG),
    "lps": _select_desc("lps", entity_category=EntityCategory.CONFIG),
    "en": _select_desc("en", entity_category=None),
}
SELECT_OPTIONS: dict[str, tuple[str, ...]] = {
    key: control_spec(key).options for key in SELECT_KEYS
}
CHARGING_PLAN_REPEAT_OPTIONS = tuple(CHARGING_PLAN_REPEAT_TO_MASK)
CHARGING_PLAN_REPEAT_DESCRIPTION = EntityDescription(
    key=CHARGING_PLAN_DATA,
    name="Charging Plan Repeat",
    icon="mdi:calendar-week",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jackery select entities."""
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

        for key in supported_keys(coordinator.data, SELECT_KEYS):
            entities.append(
                JackerySelectEntity(
                    api=api,
                    coordinator=coordinator,
                    description=SELECT_DESCRIPTIONS[key],
                    device_info=device,
                )
            )
        if has_charging_plan_data_support(coordinator.data, device):
            entities.append(
                JackeryChargingPlanRepeatEntity(
                    api=api,
                    coordinator=coordinator,
                    description=CHARGING_PLAN_REPEAT_DESCRIPTION,
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
                device_coordinator.data,
                device_info,
            ):
                return

            entity_added = True
            async_add_entities(
                [
                    JackeryChargingPlanRepeatEntity(
                        api=api,
                        coordinator=device_coordinator,
                        description=CHARGING_PLAN_REPEAT_DESCRIPTION,
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

        if has_charging_plan_data_support(coordinator.data, device):
            continue

        unsubscribe = coordinator.async_add_listener(
            _build_charging_plan_listener(device, coordinator)
        )
        if hasattr(config_entry, "async_on_unload"):
            config_entry.async_on_unload(unsubscribe)


class JackerySelectEntity(CloudOnlineAvailabilityMixin, CoordinatorEntity, SelectEntity):
    """Implementation of a Jackery select."""

    entity_description: EntityDescription

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        description: EntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._slug = control_spec(description.key).slug
        self._options = SELECT_OPTIONS[description.key]
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._attr_unique_id = f"{self._device_id}_{description.key}"
        self._attr_name = description.name
        self._attr_icon = description.icon
        if description.entity_category is not None:
            self._attr_entity_category = description.entity_category
        self._attr_options = list(self._options)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_info.get("devName", f"Jackery Device {self._device_id}"),
            manufacturer="Jackery",
            model=device_info.get("productType"),
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None

        try:
            return self._options[int(value)]
        except (IndexError, TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict | None:
        text = ENTITY_HELP_TEXT.get(self.entity_description.key)
        return {"description": text} if text else None

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        if option not in self._options:
            raise HomeAssistantError(
                f"Unsupported option '{option}' for {self.entity_description.name}."
            )

        try:
            transfer_switch_cmd = TRANSFER_SWITCH_SELECT_COMMANDS.get(self.entity_description.key)
            if transfer_switch_cmd is not None:
                action_id, cmd = transfer_switch_cmd
                int_value = self._attr_options.index(option)
                await self._api.async_send_device_command(
                    self._device_id,
                    self._device_sn,
                    action_id,
                    {"cmd": cmd, self.entity_description.key: int_value},
                )
            else:
                await self._api.async_set_device_property(
                    self._device_id,
                    self._device_sn,
                    self._slug,
                    option,
                )
        except asyncio.CancelledError:
            raise
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.name}: {err}"
            ) from err

        updated_data = dict(self.coordinator.data or {})
        updated_data[self.entity_description.key] = self._options.index(option)
        self.coordinator.async_set_updated_data(updated_data)
        await self.coordinator.async_request_refresh()


class JackeryChargingPlanRepeatEntity(CloudOnlineAvailabilityMixin, CoordinatorEntity, SelectEntity):
    """Select entity for charging-plan repeat masks."""

    entity_description: EntityDescription

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        description: EntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the charging-plan repeat select."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._device_info = device_info
        self._attr_unique_id = f"{self._device_id}_charging_plan_repeat"
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_entity_category = description.entity_category
        self._attr_options = list(CHARGING_PLAN_REPEAT_OPTIONS)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_info.get("devName", f"Jackery Device {self._device_id}"),
            manufacturer="Jackery",
            model=device_info.get("productType"),
        )

    @property
    def available(self) -> bool:
        """Return whether the repeat select is currently usable."""
        try:
            parent_available = super().available
        except AttributeError:
            parent_available = True
        return (
            parent_available
            and has_charging_plan_data_support(
                self.coordinator.data,
                self._device_info,
            )
            and self._parsed_value() is not None
        )

    @property
    def current_option(self) -> str | None:
        """Return the current repeat option."""
        parsed_value = self._parsed_value()
        if parsed_value is None:
            return None

        return charging_plan_repeat_option(parsed_value[1])

    async def async_select_option(self, option: str) -> None:
        """Update only the repeat segment of the charging-plan payload."""
        if option not in CHARGING_PLAN_REPEAT_OPTIONS:
            raise HomeAssistantError(
                f"Unsupported option '{option}' for {self.entity_description.name}."
            )

        parsed_value = self._parsed_value()
        if parsed_value is None:
            raise HomeAssistantError("Charging plan data is unavailable or malformed.")

        time_range, _repeat_mask = parsed_value
        combined_value = compose_charging_plan(
            time_range,
            charging_plan_repeat_mask(option),
        )

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
