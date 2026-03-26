"""Property capability metadata for Jackery devices."""

from __future__ import annotations

from collections.abc import Mapping

SENSOR_KEYS: tuple[str, ...] = (
    "rb",
    "bt",
    "op",
    "ip",
    "acip",
    "cip",
    "it",
    "ot",
    "acov",
    "acohz",
    "ec",
    "last_updated",
)

BINARY_SENSOR_KEYS: tuple[str, ...] = (
    "ta",
    "pal",
    "wss",
)

SWITCH_KEYS: tuple[str, ...] = (
    "oac",
    "odc",
    "odcu",
    "odcc",
    "iac",
    "idc",
    "sfc",
    "ups",
)

SELECT_KEYS: tuple[str, ...] = (
    "lm",
    "cs",
    "lps",
)

NUMBER_KEYS: tuple[str, ...] = (
    "ast",
    "pm",
    "sltb",
)

PLATFORM_KEYS: dict[str, tuple[str, ...]] = {
    "sensor": SENSOR_KEYS,
    "binary_sensor": BINARY_SENSOR_KEYS,
    "switch": SWITCH_KEYS,
    "select": SELECT_KEYS,
    "number": NUMBER_KEYS,
}

ENTITY_DOMAIN_BY_KEY: dict[str, str] = {
    key: platform for platform, keys in PLATFORM_KEYS.items() for key in keys
}

SELECT_OPTIONS: dict[str, tuple[str, ...]] = {
    "lm": ("off", "low", "high", "sos"),
    "cs": ("fast", "mute"),
    "lps": ("full", "eco"),
}

WRITE_KEY_OVERRIDES: dict[str, str] = {
    "sltb": "slt",
}

LEGACY_OUTPUT_KEYS: tuple[str, ...] = (
    "oac",
    "odc",
    "odcu",
    "odcc",
)


def supported_keys_for_platform(
    properties: Mapping[str, object], platform: str
) -> tuple[str, ...]:
    """Return the supported property keys for a platform."""
    return tuple(key for key in PLATFORM_KEYS[platform] if key in properties)


def supported_keys_by_platform(
    properties: Mapping[str, object],
) -> dict[str, tuple[str, ...]]:
    """Return supported property keys for every platform."""
    return {
        platform: supported_keys_for_platform(properties, platform)
        for platform in PLATFORM_KEYS
    }


def expected_unique_ids(device_id: str | int, properties: Mapping[str, object]) -> set[str]:
    """Return the set of entity unique IDs expected for a device."""
    return {
        f"{device_id}_{key}"
        for keys in supported_keys_by_platform(properties).values()
        for key in keys
    }


def expected_entity_domain_for_key(key: str) -> str | None:
    """Return the Home Assistant entity domain expected for a property key."""
    return ENTITY_DOMAIN_BY_KEY.get(key)
