"""Tests for Jackery capability gating."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


FEATURES_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "jackery"
    / "features.py"
)
spec = spec_from_file_location("jackery_features", FEATURES_PATH)
features = module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(features)

expected_unique_ids = features.expected_unique_ids
expected_entity_domain_for_key = features.expected_entity_domain_for_key
supported_keys_by_platform = features.supported_keys_by_platform


EXPLORER_240_PROPERTIES = {
    "lm": 0,
    "ast": 0,
    "pmb": 0,
    "cip": 0,
    "oac": 1,
    "bs": 0,
    "bt": 320,
    "pal": 0,
    "acohz": 50,
    "ec": 0,
    "op": 10,
    "acip": 72,
    "acov": 2491,
    "ot": 999,
    "ip": 72,
    "it": 1,
    "acpss": 0,
    "ta": 0,
    "lps": 0,
    "acpsp": 0,
    "odc": 1,
    "rb": 99,
    "cs": 0,
    "sfc": 0,
    "sltb": 3,
    "pm": 0,
    "last_updated": "2026-03-26T01:00:00+00:00",
}


def test_explorer_240_only_exposes_supported_entities() -> None:
    platforms = supported_keys_by_platform(EXPLORER_240_PROPERTIES)

    assert platforms["switch"] == ("oac", "odc", "sfc")
    assert platforms["select"] == ("lm", "cs", "lps")
    assert platforms["number"] == ("ast", "pm", "sltb")
    assert "odcu" not in platforms["switch"]
    assert "odcc" not in platforms["switch"]
    assert "wss" not in platforms["binary_sensor"]


def test_devices_with_separate_outputs_get_their_own_controls() -> None:
    properties = {
        "oac": 1,
        "odcu": 1,
        "odcc": 0,
        "odc": 1,
        "iac": 0,
        "idc": 1,
        "ups": 0,
        "wss": 1,
        "lm": 2,
        "last_updated": "2026-03-26T01:00:00+00:00",
    }

    platforms = supported_keys_by_platform(properties)

    assert platforms["switch"] == ("oac", "odc", "odcu", "odcc", "iac", "idc", "ups")
    assert platforms["binary_sensor"] == ("wss",)


def test_expected_unique_ids_match_supported_capabilities() -> None:
    unique_ids = expected_unique_ids("474359726516207616", EXPLORER_240_PROPERTIES)

    assert "474359726516207616_oac" in unique_ids
    assert "474359726516207616_odc" in unique_ids
    assert "474359726516207616_sfc" in unique_ids
    assert "474359726516207616_odcu" not in unique_ids
    assert "474359726516207616_odcc" not in unique_ids


def test_expected_entity_domain_tracks_platform_migrations() -> None:
    assert expected_entity_domain_for_key("oac") == "switch"
    assert expected_entity_domain_for_key("odc") == "switch"
    assert expected_entity_domain_for_key("ta") == "binary_sensor"
    assert expected_entity_domain_for_key("lm") == "select"
    assert expected_entity_domain_for_key("ast") == "number"
    assert expected_entity_domain_for_key("unknown") is None
