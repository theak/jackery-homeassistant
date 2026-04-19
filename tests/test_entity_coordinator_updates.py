"""Regression tests for optimistic coordinator state updates."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "jackery"
TEST_PACKAGE = "jackery_entity_updates_test"
_MISSING = object()


def load_module(module_name: str, path: Path, stubbed_modules: dict[str, object]):
    """Load a module directly from the repository."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    _install_stub_module(stubbed_modules, module_name, module)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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
    """Install the minimal Home Assistant surface needed for unit tests."""
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
    helpers = ensure_module("homeassistant.helpers", package=True)

    switch_mod = ensure_module("homeassistant.components.switch")
    select_mod = ensure_module("homeassistant.components.select")
    number_mod = ensure_module("homeassistant.components.number")
    sensor_mod = ensure_module("homeassistant.components.sensor")
    binary_sensor_mod = ensure_module("homeassistant.components.binary_sensor")
    text_mod = ensure_module("homeassistant.components.text")
    config_entries_mod = ensure_module("homeassistant.config_entries")
    const_mod = ensure_module("homeassistant.const")
    core_mod = ensure_module("homeassistant.core")
    exceptions_mod = ensure_module("homeassistant.exceptions")
    entity_mod = ensure_module("homeassistant.helpers.entity")
    entity_platform_mod = ensure_module("homeassistant.helpers.entity_platform")
    update_coordinator_mod = ensure_module("homeassistant.helpers.update_coordinator")

    class SwitchEntity:
        """Stub switch entity."""

    class SelectEntity:
        """Stub select entity."""

    class NumberEntity:
        """Stub number entity."""

    class SensorEntity:
        """Stub sensor entity."""

    class BinarySensorEntity:
        """Stub binary sensor entity."""

    class TextEntity:
        """Stub text entity."""

    class NumberMode:
        """Stub number mode enum."""

        BOX = "box"

    class TextMode:
        """Stub text mode enum."""

        TEXT = "text"

    class ConfigEntry:
        """Stub config entry."""

    class HomeAssistant:
        """Stub Home Assistant object."""

    class HomeAssistantError(Exception):
        """Stub Home Assistant exception."""

    @dataclass
    class DeviceInfo:
        """Stub device info object."""

        identifiers: object
        name: str | None = None
        manufacturer: str | None = None
        model: str | None = None

    @dataclass
    class EntityDescription:
        """Stub entity description."""

        key: str
        name: str | None = None
        icon: str | None = None

    @dataclass
    class SensorEntityDescription(EntityDescription):
        """Stub sensor entity description."""

        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        state_class: str | None = None
        entity_category: str | None = None

    @dataclass
    class BinarySensorEntityDescription(EntityDescription):
        """Stub binary sensor entity description."""

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

    class BinarySensorDeviceClass:
        """Stub binary sensor device class enum."""

        POWER = "power"
        PROBLEM = "problem"

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

    class CoordinatorEntity:
        """Stub coordinator entity that tracks direct state writes."""

        def __init__(self, coordinator) -> None:
            self.coordinator = coordinator
            self.write_count = 0

        @property
        def available(self) -> bool:
            return True

        def async_write_ha_state(self) -> None:
            self.write_count += 1

    class DataUpdateCoordinator:
        """Stub data coordinator base type."""

    class UnitOfTime:
        """Stub unit enum."""

        MINUTES = "min"
        HOURS = "h"

    switch_mod.SwitchEntity = SwitchEntity
    select_mod.SelectEntity = SelectEntity
    number_mod.NumberEntity = NumberEntity
    sensor_mod.SensorEntity = SensorEntity
    sensor_mod.SensorEntityDescription = SensorEntityDescription
    sensor_mod.SensorDeviceClass = SensorDeviceClass
    sensor_mod.SensorStateClass = SensorStateClass
    binary_sensor_mod.BinarySensorEntity = BinarySensorEntity
    binary_sensor_mod.BinarySensorEntityDescription = BinarySensorEntityDescription
    binary_sensor_mod.BinarySensorDeviceClass = BinarySensorDeviceClass
    number_mod.NumberMode = NumberMode
    text_mod.TextEntity = TextEntity
    text_mod.TextMode = TextMode
    config_entries_mod.ConfigEntry = ConfigEntry
    const_mod.EntityCategory = EntityCategory
    const_mod.PERCENTAGE = "%"
    const_mod.UnitOfElectricPotential = UnitOfElectricPotential
    const_mod.UnitOfFrequency = UnitOfFrequency
    const_mod.UnitOfPower = UnitOfPower
    const_mod.UnitOfTemperature = UnitOfTemperature
    const_mod.UnitOfTime = UnitOfTime
    core_mod.HomeAssistant = HomeAssistant
    exceptions_mod.HomeAssistantError = HomeAssistantError
    entity_mod.DeviceInfo = DeviceInfo
    entity_mod.EntityDescription = EntityDescription
    entity_platform_mod.AddEntitiesCallback = object
    update_coordinator_mod.CoordinatorEntity = CoordinatorEntity
    update_coordinator_mod.DataUpdateCoordinator = DataUpdateCoordinator

    homeassistant.components = components
    homeassistant.helpers = helpers
    components.switch = switch_mod
    components.select = select_mod
    components.number = number_mod
    components.sensor = sensor_mod
    components.binary_sensor = binary_sensor_mod
    components.text = text_mod
    helpers.entity = entity_mod
    helpers.entity_platform = entity_platform_mod
    helpers.update_coordinator = update_coordinator_mod


def install_package_stubs(stubbed_modules: dict[str, object]) -> None:
    """Install the minimal Jackery package structure for relative imports."""
    package_mod = types.ModuleType(TEST_PACKAGE)
    package_mod.__path__ = [str(PACKAGE_ROOT)]

    api_mod = types.ModuleType(f"{TEST_PACKAGE}.api")

    class JackeryAPI:
        """Stub Jackery API type."""

    api_mod.JackeryAPI = JackeryAPI

    _install_stub_module(stubbed_modules, TEST_PACKAGE, package_mod)
    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.api", api_mod)


stubbed_modules: dict[str, object] = {}
install_homeassistant_stubs(stubbed_modules)
install_package_stubs(stubbed_modules)
load_module(
    f"{TEST_PACKAGE}.const",
    PACKAGE_ROOT / "const.py",
    stubbed_modules,
)
load_module(
    f"{TEST_PACKAGE}.protocol",
    PACKAGE_ROOT / "protocol.py",
    stubbed_modules,
)
sensor = load_module(
    f"{TEST_PACKAGE}.sensor",
    PACKAGE_ROOT / "sensor.py",
    stubbed_modules,
)
binary_sensor = load_module(
    f"{TEST_PACKAGE}.binary_sensor",
    PACKAGE_ROOT / "binary_sensor.py",
    stubbed_modules,
)
switch = load_module(
    f"{TEST_PACKAGE}.switch",
    PACKAGE_ROOT / "switch.py",
    stubbed_modules,
)
select = load_module(
    f"{TEST_PACKAGE}.select",
    PACKAGE_ROOT / "select.py",
    stubbed_modules,
)
number = load_module(
    f"{TEST_PACKAGE}.number",
    PACKAGE_ROOT / "number.py",
    stubbed_modules,
)
text = load_module(
    f"{TEST_PACKAGE}.text",
    PACKAGE_ROOT / "text.py",
    stubbed_modules,
)


def tearDownModule() -> None:
    """Restore sys.modules entries replaced by test-only stubs."""
    restore_stubbed_modules(stubbed_modules)


class TrackingCoordinator:
    """Minimal coordinator test double."""

    def __init__(self, data: dict[str, object]) -> None:
        self.data = data
        self.updated_data_calls: list[dict[str, object]] = []
        self.refresh_requests = 0
        self.listeners: list[object] = []

    def async_set_updated_data(self, data: dict[str, object]) -> None:
        self.updated_data_calls.append(data)
        self.data = data
        for listener in tuple(self.listeners):
            listener()

    async def async_request_refresh(self) -> None:
        self.refresh_requests += 1

    def async_add_listener(self, listener):
        self.listeners.append(listener)

        def _remove_listener() -> None:
            if listener in self.listeners:
                self.listeners.remove(listener)

        return _remove_listener


class CoordinatorUpdateTests(unittest.IsolatedAsyncioTestCase):
    """Verify writable entities publish copied coordinator snapshots."""

    device_info = {
        "devId": "device-1",
        "devSn": "serial-1",
        "devName": "Jackery Explorer",
        "productType": "Explorer 1000",
    }

    async def test_switch_updates_coordinator_with_copied_snapshot(self) -> None:
        """Switch writes should publish a copied payload and request refresh."""
        original_data = {"oac": 0, "unchanged": 7}
        coordinator = TrackingCoordinator(original_data)
        api = types.SimpleNamespace(async_set_device_property=AsyncMock())
        entity = switch.JackerySwitchEntity(
            api=api,
            coordinator=coordinator,
            description=switch.SWITCH_DESCRIPTIONS["oac"],
            device_info=self.device_info,
        )

        self.assertEqual(entity._attr_unique_id, "device-1_switch_oac")

        await entity.async_turn_on()

        api.async_set_device_property.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "ac",
            1,
        )
        self.assertEqual(original_data, {"oac": 0, "unchanged": 7})
        self.assertEqual(coordinator.updated_data_calls, [{"oac": 1, "unchanged": 7}])
        self.assertIsNot(coordinator.data, original_data)
        self.assertEqual(coordinator.refresh_requests, 1)
        self.assertEqual(entity.write_count, 0)
        self.assertTrue(entity.is_on)

    async def test_switch_turn_off_uses_numeric_payload(self) -> None:
        """Switch off writes should send the raw integer state."""
        coordinator = TrackingCoordinator({"oac": 1, "unchanged": 7})
        api = types.SimpleNamespace(async_set_device_property=AsyncMock())
        entity = switch.JackerySwitchEntity(
            api=api,
            coordinator=coordinator,
            description=switch.SWITCH_DESCRIPTIONS["oac"],
            device_info=self.device_info,
        )

        await entity.async_turn_off()

        api.async_set_device_property.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "ac",
            0,
        )
        self.assertEqual(coordinator.updated_data_calls, [{"oac": 0, "unchanged": 7}])
        self.assertFalse(entity.is_on)

    async def test_select_updates_coordinator_with_copied_snapshot(self) -> None:
        """Select writes should publish the new option index atomically."""
        original_data = {"lm": 0, "unchanged": 7}
        coordinator = TrackingCoordinator(original_data)
        api = types.SimpleNamespace(async_set_device_property=AsyncMock())
        entity = select.JackerySelectEntity(
            api=api,
            coordinator=coordinator,
            description=select.SELECT_DESCRIPTIONS["lm"],
            device_info=self.device_info,
        )

        await entity.async_select_option("high")

        api.async_set_device_property.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "light",
            "high",
        )
        self.assertEqual(original_data, {"lm": 0, "unchanged": 7})
        self.assertEqual(coordinator.updated_data_calls, [{"lm": 2, "unchanged": 7}])
        self.assertIsNot(coordinator.data, original_data)
        self.assertEqual(coordinator.refresh_requests, 1)
        self.assertEqual(entity.write_count, 0)
        self.assertEqual(entity.current_option, "high")

    async def test_number_updates_coordinator_with_copied_snapshot(self) -> None:
        """Number writes should publish the normalized integer value atomically."""
        original_data = {"pm": 20, "unchanged": 7}
        coordinator = TrackingCoordinator(original_data)
        api = types.SimpleNamespace(async_set_device_property=AsyncMock())
        entity = number.JackeryNumberEntity(
            api=api,
            coordinator=coordinator,
            description=number.NUMBER_DESCRIPTIONS["pm"],
            device_info=self.device_info,
        )

        await entity.async_set_native_value(15.8)

        api.async_set_device_property.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "energy-saving",
            16,
        )
        self.assertEqual(original_data, {"pm": 20, "unchanged": 7})
        self.assertEqual(coordinator.updated_data_calls, [{"pm": 16, "unchanged": 7}])
        self.assertIsNot(coordinator.data, original_data)
        self.assertEqual(coordinator.refresh_requests, 1)
        self.assertEqual(entity.write_count, 0)
        self.assertEqual(entity.native_value, 16.0)

    async def test_number_clamps_values_to_supported_range(self) -> None:
        """Number writes should clamp out-of-range values before publishing."""
        coordinator = TrackingCoordinator({"pm": 20})
        api = types.SimpleNamespace(async_set_device_property=AsyncMock())
        entity = number.JackeryNumberEntity(
            api=api,
            coordinator=coordinator,
            description=number.NUMBER_DESCRIPTIONS["pm"],
            device_info=self.device_info,
        )

        await entity.async_set_native_value(2000)

        api.async_set_device_property.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "energy-saving",
            1440,
        )
        self.assertEqual(coordinator.updated_data_calls, [{"pm": 1440}])
        self.assertEqual(entity.native_value, 1440.0)

    async def test_read_only_platforms_add_late_supported_entities(self) -> None:
        """Sensors and binary sensors should appear when their keys arrive later."""
        device = dict(self.device_info)
        entry_id = "entry-1"

        async def collect_entities(module, coordinator_data):
            added: list[object] = []
            coordinator = TrackingCoordinator(coordinator_data)
            hass = types.SimpleNamespace(
                data={
                    "jackery": {
                        entry_id: {
                            "coordinators": {"device-1": coordinator},
                            "devices": [device],
                        }
                    }
                }
            )
            entry = types.SimpleNamespace(entry_id=entry_id)
            await module.async_setup_entry(hass, entry, added.extend)
            return added, coordinator

        added, coordinator = await collect_entities(sensor, {"rb": 80})
        self.assertEqual([entity.entity_description.key for entity in added], ["rb"])
        coordinator.async_set_updated_data(
            {
                "rb": 80,
                "bs": 1,
                "cip": 145,
                "acohz": 50,
                "ec": 0,
            }
        )
        self.assertEqual(
            [entity.entity_description.key for entity in added],
            ["rb", "cip", "acohz", "ec", "bs"],
        )
        coordinator.async_set_updated_data(
            {
                "rb": 80,
                "bs": 1,
                "cip": 145,
                "acohz": 50,
                "ec": 0,
                "pmb": 1,
            }
        )
        self.assertEqual(
            [entity.entity_description.key for entity in added],
            ["rb", "cip", "acohz", "ec", "bs", "pmb"],
        )
        coordinator.async_set_updated_data(
            {
                "rb": 80,
                "bs": 1,
                "cip": 145,
                "acohz": 50,
                "ec": 0,
                "pmb": 1,
            }
        )
        self.assertEqual(
            [entity.entity_description.key for entity in added],
            ["rb", "cip", "acohz", "ec", "bs", "pmb"],
        )

        added, coordinator = await collect_entities(binary_sensor, {"oac": 1})
        self.assertEqual([entity.entity_description.key for entity in added], ["oac"])
        coordinator.async_set_updated_data({"oac": 1, "ta": 0})
        self.assertEqual(
            [entity.entity_description.key for entity in added],
            ["oac", "ta"],
        )
        coordinator.async_set_updated_data({"oac": 1, "ta": 0, "pal": 1})
        self.assertEqual(
            [entity.entity_description.key for entity in added],
            ["oac", "ta", "pal"],
        )

    async def test_read_only_late_entities_track_each_device_independently(self) -> None:
        """Late read-only entity registration should be isolated per device."""
        coordinator_one = TrackingCoordinator({})
        coordinator_two = TrackingCoordinator({})
        added: list[object] = []
        hass = types.SimpleNamespace(
            data={
                "jackery": {
                    "entry-1": {
                        "coordinators": {
                            "device-1": coordinator_one,
                            "device-2": coordinator_two,
                        },
                        "devices": [
                            dict(self.device_info),
                            {
                                **self.device_info,
                                "devId": "device-2",
                                "devSn": "serial-2",
                                "devName": "Jackery Explorer 2",
                            },
                        ],
                    }
                }
            }
        )
        entry = types.SimpleNamespace(entry_id="entry-1")

        await sensor.async_setup_entry(hass, entry, added.extend)

        coordinator_one.async_set_updated_data({"bs": 1})
        self.assertEqual(
            [(entity._device_id, entity.entity_description.key) for entity in added],
            [("device-1", "bs")],
        )

        coordinator_two.async_set_updated_data({"bs": 2, "acohz": 50})
        self.assertEqual(
            [(entity._device_id, entity.entity_description.key) for entity in added],
            [("device-1", "bs"), ("device-2", "acohz"), ("device-2", "bs")],
        )

    async def test_charging_plan_switch_updates_coordinator_snapshot(self) -> None:
        """Charging-plan switch writes should use the raw DP helper."""
        original_data = {"107": 0, "108": "22:00-06:00,1111111", "unchanged": 7}
        coordinator = TrackingCoordinator(original_data)
        api = types.SimpleNamespace(async_set_device_dp=AsyncMock())
        entity = switch.JackeryChargingPlanSwitchEntity(
            api=api,
            coordinator=coordinator,
            description=switch.CHARGING_PLAN_SWITCH_DESCRIPTION,
            device_info=self.device_info,
        )

        await entity.async_turn_on()

        api.async_set_device_dp.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "107",
            1,
        )
        self.assertEqual(original_data, {"107": 0, "108": "22:00-06:00,1111111", "unchanged": 7})
        self.assertEqual(
            coordinator.updated_data_calls,
            [{"107": 1, "108": "22:00-06:00,1111111", "unchanged": 7}],
        )
        self.assertTrue(entity.is_on)

    async def test_charging_plan_time_preserves_repeat_mask(self) -> None:
        """Time writes should replace only the time segment of DP108."""
        original_data = {"107": 1, "108": "22:00-06:00,0111110", "unchanged": 7}
        coordinator = TrackingCoordinator(original_data)
        api = types.SimpleNamespace(async_set_device_dp=AsyncMock())
        entity = text.JackeryChargingPlanTimeEntity(
            api=api,
            coordinator=coordinator,
            description=text.CHARGING_PLAN_TIME_DESCRIPTION,
            device_info=self.device_info,
        )

        await entity.async_set_value("23:30-05:30")

        api.async_set_device_dp.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "108",
            "23:30-05:30,0111110",
        )
        self.assertEqual(
            coordinator.updated_data_calls,
            [{"107": 1, "108": "23:30-05:30,0111110", "unchanged": 7}],
        )
        self.assertEqual(entity.native_value, "23:30-05:30")

    async def test_charging_plan_repeat_preserves_time_range(self) -> None:
        """Repeat writes should replace only the repeat segment of DP108."""
        original_data = {"107": 1, "108": "22:00-06:00,0111110", "unchanged": 7}
        coordinator = TrackingCoordinator(original_data)
        api = types.SimpleNamespace(async_set_device_dp=AsyncMock())
        entity = select.JackeryChargingPlanRepeatEntity(
            api=api,
            coordinator=coordinator,
            description=select.CHARGING_PLAN_REPEAT_DESCRIPTION,
            device_info=self.device_info,
        )

        await entity.async_select_option("Weekends")

        api.async_set_device_dp.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "108",
            "22:00-06:00,1000001",
        )
        self.assertEqual(
            coordinator.updated_data_calls,
            [{"107": 1, "108": "22:00-06:00,1000001", "unchanged": 7}],
        )
        self.assertEqual(entity.current_option, "Weekends")

    async def test_charging_plan_entities_reject_malformed_dp108(self) -> None:
        """Malformed charging-plan payloads should make dependent entities unavailable."""
        coordinator = TrackingCoordinator({"107": 1, "108": "bad-value"})
        time_entity = text.JackeryChargingPlanTimeEntity(
            api=types.SimpleNamespace(async_set_device_dp=AsyncMock()),
            coordinator=coordinator,
            description=text.CHARGING_PLAN_TIME_DESCRIPTION,
            device_info=self.device_info,
        )
        repeat_entity = select.JackeryChargingPlanRepeatEntity(
            api=types.SimpleNamespace(async_set_device_dp=AsyncMock()),
            coordinator=coordinator,
            description=select.CHARGING_PLAN_REPEAT_DESCRIPTION,
            device_info=self.device_info,
        )

        self.assertFalse(time_entity.available)
        self.assertIsNone(time_entity.native_value)
        self.assertFalse(repeat_entity.available)
        self.assertIsNone(repeat_entity.current_option)

        with self.assertRaises(sys.modules["homeassistant.exceptions"].HomeAssistantError):
            await time_entity.async_set_value("22:00-06:00")
        with self.assertRaises(sys.modules["homeassistant.exceptions"].HomeAssistantError):
            await repeat_entity.async_select_option("Everyday")

    def test_writable_entities_use_base_name_handling(self) -> None:
        """Writable entities should rely on _attr_name/base entity naming."""
        self.assertNotIn("name", switch.JackerySwitchEntity.__dict__)
        self.assertNotIn("name", select.JackerySelectEntity.__dict__)
        self.assertNotIn("name", number.JackeryNumberEntity.__dict__)
        self.assertNotIn("name", text.JackeryChargingPlanTimeEntity.__dict__)

    async def test_switch_does_not_wrap_cancellation(self) -> None:
        """Switch writes should propagate cancellation errors unchanged."""
        coordinator = TrackingCoordinator({"oac": 0})
        api = types.SimpleNamespace(
            async_set_device_property=AsyncMock(side_effect=asyncio.CancelledError())
        )
        entity = switch.JackerySwitchEntity(
            api=api,
            coordinator=coordinator,
            description=switch.SWITCH_DESCRIPTIONS["oac"],
            device_info=self.device_info,
        )

        with self.assertRaises(asyncio.CancelledError):
            await entity.async_turn_on()

        self.assertEqual(coordinator.updated_data_calls, [])
        self.assertEqual(coordinator.refresh_requests, 0)

    async def test_select_does_not_wrap_cancellation(self) -> None:
        """Select writes should propagate cancellation errors unchanged."""
        coordinator = TrackingCoordinator({"lm": 0})
        api = types.SimpleNamespace(
            async_set_device_property=AsyncMock(side_effect=asyncio.CancelledError())
        )
        entity = select.JackerySelectEntity(
            api=api,
            coordinator=coordinator,
            description=select.SELECT_DESCRIPTIONS["lm"],
            device_info=self.device_info,
        )

        with self.assertRaises(asyncio.CancelledError):
            await entity.async_select_option("high")

        self.assertEqual(coordinator.updated_data_calls, [])
        self.assertEqual(coordinator.refresh_requests, 0)

    async def test_number_does_not_wrap_cancellation(self) -> None:
        """Number writes should propagate cancellation errors unchanged."""
        coordinator = TrackingCoordinator({"pm": 20})
        api = types.SimpleNamespace(
            async_set_device_property=AsyncMock(side_effect=asyncio.CancelledError())
        )
        entity = number.JackeryNumberEntity(
            api=api,
            coordinator=coordinator,
            description=number.NUMBER_DESCRIPTIONS["pm"],
            device_info=self.device_info,
        )

        with self.assertRaises(asyncio.CancelledError):
            await entity.async_set_native_value(15)

        self.assertEqual(coordinator.updated_data_calls, [])
        self.assertEqual(coordinator.refresh_requests, 0)

    async def test_charging_plan_time_does_not_wrap_cancellation(self) -> None:
        """Charging-plan text writes should propagate cancellation unchanged."""
        coordinator = TrackingCoordinator({"107": 1, "108": "22:00-06:00,1111111"})
        api = types.SimpleNamespace(
            async_set_device_dp=AsyncMock(side_effect=asyncio.CancelledError())
        )
        entity = text.JackeryChargingPlanTimeEntity(
            api=api,
            coordinator=coordinator,
            description=text.CHARGING_PLAN_TIME_DESCRIPTION,
            device_info=self.device_info,
        )

        with self.assertRaises(asyncio.CancelledError):
            await entity.async_set_value("23:00-05:00")

        self.assertEqual(coordinator.updated_data_calls, [])
        self.assertEqual(coordinator.refresh_requests, 0)

    async def test_charging_plan_platforms_wait_for_both_support_keys(self) -> None:
        """Charging-plan entities should appear once both support DPs are reported."""
        api = types.SimpleNamespace(async_set_device_dp=AsyncMock(), async_set_device_property=AsyncMock())
        device = dict(self.device_info)
        entry_id = "entry-1"

        async def collect_entities(module, coordinator_data):
            added: list[object] = []
            coordinator = TrackingCoordinator(coordinator_data)
            hass = types.SimpleNamespace(
                data={
                    "jackery": {
                        entry_id: {
                            "api": api,
                            "coordinators": {"device-1": coordinator},
                            "devices": [device],
                        }
                    }
                }
            )
            entry = types.SimpleNamespace(entry_id=entry_id)
            await module.async_setup_entry(hass, entry, added.extend)
            return added, coordinator

        added, coordinator = await collect_entities(switch, {"107": 1})
        self.assertEqual([type(entity).__name__ for entity in added], [])
        coordinator.async_set_updated_data({"107": 1})
        self.assertEqual([type(entity).__name__ for entity in added], [])
        coordinator.async_set_updated_data({"107": 1, "108": "22:00-06:00,1111111"})
        self.assertEqual(
            [type(entity).__name__ for entity in added],
            ["JackeryChargingPlanSwitchEntity"],
        )
        coordinator.async_set_updated_data({"107": 1, "108": "23:00-05:00,1111111"})
        self.assertEqual(
            [type(entity).__name__ for entity in added],
            ["JackeryChargingPlanSwitchEntity"],
        )

        added, coordinator = await collect_entities(select, {"108": "22:00-06:00,1111111"})
        self.assertEqual(
            [
                type(entity).__name__
                for entity in added
                if type(entity).__name__ == "JackeryChargingPlanRepeatEntity"
            ],
            [],
        )
        coordinator.async_set_updated_data({"108": "22:00-06:00,1111111"})
        self.assertEqual(
            [
                type(entity).__name__
                for entity in added
                if type(entity).__name__ == "JackeryChargingPlanRepeatEntity"
            ],
            [],
        )
        coordinator.async_set_updated_data({"107": 1, "108": "22:00-06:00,1111111"})
        self.assertEqual(
            [
                type(entity).__name__
                for entity in added
                if type(entity).__name__ == "JackeryChargingPlanRepeatEntity"
            ],
            ["JackeryChargingPlanRepeatEntity"],
        )

        added, coordinator = await collect_entities(text, {})
        self.assertEqual([type(entity).__name__ for entity in added], [])
        coordinator.async_set_updated_data({"107": 1})
        self.assertEqual([type(entity).__name__ for entity in added], [])
        coordinator.async_set_updated_data({"107": 1, "108": "22:00-06:00,1111111"})
        self.assertEqual(
            [type(entity).__name__ for entity in added],
            ["JackeryChargingPlanTimeEntity"],
        )

    async def test_deferred_charging_plan_entities_track_each_device_independently(self) -> None:
        """Late charging-plan discovery should add one entity per supporting device."""
        api = types.SimpleNamespace(
            async_set_device_dp=AsyncMock(),
            async_set_device_property=AsyncMock(),
        )
        coordinator_one = TrackingCoordinator({})
        coordinator_two = TrackingCoordinator({})
        added: list[object] = []
        hass = types.SimpleNamespace(
            data={
                "jackery": {
                    "entry-1": {
                        "api": api,
                        "coordinators": {
                            "device-1": coordinator_one,
                            "device-2": coordinator_two,
                        },
                        "devices": [
                            dict(self.device_info),
                            {
                                **self.device_info,
                                "devId": "device-2",
                                "devSn": "serial-2",
                                "devName": "Jackery Explorer 2",
                            },
                        ],
                    }
                }
            }
        )
        entry = types.SimpleNamespace(entry_id="entry-1")

        await switch.async_setup_entry(hass, entry, added.extend)

        coordinator_one.async_set_updated_data({"107": 1, "108": "22:00-06:00,1111111"})
        self.assertEqual(
            [entity._device_id for entity in added],
            ["device-1"],
        )

        coordinator_two.async_set_updated_data({"107": 1, "108": "22:00-06:00,1111111"})
        self.assertEqual(
            [entity._device_id for entity in added],
            ["device-1", "device-2"],
        )


class HomeAssistantStubInstallerTests(unittest.TestCase):
    """Verify Home Assistant test stubs can extend partial installs."""

    def test_install_homeassistant_stubs_adds_missing_modules(self) -> None:
        """A pre-existing partial Home Assistant package should be completed."""
        local_stubbed_modules: dict[str, object] = {}
        homeassistant = types.ModuleType("homeassistant")
        homeassistant.__path__ = []
        helpers = types.ModuleType("homeassistant.helpers")
        helpers.__path__ = []

        _install_stub_module(local_stubbed_modules, "homeassistant", homeassistant)
        _install_stub_module(
            local_stubbed_modules, "homeassistant.helpers", helpers
        )

        try:
            install_homeassistant_stubs(local_stubbed_modules)

            self.assertIs(sys.modules["homeassistant"], homeassistant)
            self.assertIs(homeassistant.helpers, helpers)
            self.assertIn("homeassistant.components.switch", sys.modules)
            self.assertTrue(
                hasattr(sys.modules["homeassistant.const"], "UnitOfTime")
            )
            self.assertTrue(
                hasattr(
                    sys.modules["homeassistant.helpers.update_coordinator"],
                    "CoordinatorEntity",
                )
            )
        finally:
            restore_stubbed_modules(local_stubbed_modules)


if __name__ == "__main__":
    unittest.main()
