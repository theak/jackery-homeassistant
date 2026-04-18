"""Protocol helpers for Jackery property and control support."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass


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

    @property
    def state_keys(self) -> tuple[str, ...]:
        """Keys that can expose the current state for this control."""
        return self.read_keys or (self.key,)


CONTROL_SPECS: dict[str, JackeryControlSpec] = {
    "oac": JackeryControlSpec(
        key="oac",
        slug="ac",
        name="AC Output",
        platform="switch",
        icon="mdi:power-plug",
    ),
    "odc": JackeryControlSpec(
        key="odc",
        slug="dc",
        name="DC Output",
        platform="switch",
        icon="mdi:power",
    ),
    "odcu": JackeryControlSpec(
        key="odcu",
        slug="usb",
        name="USB Output",
        platform="switch",
        icon="mdi:usb-port",
    ),
    "odcc": JackeryControlSpec(
        key="odcc",
        slug="car",
        name="DC Car Output",
        platform="switch",
        icon="mdi:car",
    ),
    "sfc": JackeryControlSpec(
        key="sfc",
        slug="sfc",
        name="Super Fast Charge",
        platform="switch",
        icon="mdi:flash",
    ),
    "lm": JackeryControlSpec(
        key="lm",
        slug="light",
        name="Light Mode",
        platform="select",
        icon="mdi:lightbulb",
        options=("off", "low", "high", "sos"),
    ),
    "cs": JackeryControlSpec(
        key="cs",
        slug="charge-speed",
        name="Charge Speed",
        platform="select",
        icon="mdi:battery-charging",
        options=("fast", "mute"),
    ),
    "lps": JackeryControlSpec(
        key="lps",
        slug="battery-protection",
        name="Battery Protection",
        platform="select",
        icon="mdi:battery-heart-variant",
        options=("full", "eco"),
    ),
    "ast": JackeryControlSpec(
        key="ast",
        slug="auto-shutdown",
        name="Auto Shutdown",
        platform="number",
        icon="mdi:timer-off-outline",
    ),
    "pm": JackeryControlSpec(
        key="pm",
        slug="energy-saving",
        name="Energy Saving",
        platform="number",
        icon="mdi:leaf",
    ),
    "sltb": JackeryControlSpec(
        key="sltb",
        slug="screen-timeout",
        name="Screen Timeout",
        platform="number",
        icon="mdi:monitor-screenshot",
        read_keys=("sltb", "slt"),
    ),
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
_CHARGING_PLAN_TIME_RANGE = re.compile(
    r"^(?:[01]\d|2[0-3]):[0-5]\d-(?:[01]\d|2[0-3]):[0-5]\d$"
)


def _property_keys(properties: Mapping[str, object] | None) -> set[str]:
    """Return the set of reported property keys."""
    if not properties:
        return set()
    return {str(key) for key in properties}


def has_split_dc_outputs(properties: Mapping[str, object] | None) -> bool:
    """Return whether the device reports separate USB or car output keys."""
    keys = _property_keys(properties)
    return "odcu" in keys or "odcc" in keys


def has_charging_plan_support(properties: Mapping[str, object] | None) -> bool:
    """Return whether the device reports both charging-plan DPs."""
    keys = _property_keys(properties)
    return {
        CHARGING_PLAN_SWITCH_DP,
        CHARGING_PLAN_DATA_DP,
    }.issubset(keys)


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
