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


def _module_available(module_name: str) -> bool:
    """Return True when a real module is already loaded or importable."""
    if module_name in sys.modules:
        return True

    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


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
    if _module_available("homeassistant"):
        return

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    components = types.ModuleType("homeassistant.components")
    components.__path__ = []
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []

    switch_mod = types.ModuleType("homeassistant.components.switch")
    select_mod = types.ModuleType("homeassistant.components.select")
    number_mod = types.ModuleType("homeassistant.components.number")
    config_entries_mod = types.ModuleType("homeassistant.config_entries")
    const_mod = types.ModuleType("homeassistant.const")
    core_mod = types.ModuleType("homeassistant.core")
    exceptions_mod = types.ModuleType("homeassistant.exceptions")
    entity_mod = types.ModuleType("homeassistant.helpers.entity")
    entity_platform_mod = types.ModuleType("homeassistant.helpers.entity_platform")
    update_coordinator_mod = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class SwitchEntity:
        """Stub switch entity."""

    class SelectEntity:
        """Stub select entity."""

    class NumberEntity:
        """Stub number entity."""

    class NumberMode:
        """Stub number mode enum."""

        BOX = "box"

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

    class CoordinatorEntity:
        """Stub coordinator entity that tracks direct state writes."""

        def __init__(self, coordinator) -> None:
            self.coordinator = coordinator
            self.write_count = 0

        def async_write_ha_state(self) -> None:
            self.write_count += 1

    class DataUpdateCoordinator:
        """Stub data coordinator base type."""

    class UnitOfTime:
        """Stub unit enum."""

        MINUTES = "min"

    switch_mod.SwitchEntity = SwitchEntity
    select_mod.SelectEntity = SelectEntity
    number_mod.NumberEntity = NumberEntity
    number_mod.NumberMode = NumberMode
    config_entries_mod.ConfigEntry = ConfigEntry
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

    _install_stub_module(stubbed_modules, "homeassistant", homeassistant)
    _install_stub_module(stubbed_modules, "homeassistant.components", components)
    _install_stub_module(
        stubbed_modules, "homeassistant.components.switch", switch_mod
    )
    _install_stub_module(
        stubbed_modules, "homeassistant.components.select", select_mod
    )
    _install_stub_module(
        stubbed_modules, "homeassistant.components.number", number_mod
    )
    _install_stub_module(
        stubbed_modules, "homeassistant.config_entries", config_entries_mod
    )
    _install_stub_module(stubbed_modules, "homeassistant.const", const_mod)
    _install_stub_module(stubbed_modules, "homeassistant.core", core_mod)
    _install_stub_module(
        stubbed_modules, "homeassistant.exceptions", exceptions_mod
    )
    _install_stub_module(stubbed_modules, "homeassistant.helpers", helpers)
    _install_stub_module(
        stubbed_modules, "homeassistant.helpers.entity", entity_mod
    )
    _install_stub_module(
        stubbed_modules,
        "homeassistant.helpers.entity_platform",
        entity_platform_mod,
    )
    _install_stub_module(
        stubbed_modules,
        "homeassistant.helpers.update_coordinator",
        update_coordinator_mod,
    )


def install_package_stubs(stubbed_modules: dict[str, object]) -> None:
    """Install the minimal Jackery package structure for relative imports."""
    package_mod = types.ModuleType(TEST_PACKAGE)
    package_mod.__path__ = [str(PACKAGE_ROOT)]

    api_mod = types.ModuleType(f"{TEST_PACKAGE}.api")

    class JackeryAPI:
        """Stub Jackery API type."""

    const_mod = types.ModuleType(f"{TEST_PACKAGE}.const")
    const_mod.DOMAIN = "jackery"

    api_mod.JackeryAPI = JackeryAPI

    _install_stub_module(stubbed_modules, TEST_PACKAGE, package_mod)
    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.api", api_mod)
    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.const", const_mod)

stubbed_modules: dict[str, object] = {}
install_homeassistant_stubs(stubbed_modules)
install_package_stubs(stubbed_modules)
load_module(
    f"{TEST_PACKAGE}.protocol",
    PACKAGE_ROOT / "protocol.py",
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


def tearDownModule() -> None:
    """Restore sys.modules entries replaced by test-only stubs."""
    restore_stubbed_modules(stubbed_modules)


class TrackingCoordinator:
    """Minimal coordinator test double."""

    def __init__(self, data: dict[str, object]) -> None:
        self.data = data
        self.updated_data_calls: list[dict[str, object]] = []
        self.refresh_requests = 0

    def async_set_updated_data(self, data: dict[str, object]) -> None:
        self.updated_data_calls.append(data)
        self.data = data

    async def async_request_refresh(self) -> None:
        self.refresh_requests += 1


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

    def test_writable_entities_use_base_name_handling(self) -> None:
        """Writable entities should rely on _attr_name/base entity naming."""
        self.assertNotIn("name", switch.JackerySwitchEntity.__dict__)
        self.assertNotIn("name", select.JackerySelectEntity.__dict__)
        self.assertNotIn("name", number.JackeryNumberEntity.__dict__)

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


if __name__ == "__main__":
    unittest.main()
