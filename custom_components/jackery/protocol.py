"""Protocol helpers for Jackery property and control support."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class JackeryControlSpec:
    """Describe a writable Jackery property."""

    key: str
    slug: str
    name: str
    platform: str
    icon: str
    read_keys: tuple[str, ...] = ()
    options: tuple[str, ...] = ()
    # MQTT action_id for portable device commands (None = Transfer Switch only).
    action_id: int | None = None
    # Override the property key written in the MQTT body (e.g. sltb reads "slt").
    write_key: str | None = None

    @property
    def state_keys(self) -> tuple[str, ...]:
        """Keys that can expose the current state for this control."""
        return self.read_keys or (self.key,)

    @property
    def prop_key(self) -> str:
        """Property key to use in MQTT command body."""
        return self.write_key or self.key


CONTROL_SPECS: dict[str, JackeryControlSpec] = {
    # Portable device properties
    "oac": JackeryControlSpec(
        key="oac",
        slug="ac",
        name="AC Output",
        platform="switch",
        icon="mdi:power-plug",
        action_id=4,
    ),
    "odc": JackeryControlSpec(
        key="odc",
        slug="dc",
        name="DC Output",
        platform="switch",
        icon="mdi:power",
        action_id=1,
    ),
    "odcu": JackeryControlSpec(
        key="odcu",
        slug="usb",
        name="USB Output",
        platform="switch",
        icon="mdi:usb-port",
        action_id=2,
    ),
    "odcc": JackeryControlSpec(
        key="odcc",
        slug="car",
        name="DC Car Output",
        platform="switch",
        icon="mdi:car",
        action_id=3,
    ),
    "sfc": JackeryControlSpec(
        key="sfc",
        slug="sfc",
        name="Super Fast Charge",
        platform="switch",
        icon="mdi:flash",
        action_id=13,
    ),
    "outPrio": JackeryControlSpec(
        key="outPrio",
        slug="output-priority",
        name="AC Output Priority",
        platform="switch",
        icon="mdi:power-plug-battery",
        action_id=47,
    ),
    "odcPrio": JackeryControlSpec(
        key="odcPrio",
        slug="dc-output-priority",
        name="DC Output Priority",
        platform="switch",
        icon="mdi:car-battery",
        action_id=48,
    ),
    "dhg_recall": JackeryControlSpec(
        key="dhg_recall",
        slug="discharge-memory",
        name="Discharge Memory",
        platform="switch",
        icon="mdi:memory",
        action_id=53,
    ),
    "lm": JackeryControlSpec(
        key="lm",
        slug="light",
        name="Light Mode",
        platform="select",
        icon="mdi:lightbulb",
        options=("off", "low", "high", "sos"),
        action_id=7,
    ),
    "cs": JackeryControlSpec(
        key="cs",
        slug="charge-speed",
        name="Charge Speed",
        platform="select",
        icon="mdi:battery-charging",
        options=("fast", "mute"),
        action_id=10,
    ),
    "lps": JackeryControlSpec(
        key="lps",
        slug="battery-protection",
        name="Battery Protection",
        platform="select",
        icon="mdi:battery-heart-variant",
        options=("full", "eco"),
        action_id=11,
    ),
    "ast": JackeryControlSpec(
        key="ast",
        slug="auto-shutdown",
        name="Auto Shutdown",
        platform="number",
        icon="mdi:timer-off-outline",
        action_id=9,
    ),
    "pm": JackeryControlSpec(
        key="pm",
        slug="energy-saving",
        name="Energy Saving",
        platform="number",
        icon="mdi:leaf",
        action_id=12,
    ),
    "sltb": JackeryControlSpec(
        key="sltb",
        slug="screen-timeout",
        name="Screen Timeout",
        platform="number",
        icon="mdi:monitor-screenshot",
        read_keys=("sltb", "slt"),
        action_id=8,
        write_key="slt",
    ),
    # Transfer Switch properties - action_ids are set per-command in the platform
    # modules (TRANSFER_SWITCH_COMMANDS / _NUMBER_COMMANDS / _SELECT_COMMANDS).
    # action_id is intentionally omitted here; these never go through
    # async_set_device_property.
    "ddt": JackeryControlSpec(
        key="ddt",
        slug="ddt",
        name="Backup Reserve",
        platform="number",
        icon="mdi:battery-lock",
    ),
    "autoDt": JackeryControlSpec(
        key="autoDt",
        slug="autoDt",
        name="Auto Mode Backup Reserve",
        platform="number",
        icon="mdi:battery-lock",
    ),
    "cdsDt": JackeryControlSpec(
        key="cdsDt",
        slug="cdsDt",
        name="Scheduled Mode Backup Reserve",
        platform="number",
        icon="mdi:battery-lock",
    ),
    "selfDt": JackeryControlSpec(
        key="selfDt",
        slug="selfDt",
        name="Self Consumption Mode Backup Reserve",
        platform="number",
        icon="mdi:battery-lock",
    ),
    "en": JackeryControlSpec(
        key="en",
        slug="en",
        name="Working Mode",
        platform="select",
        icon="mdi:transfer-switch",
        options=("Automatic Charging", "Scheduled Tasks", "Self Consumption"),
    ),
    "ups": JackeryControlSpec(
        key="ups",
        slug="ups",
        name="UPS Mode",
        platform="switch",
        icon="mdi:power-plug-battery",
    ),
    "pss": JackeryControlSpec(
        key="pss",
        slug="pss",
        name="Grid / Station",
        platform="switch",
        icon="mdi:transmission-tower",
    ),
    "rc": JackeryControlSpec(
        key="rc",
        slug="rc",
        name="Force Charge",
        platform="switch",
        icon="mdi:battery-charging-100",
    ),
    "wps": JackeryControlSpec(
        key="wps",
        slug="wps",
        name="Weather Protection",
        platform="switch",
        icon="mdi:weather-lightning",
    ),
}

# Slug-indexed reverse lookup for fast action_id resolution in api.py.
CONTROL_SPECS_BY_SLUG: dict[str, JackeryControlSpec] = {
    spec.slug: spec for spec in CONTROL_SPECS.values()
}

CHARGING_PLAN_SWITCH_DP = "107"
CHARGING_PLAN_DATA_DP = "108"
CHARGING_PLAN_REPEAT_TO_MASK: dict[str, str] = {
    "Everyday": "1111111",
    "Weekdays": "0111110",
    "Weekends": "1000001",
    "Once": "0000000",
}
CHARGING_PLAN_MASK_TO_REPEAT: dict[str, str] = {
    mask: option for option, mask in CHARGING_PLAN_REPEAT_TO_MASK.items()
}
KNOWN_CHARGING_PLAN_MODELS = frozenset(
    {
        "homepower 3000",
        "homepower 3600 plus",
        "explorer 3000 v2",
        "explorer 5000 plus",
    }
)
_CHARGING_PLAN_TIME_RANGE = re.compile(
    r"^(?:[01]\d|2[0-3]):[0-5]\d-(?:[01]\d|2[0-3]):[0-5]\d$"
)
_MODEL_NAME_SANITIZER = re.compile(r"[^a-z0-9]+")

# Properties that only appear on Transfer Switch devices (both raw and flattened forms).
_TRANSFER_SWITCH_MARKER_KEYS = frozenset({"ac1", "fz", "cds", "cir", "ac1_rb", "fz_gs"})


def _property_keys(properties: Mapping[str, object] | None) -> set[str]:
    """Return the set of reported property keys."""
    if not properties:
        return set()
    return {str(key) for key in properties}


def _normalize_model_name(value: object) -> str:
    """Normalize a device model name for capability matching."""
    if not isinstance(value, str):
        return ""

    normalized = _MODEL_NAME_SANITIZER.sub(" ", value.casefold())
    return " ".join(normalized.split())


def is_transfer_switch_device(
    device_info: Mapping[str, object] | None = None,
    properties: Mapping[str, object] | None = None,
) -> bool:
    """Return whether this device should be treated as a Transfer Switch.

    Checks modelCode == 2001 first, then falls back to property-based detection
    for forward-compat with future Box variants.  Works with both raw properties
    (pre-flatten, has "ac1"/"fz" keys) and flattened coordinator data
    (has "ac1_rb"/"fz_gs" keys).
    """
    if device_info and device_info.get("modelCode") == 2001:
        return True
    if properties:
        return bool(_property_keys(properties) & _TRANSFER_SWITCH_MARKER_KEYS)
    return False


def has_known_charging_plan_model(device_info: Mapping[str, object] | None) -> bool:
    """Return whether the device model is known to support charging plans."""
    if not device_info:
        return False

    for key in ("productType", "devName", "devNickname", "modelName", "deviceName"):
        if _normalize_model_name(device_info.get(key)) in KNOWN_CHARGING_PLAN_MODELS:
            return True

    return False


def has_split_dc_outputs(properties: Mapping[str, object] | None) -> bool:
    """Return whether the device reports separate USB or car output keys."""
    keys = _property_keys(properties)
    return "odcu" in keys or "odcc" in keys


def has_charging_plan_switch_support(
    properties: Mapping[str, object] | None,
    device_info: Mapping[str, object] | None = None,
) -> bool:
    """Return whether the device reports the charging-plan switch DP."""
    keys = _property_keys(properties)
    return CHARGING_PLAN_SWITCH_DP in keys or has_known_charging_plan_model(
        device_info
    )


def has_charging_plan_data_support(
    properties: Mapping[str, object] | None,
    device_info: Mapping[str, object] | None = None,
) -> bool:
    """Return whether the device reports the charging-plan data DP."""
    keys = _property_keys(properties)
    return CHARGING_PLAN_DATA_DP in keys or has_known_charging_plan_model(
        device_info
    )


def parse_charging_plan(value: object) -> tuple[str, str] | None:
    """Split a charging-plan payload into time range and repeat mask."""
    if not isinstance(value, str):
        return None

    time_range, separator, repeat_mask = value.partition(",")
    if not separator:
        return None
    if _CHARGING_PLAN_TIME_RANGE.fullmatch(time_range) is None:
        return None
    if repeat_mask not in CHARGING_PLAN_MASK_TO_REPEAT:
        return None

    return time_range, repeat_mask


def compose_charging_plan(time_range: str, repeat_mask: str) -> str:
    """Join a validated charging-plan time range and repeat mask."""
    if _CHARGING_PLAN_TIME_RANGE.fullmatch(time_range) is None:
        raise ValueError(f"Invalid charging plan time range: {time_range!r}")
    if repeat_mask not in CHARGING_PLAN_MASK_TO_REPEAT:
        raise ValueError(f"Invalid charging plan repeat mask: {repeat_mask!r}")

    return f"{time_range},{repeat_mask}"


def charging_plan_repeat_option(repeat_mask: str) -> str | None:
    """Return the user-facing repeat option for a repeat mask."""
    return CHARGING_PLAN_MASK_TO_REPEAT.get(repeat_mask)


def charging_plan_repeat_mask(option: str) -> str:
    """Return the repeat mask for a user-facing charging-plan option."""
    return CHARGING_PLAN_REPEAT_TO_MASK[option]


def is_supported_property(
    properties: Mapping[str, object] | None,
    key: str,
) -> bool:
    """Return whether an entity should be created for the property."""
    keys = _property_keys(properties)

    if key == "odc":
        return "odc" in keys and not has_split_dc_outputs(properties)

    if key in {"odcu", "odcc"}:
        return key in keys

    spec = CONTROL_SPECS.get(key)
    if spec is not None:
        return any(state_key in keys for state_key in spec.state_keys)

    return key in keys


def supported_keys(
    properties: Mapping[str, object] | None,
    candidates: tuple[str, ...],
) -> tuple[str, ...]:
    """Filter candidate keys down to those supported by the device."""
    return tuple(key for key in candidates if is_supported_property(properties, key))


def control_spec(key: str) -> JackeryControlSpec:
    """Return the control spec for a property key."""
    return CONTROL_SPECS[key]


def timezone_command(
    is_transfer_switch: bool, utc_offset_hours: float, zone: str
) -> tuple[int, dict[str, object], int | None]:
    """Build (action_id, body, ack_cmd) for setting a device's timezone.

    The device wants ``uo`` as an integer number of seconds (a string sets 0).
    The Explorer 5000 Plus drops bodies that contain ``timezone``, so portables
    get ``uo`` only.
    """
    seconds = round(utc_offset_hours * 3600)
    if is_transfer_switch:
        return 1, {"cmd": 3, "uo": seconds, "timezone": zone}, 3
    return 25, {"uo": seconds}, None


CLOUD_ONLINE_KEY = "cloud_online"
CLOUD_ONLINE_TIME_KEY = "cloud_online_time"
CLOUD_OFFLINE_TIME_KEY = "cloud_offline_time"
# Entities that describe the cloud link itself and must stay available while offline.
CLOUD_STATUS_KEYS = frozenset(
    {CLOUD_ONLINE_KEY, CLOUD_ONLINE_TIME_KEY, CLOUD_OFFLINE_TIME_KEY, "last_updated"}
)


def parse_cloud_status(device: Mapping[str, object] | None) -> dict[str, object]:
    """Extract online state and transition times from a property response's device block."""
    if not isinstance(device, Mapping):
        return {}
    status: dict[str, object] = {}
    online = device.get("onlineStatus")
    if online is not None:
        status[CLOUD_ONLINE_KEY] = online == 1
    for src, dst in (
        ("onlineTime", CLOUD_ONLINE_TIME_KEY),
        ("offlineTime", CLOUD_OFFLINE_TIME_KEY),
    ):
        ts = device.get(src)
        if isinstance(ts, (int, float)) and not isinstance(ts, bool) and ts > 0:
            status[dst] = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return status


def is_cloud_online(properties: Mapping[str, object] | None) -> bool:
    """Return False only when the cloud explicitly reports the device offline."""
    return not properties or properties.get(CLOUD_ONLINE_KEY) is not False


class CloudOnlineAvailabilityMixin:
    """Mark coordinator entities unavailable while the device is offline from the cloud."""

    @property
    def available(self) -> bool:
        try:
            parent_available = super().available
        except AttributeError:
            parent_available = True
        if not parent_available:
            return False
        description = getattr(self, "entity_description", None)
        if getattr(description, "key", None) in CLOUD_STATUS_KEYS:
            return True
        return is_cloud_online(self.coordinator.data)
