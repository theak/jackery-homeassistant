"""Tests for Jackery entity description metadata."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONST_PATH = REPO_ROOT / "custom_components" / "jackery" / "const.py"
_MISSING = object()


def _install_stub_module(
    stubbed_modules: dict[str, object], module_name: str, module: types.ModuleType
) -> None:
    """Install a module and remember the previous sys.modules entry."""
    stubbed_modules.setdefault(module_name, sys.modules.get(module_name, _MISSING))
    sys.modules[module_name] = module


def restore_stubbed_modules(stubbed_modules: dict[str, object]) -> None:
    """Restore any sys.modules entries replaced for this test module."""
    for module_name, previous in reversed(list(stubbed_modules.items())):
        if previous is _MISSING:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous


def install_homeassistant_stubs(stubbed_modules: dict[str, object]) -> None:
    """Install the minimal Home Assistant surface needed for const imports."""

    def ensure_module(
        module_name: str, *, package: bool = False
    ) -> types.ModuleType:
        module = sys.modules.get(module_name)
        if not isinstance(module, types.ModuleType):
            module = types.ModuleType(module_name)
            _install_stub_module(stubbed_modules, module_name, module)
        if package and not hasattr(module, "__path__"):
            module.__path__ = []
        return module

    homeassistant = ensure_module("homeassistant", package=True)
    components = ensure_module("homeassistant.components", package=True)
    binary_sensor_mod = ensure_module("homeassistant.components.binary_sensor")
    sensor_mod = ensure_module("homeassistant.components.sensor")
    const_mod = ensure_module("homeassistant.const")

    class BinarySensorDeviceClass:
        """Stub binary sensor device class enum."""

        POWER = "power"
        PROBLEM = "problem"

    @dataclass
    class BinarySensorEntityDescription:
        """Stub binary sensor description."""

        key: str
        name: str | None = None
        icon: str | None = None
        device_class: str | None = None
        entity_category: str | None = None

    class SensorDeviceClass:
        """Stub sensor device class enum."""

        BATTERY = "battery"
        DURATION = "duration"
        FREQUENCY = "frequency"
        POWER = "power"
        TEMPERATURE = "temperature"
        TIMESTAMP = "timestamp"
        VOLTAGE = "voltage"

    @dataclass
    class SensorEntityDescription:
        """Stub sensor description."""

        key: str
        name: str | None = None
        icon: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        state_class: str | None = None
        entity_category: str | None = None

    class SensorStateClass:
        """Stub sensor state class enum."""

        MEASUREMENT = "measurement"

    class EntityCategory:
        """Stub entity category enum."""

        DIAGNOSTIC = "diagnostic"

    class UnitOfElectricPotential:
        """Stub voltage unit enum."""

        VOLT = "V"

    class UnitOfFrequency:
        """Stub frequency unit enum."""

        HERTZ = "Hz"

    class UnitOfPower:
        """Stub power unit enum."""

        WATT = "W"

    class UnitOfTemperature:
        """Stub temperature unit enum."""

        CELSIUS = "degC"

    class UnitOfTime:
        """Stub time unit enum."""

        HOURS = "h"

    binary_sensor_mod.BinarySensorDeviceClass = BinarySensorDeviceClass
    binary_sensor_mod.BinarySensorEntityDescription = BinarySensorEntityDescription
    sensor_mod.SensorDeviceClass = SensorDeviceClass
    sensor_mod.SensorEntityDescription = SensorEntityDescription
    sensor_mod.SensorStateClass = SensorStateClass
    const_mod.EntityCategory = EntityCategory
    const_mod.PERCENTAGE = "%"
    const_mod.UnitOfElectricPotential = UnitOfElectricPotential
    const_mod.UnitOfFrequency = UnitOfFrequency
    const_mod.UnitOfPower = UnitOfPower
    const_mod.UnitOfTemperature = UnitOfTemperature
    const_mod.UnitOfTime = UnitOfTime

    homeassistant.components = components
    components.binary_sensor = binary_sensor_mod
    components.sensor = sensor_mod


def load_const_module(stubbed_modules: dict[str, object]):
    """Load the const module directly from the repository."""
    spec = importlib.util.spec_from_file_location("jackery_const_test", CONST_PATH)
    module = importlib.util.module_from_spec(spec)
    _install_stub_module(stubbed_modules, spec.name, module)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


stubbed_modules: dict[str, object] = {}
install_homeassistant_stubs(stubbed_modules)
const = load_const_module(stubbed_modules)


def tearDownModule() -> None:
    """Restore sys.modules entries replaced by test-only stubs."""
    restore_stubbed_modules(stubbed_modules)


class EntityDescriptionTests(unittest.TestCase):
    """Validate metadata for the read-only Jackery entities."""

    def test_sensor_descriptions_include_new_live_api_fields(self) -> None:
        """New live properties should have sensor descriptions with the right units."""
        sensors = {
            description.key: description for description in const.SENSOR_DESCRIPTIONS
        }

        self.assertEqual(sensors["ip"].name, "Total Input Power")
        self.assertEqual(sensors["ip"].native_unit_of_measurement, "W")
        self.assertEqual(sensors["ip"].device_class, "power")
        self.assertEqual(sensors["ip"].state_class, "measurement")

        self.assertEqual(sensors["bs"].name, "Battery Status")
        self.assertEqual(sensors["bs"].value(0), "Idle")
        self.assertEqual(sensors["bs"].value(1), "Charging")
        self.assertEqual(sensors["bs"].value(2), "Discharging")
        self.assertEqual(sensors["bs"].value(3), "Fault")

        self.assertEqual(sensors["cip"].name, "DC Input Power")
        self.assertEqual(sensors["cip"].native_unit_of_measurement, "W")
        self.assertEqual(sensors["cip"].device_class, "power")
        self.assertEqual(sensors["cip"].state_class, "measurement")

        self.assertNotIn("acpsp", sensors)

        self.assertEqual(sensors["acohz"].name, "AC Output Frequency")
        self.assertEqual(sensors["acohz"].native_unit_of_measurement, "Hz")
        self.assertEqual(sensors["acohz"].device_class, "frequency")
        self.assertEqual(sensors["acohz"].state_class, "measurement")

        self.assertEqual(sensors["ec"].name, "Error Code")
        self.assertEqual(sensors["ec"].entity_category, "diagnostic")

        self.assertEqual(sensors["pmb"].name, "Parallel Modules Connected")
        self.assertEqual(sensors["pmb"].entity_category, "diagnostic")

    def test_binary_sensor_descriptions_include_new_alarm_fields(self) -> None:
        """Alarm properties should be exposed as diagnostic problem sensors."""
        binary_sensors = {
            description.key: description
            for description in const.BINARY_SENSOR_DESCRIPTIONS
        }

        self.assertNotIn("acpss", binary_sensors)

        self.assertEqual(binary_sensors["ta"].name, "Temperature Alarm")
        self.assertEqual(binary_sensors["ta"].device_class, "problem")
        self.assertEqual(binary_sensors["ta"].entity_category, "diagnostic")

        self.assertEqual(binary_sensors["pal"].name, "Power Alarm")
        self.assertEqual(binary_sensors["pal"].device_class, "problem")
        self.assertEqual(binary_sensors["pal"].entity_category, "diagnostic")


if __name__ == "__main__":
    unittest.main()
