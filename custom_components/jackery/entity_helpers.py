"""Shared entity helpers for Jackery platforms."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN


def build_device_info(device: Mapping[str, Any]) -> DeviceInfo:
    """Build Home Assistant device metadata."""
    model = (
        device.get("devModel")
        or device.get("productType")
        or device.get("modelName")
        or device.get("devName")
    )
    return DeviceInfo(
        identifiers={(DOMAIN, device["devId"])},
        name=device.get("devName", f"Jackery Device {device['devId']}"),
        manufacturer="Jackery",
        model=model,
        serial_number=device.get("devSn"),
    )


class JackeryCoordinatorEntity(CoordinatorEntity):
    """Base coordinator-backed Jackery entity."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        property_key: str,
        device: Mapping[str, Any],
    ) -> None:
        """Initialize the shared entity state."""
        super().__init__(coordinator)
        self._device = dict(device)
        self._device_id = str(device["devId"])
        self._property_key = property_key
        self._attr_unique_id = f"{self._device_id}_{property_key}"
        self._attr_device_info = build_device_info(device)

    @property
    def property_value(self) -> Any:
        """Return the current raw property value."""
        return self.coordinator.data.get(self._property_key)


class JackeryControllableEntity(JackeryCoordinatorEntity):
    """Base class for MQTT-backed Jackery control entities."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: Any,
        property_key: str,
        device: Mapping[str, Any],
    ) -> None:
        """Initialize the controllable entity."""
        super().__init__(coordinator, property_key, device)
        self._api = api

    async def async_set_jackery_value(self, value: str | int) -> None:
        """Push a value to Jackery and refresh coordinator state."""
        try:
            result = await self._api.async_set_property(
                self._device_id,
                self._property_key,
                value,
            )
        except Exception as err:  # pragma: no cover - exercised in HA runtime
            raise HomeAssistantError(str(err)) from err

        if isinstance(result, dict) and result:
            updated = dict(self.coordinator.data)
            updated.update(result)
            updated["last_updated"] = dt_util.now()
            self.coordinator.async_set_updated_data(updated)

        await self.coordinator.async_request_refresh()

    @callback
    def update_coordinator_state(self, values: Mapping[str, Any]) -> None:
        """Apply device-reported values to the coordinator immediately."""
        updated = dict(self.coordinator.data)
        updated.update(values)
        updated["last_updated"] = dt_util.now()
        self.coordinator.async_set_updated_data(updated)
