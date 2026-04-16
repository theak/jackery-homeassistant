"""Regression tests for optimistic coordinator state updates."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "jackery"


def load_module(module_name: str, path: Path):
    """Load a module directly from the repository."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def install_homeassistant_stubs() -> None:
    """Install the minimal Home Assistant surface needed for unit tests."""
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

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.switch"] = switch_mod
    sys.modules["homeassistant.components.select"] = select_mod
    sys.modules["homeassistant.components.number"] = number_mod
    sys.modules["homeassistant.config_entries"] = config_entries_mod
    sys.modules["homeassistant.const"] = const_mod
    sys.modules["homeassistant.core"] = core_mod
    sys.modules["homeassistant.exceptions"] = exceptions_mod
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.entity"] = entity_mod
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform_mod
    sys.modules["homeassistant.helpers.update_coordinator"] = (
        update_coordinator_mod
    )


def install_package_stubs() -> None:
    """Install the minimal Jackery package structure for relative imports."""
    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(REPO_ROOT / "custom_components")]
    jackery = types.ModuleType("custom_components.jackery")
    jackery.__path__ = [str(PACKAGE_ROOT)]

    api_mod = types.ModuleType("custom_components.jackery.api")

    class JackeryAPI:
        """Stub Jackery API type."""

    const_mod = types.ModuleType("custom_components.jackery.const")
    const_mod.DOMAIN = "jackery"

    api_mod.JackeryAPI = JackeryAPI

    sys.modules["custom_components"] = custom_components
    sys.modules["custom_components.jackery"] = jackery
    sys.modules["custom_components.jackery.api"] = api_mod
    sys.modules["custom_components.jackery.const"] = const_mod


install_homeassistant_stubs()
install_package_stubs()
load_module("custom_components.jackery.protocol", PACKAGE_ROOT / "protocol.py")
switch = load_module("custom_components.jackery.switch", PACKAGE_ROOT / "switch.py")
select = load_module("custom_components.jackery.select", PACKAGE_ROOT / "select.py")
number = load_module("custom_components.jackery.number", PACKAGE_ROOT / "number.py")


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

        await entity.async_turn_on()

        api.async_set_device_property.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "ac",
            "on",
        )
        self.assertEqual(original_data, {"oac": 0, "unchanged": 7})
        self.assertEqual(coordinator.updated_data_calls, [{"oac": 1, "unchanged": 7}])
        self.assertIsNot(coordinator.data, original_data)
        self.assertEqual(coordinator.refresh_requests, 1)
        self.assertEqual(entity.write_count, 0)
        self.assertTrue(entity.is_on)

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
        """Number writes should publish the coerced integer value atomically."""
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
            15,
        )
        self.assertEqual(original_data, {"pm": 20, "unchanged": 7})
        self.assertEqual(coordinator.updated_data_calls, [{"pm": 15, "unchanged": 7}])
        self.assertIsNot(coordinator.data, original_data)
        self.assertEqual(coordinator.refresh_requests, 1)
        self.assertEqual(entity.write_count, 0)
        self.assertEqual(entity.native_value, 15.0)


if __name__ == "__main__":
    unittest.main()
