"""Circuit entities for Jackery Transfer Switch.

Circuit data is fetched by the coordinator (via MQTT QueryCircuitProperty)
and stored in ``coordinator.data["_circuits"]`` alongside regular HTTP properties.
Each circuit has: nm (base64 name), idx (1-12), pc (power W), sw (0/1),
sph (split-phase partner idx, 0=solo), pr (priority), sph_pc (split-phase power).

Split-phase pairs (e.g. idx 8 sph=10, idx 10 sph=8) are combined into a
single entity using the named circuit's label and summing power from both.
"""

from __future__ import annotations

import base64
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import JackeryAPI
from .const import DOMAIN
from .protocol import CloudOnlineAvailabilityMixin

_LOGGER = logging.getLogger(__name__)


def _decode_circuit_name(nm: str) -> str:
    """Decode a base64-encoded circuit name, falling back to raw value."""
    if not nm:
        return ""
    try:
        return base64.b64decode(nm).decode("utf-8")
    except Exception:
        return nm


def _circuit_display_name(circuit: dict, partner: dict | None = None) -> str:
    """Build a display name for a circuit (or split-phase pair).

    Rules:
    - Use the decoded name if set, otherwise fall back to "Circuit <idx>".
    - For split-phase pairs, prefer whichever circuit has a name.
    - Strip leading "Circuit " from user names to avoid "Circuit Circuit 5".
    """
    name = _decode_circuit_name(circuit.get("nm", ""))
    if not name and partner:
        name = _decode_circuit_name(partner.get("nm", ""))
    if not name:
        name = str(circuit["idx"])
    # Avoid "Circuit Circuit 5" - strip if user already prefixed with "Circuit"
    if name.lower().startswith("circuit "):
        name = name[8:]
    return name


def _get_circuits(coordinator: DataUpdateCoordinator) -> list[dict]:
    """Read circuits from coordinator data, returning [] if absent."""
    data = coordinator.data
    if not isinstance(data, dict):
        return []
    return data.get("_circuits") or []


def _find_circuit(coordinator: DataUpdateCoordinator, idx: int) -> dict | None:
    """Find a specific circuit by index in coordinator data."""
    for circuit in _get_circuits(coordinator):
        if circuit.get("idx") == idx:
            return circuit
    return None


def _circuit_by_idx(circuits: list[dict], idx: int) -> dict | None:
    """Find a circuit by index in a list."""
    for c in circuits:
        if c.get("idx") == idx:
            return c
    return None


def get_logical_circuits(circuits: list[dict]) -> list[dict]:
    """Collapse split-phase pairs into logical circuit entries.

    Returns a list of dicts with keys:
        primary_idx, partner_idx (or None), name, indices (list of idx).
    Solo circuits have partner_idx=None.
    """
    seen: set[int] = set()
    result: list[dict] = []
    for c in sorted(circuits, key=lambda x: x.get("idx", 0)):
        idx = c.get("idx")
        if idx is None or idx in seen:
            continue
        seen.add(idx)
        sph = c.get("sph", 0)
        partner = _circuit_by_idx(circuits, sph) if sph else None
        if partner and partner.get("idx") not in seen:
            seen.add(partner["idx"])
            name = _circuit_display_name(c, partner)
            result.append({
                "primary_idx": idx,
                "partner_idx": partner["idx"],
                "name": name,
                "indices": [idx, partner["idx"]],
            })
        else:
            name = _circuit_display_name(c)
            result.append({
                "primary_idx": idx,
                "partner_idx": None,
                "name": name,
                "indices": [idx],
            })
    return result


def has_circuits(coordinator: DataUpdateCoordinator) -> bool:
    """Return True if coordinator data contains circuit data."""
    data = coordinator.data
    return isinstance(data, dict) and "_circuits" in data


def _device_info(device: dict) -> DeviceInfo:
    """Build DeviceInfo from the device dict."""
    dev_id = device["devId"]
    return DeviceInfo(
        identifiers={(DOMAIN, dev_id)},
        name=device.get("devName", f"Jackery Device {dev_id}"),
        manufacturer="Jackery",
        model=device.get("productType"),
    )


class JackeryCircuitPowerSensor(CloudOnlineAvailabilityMixin, CoordinatorEntity, SensorEntity):
    """Sensor showing per-circuit power consumption.

    For split-phase pairs, reports the sum of both circuits' power.
    """

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_info: dict,
        logical: dict,
    ) -> None:
        super().__init__(coordinator)
        self._primary_idx = logical["primary_idx"]
        self._partner_idx = logical["partner_idx"]
        self._indices = logical["indices"]
        self._circuit_name = logical["name"]
        self._attr_unique_id = (
            f"{device_info['devId']}_circuit_{self._primary_idx}_power"
        )
        self._attr_name = f"Circuit {self._circuit_name} Power"
        self._attr_icon = "mdi:flash"
        self._attr_entity_category = None
        self._attr_device_info = _device_info(device_info)

    @property
    def native_value(self) -> int | None:
        total = 0
        found = False
        for idx in self._indices:
            c = _find_circuit(self.coordinator, idx)
            if c is not None:
                found = True
                total += c.get("pc", 0) or 0
        return total if found else None

    @property
    def extra_state_attributes(self) -> dict:
        attrs: dict[str, object] = {
            "circuit_index": self._primary_idx,
            "circuit_name": self._circuit_name,
            "description": "Real-time power consumption for this circuit.",
        }
        if self._partner_idx is not None:
            attrs["split_phase_partner"] = self._partner_idx
            attrs["combined"] = True
        primary = _find_circuit(self.coordinator, self._primary_idx)
        if primary:
            attrs["priority"] = primary.get("pr")
        return attrs


class JackeryCircuitSwitch(CloudOnlineAvailabilityMixin, CoordinatorEntity, SwitchEntity):
    """Switch to turn a circuit on or off.

    For split-phase pairs, toggles both circuits together.
    """

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        device_info: dict,
        logical: dict,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._primary_idx = logical["primary_idx"]
        self._partner_idx = logical["partner_idx"]
        self._indices = logical["indices"]
        self._circuit_name = logical["name"]
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._attr_unique_id = (
            f"{self._device_id}_circuit_{self._primary_idx}_switch"
        )
        self._attr_name = f"Circuit {self._circuit_name}"
        self._attr_icon = "mdi:electric-switch"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = _device_info(device_info)

    @property
    def is_on(self) -> bool | None:
        circuit = _find_circuit(self.coordinator, self._primary_idx)
        if circuit is None:
            return None
        return circuit.get("sw") == 1

    @property
    def extra_state_attributes(self) -> dict:
        attrs: dict[str, object] = {
            "circuit_index": self._primary_idx,
            "circuit_name": self._circuit_name,
            "description": "Toggle power to this circuit on or off.",
        }
        if self._partner_idx is not None:
            attrs["split_phase_partner"] = self._partner_idx
            attrs["combined"] = True
        return attrs

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_switch(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_switch(False)

    async def _async_set_switch(self, on: bool) -> None:
        try:
            for idx in self._indices:
                await self._api.async_set_circuit_switch(
                    self._device_id,
                    self._device_sn,
                    idx,
                    on,
                )
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to {'enable' if on else 'disable'} circuit "
                f"{self._circuit_name}: {err}"
            ) from err

        # Optimistic update
        circuits = _get_circuits(self.coordinator)
        for circuit in circuits:
            if circuit.get("idx") in self._indices:
                circuit["sw"] = 1 if on else 0
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
