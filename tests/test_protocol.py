"""Tests for Jackery protocol helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPO_ROOT / "custom_components" / "jackery" / "protocol.py"


def load_protocol_module():
    """Load the protocol helper without importing Home Assistant modules."""
    spec = importlib.util.spec_from_file_location("jackery_protocol", PROTOCOL_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(spec.name)
    sys.modules[spec.name] = module
    try:
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_module is None:
            sys.modules.pop(spec.name, None)
        else:
            sys.modules[spec.name] = previous_module


protocol = load_protocol_module()


class ProtocolTests(unittest.TestCase):
    """Validate control metadata and capability detection."""

    def test_load_protocol_module_cleans_up_temporary_sys_modules_entry(self) -> None:
        """Loading the helper should not leak its temporary import alias."""
        sys.modules.pop("jackery_protocol", None)

        module = load_protocol_module()

        self.assertEqual(module.__name__, "jackery_protocol")
        self.assertNotIn("jackery_protocol", sys.modules)

    def test_load_protocol_module_restores_previous_sys_modules_entry(self) -> None:
        """Existing module entries should be restored after loading."""
        existing_module = types.ModuleType("jackery_protocol")
        sys.modules["jackery_protocol"] = existing_module
        self.addCleanup(sys.modules.pop, "jackery_protocol", None)

        module = load_protocol_module()

        self.assertEqual(module.__name__, "jackery_protocol")
        self.assertIs(sys.modules["jackery_protocol"], existing_module)

    def test_control_specs_match_known_jackery_write_slugs(self) -> None:
        """Confirmed writable controls should preserve the correct API slug."""
        expected = {
            "oac": "ac",
            "odc": "dc",
            "odcu": "usb",
            "odcc": "car",
            "sfc": "sfc",
            "lm": "light",
            "cs": "charge-speed",
            "lps": "battery-protection",
            "ast": "auto-shutdown",
            "pm": "energy-saving",
            "sltb": "screen-timeout",
        }

        actual = {
            key: protocol.control_spec(key).slug
            for key in expected
        }
        self.assertEqual(actual, expected)

    def test_combined_dc_output_suppresses_split_outputs(self) -> None:
        """Devices with only combined DC should not expose USB/car controls."""
        properties = {"odc": 1}

        self.assertEqual(
            protocol.supported_keys(properties, ("odc", "odcu", "odcc")),
            ("odc",),
        )
        self.assertTrue(protocol.is_supported_property(properties, "odc"))
        self.assertFalse(protocol.is_supported_property(properties, "odcu"))
        self.assertFalse(protocol.is_supported_property(properties, "odcc"))

    def test_split_dc_outputs_suppress_combined_toggle(self) -> None:
        """Devices with dedicated USB/car controls should hide combined DC."""
        properties = {"odc": 1, "odcu": 0, "odcc": 1}

        self.assertEqual(
            protocol.supported_keys(properties, ("odc", "odcu", "odcc")),
            ("odcu", "odcc"),
        )
        self.assertFalse(protocol.is_supported_property(properties, "odc"))

    def test_screen_timeout_accepts_alias_read_key(self) -> None:
        """Some code paths refer to screen timeout as slt rather than sltb."""
        self.assertTrue(protocol.is_supported_property({"sltb": 30}, "sltb"))
        self.assertTrue(protocol.is_supported_property({"slt": 30}, "sltb"))

    def test_new_controls_only_show_when_reported(self) -> None:
        """Recovered controls should be filtered directly from reported properties."""
        properties = {
            "oac": 1,
            "sfc": 0,
            "lm": 2,
            "cs": 1,
            "lps": 0,
            "ast": 30,
            "pm": 20,
            "sltb": 15,
        }

        self.assertEqual(
            protocol.supported_keys(
                properties,
                ("oac", "sfc", "lm", "cs", "lps", "ast", "pm", "sltb"),
            ),
            ("oac", "sfc", "lm", "cs", "lps", "ast", "pm", "sltb"),
        )
        self.assertFalse(protocol.is_supported_property(properties, "charging_plan"))


if __name__ == "__main__":
    unittest.main()
