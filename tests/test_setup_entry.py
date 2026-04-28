"""Tests for Jackery config entry setup behavior."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "jackery"
TEST_PACKAGE = "jackery_setup_entry_test"
_MISSING = object()


def load_module(
    module_name: str,
    path: Path,
    stubbed_modules: dict[str, object],
    *,
    package: bool = False,
):
    """Load a module directly from the repository."""
    kwargs = {}
    if package:
        kwargs["submodule_search_locations"] = [str(path.parent)]
    spec = importlib.util.spec_from_file_location(module_name, path, **kwargs)
    module = importlib.util.module_from_spec(spec)
    _install_stub_module(stubbed_modules, module_name, module)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _install_stub_module(
    stubbed_modules: dict[str, object], module_name: str, module: types.ModuleType
) -> None:
    """Install a stub module and remember any previous sys.modules entry."""
    stubbed_modules.setdefault(module_name, sys.modules.get(module_name, _MISSING))
    sys.modules[module_name] = module


def restore_stubbed_modules(stubbed_modules: dict[str, object]) -> None:
    """Restore sys.modules entries replaced while loading the test targets."""
    for module_name, previous in reversed(list(stubbed_modules.items())):
        if previous is _MISSING:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous


def install_homeassistant_stubs(stubbed_modules: dict[str, object]) -> None:
    """Install the minimal Home Assistant surface needed for setup tests."""

    def ensure_stub_module(
        module_name: str, *, package: bool = False
    ) -> types.ModuleType:
        module = sys.modules.get(module_name)
        if not isinstance(module, types.ModuleType):
            module = types.ModuleType(module_name)
            _install_stub_module(stubbed_modules, module_name, module)
        if package and not hasattr(module, "__path__"):
            module.__path__ = []
        return module

    homeassistant = ensure_stub_module("homeassistant", package=True)
    helpers = ensure_stub_module("homeassistant.helpers", package=True)
    util = ensure_stub_module("homeassistant.util", package=True)

    config_entries_mod = ensure_stub_module("homeassistant.config_entries")
    const_mod = ensure_stub_module("homeassistant.const")
    core_mod = ensure_stub_module("homeassistant.core")
    exceptions_mod = ensure_stub_module("homeassistant.exceptions")
    update_coordinator_mod = ensure_stub_module(
        "homeassistant.helpers.update_coordinator"
    )
    dt_mod = ensure_stub_module("homeassistant.util.dt")

    class ConfigEntry:
        """Stub config entry."""

        def __init__(self, entry_id: str, data: dict[str, object]) -> None:
            self.entry_id = entry_id
            self.data = data

    class HomeAssistant:
        """Stub Home Assistant object."""

    class Platform:
        """Stub platform enum."""

        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"
        SWITCH = "switch"
        SELECT = "select"
        NUMBER = "number"
        TEXT = "text"

    class ConfigEntryAuthFailed(Exception):
        """Stub auth failure."""

    class ConfigEntryNotReady(Exception):
        """Stub not-ready failure."""

    class UpdateFailed(Exception):
        """Stub update failure."""

    class DataUpdateCoordinator:
        """Stub coordinator that eagerly runs the refresh callback."""

        instances: list["DataUpdateCoordinator"] = []

        def __init__(
            self,
            hass,
            logger,
            *,
            name,
            update_method,
            update_interval,
        ) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_method = update_method
            self.update_interval = update_interval
            self.data = None
            type(self).instances.append(self)

        async def async_config_entry_first_refresh(self) -> None:
            self.data = await self.update_method()

    config_entries_mod.ConfigEntry = ConfigEntry
    const_mod.CONF_PASSWORD = "password"
    const_mod.CONF_USERNAME = "username"
    const_mod.Platform = Platform
    core_mod.HomeAssistant = HomeAssistant
    exceptions_mod.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    exceptions_mod.ConfigEntryNotReady = ConfigEntryNotReady
    update_coordinator_mod.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator_mod.UpdateFailed = UpdateFailed
    dt_mod.now = lambda: "2026-04-18T19:00:00+01:00"

    homeassistant.helpers = helpers
    homeassistant.util = util
    helpers.update_coordinator = update_coordinator_mod
    util.dt = dt_mod


def install_package_stubs(stubbed_modules: dict[str, object]) -> None:
    """Install the minimal Jackery package structure for relative imports."""
    package_mod = types.ModuleType(TEST_PACKAGE)
    package_mod.__path__ = [str(PACKAGE_ROOT)]
    _install_stub_module(stubbed_modules, TEST_PACKAGE, package_mod)

    const_mod = types.ModuleType(f"{TEST_PACKAGE}.const")
    const_mod.DOMAIN = "jackery"
    const_mod.POLLING_INTERVAL_SEC = 60

    api_mod = types.ModuleType(f"{TEST_PACKAGE}.api")

    class JackeryAuthenticationError(Exception):
        """Stub Jackery auth failure."""

    class JackeryAPI:
        """Configurable API stub used by setup-entry tests."""

        device_list_result: dict[str, object] = {"data": []}
        device_list_error: Exception | None = None
        device_detail_results: dict[str, dict[str, object]] = {}
        device_detail_error: Exception | None = None
        instances: list["JackeryAPI"] = []

        def __init__(self, account: str, password: str) -> None:
            self.account = account
            self.password = password
            type(self).instances.append(self)

        def get_device_list(self) -> dict[str, object]:
            if type(self).device_list_error is not None:
                raise type(self).device_list_error
            return type(self).device_list_result

        def get_device_detail(self, device_id: str) -> dict[str, object]:
            if type(self).device_detail_error is not None:
                raise type(self).device_detail_error
            return type(self).device_detail_results[device_id]

        async def async_close(self) -> None:
            """Close the stub API client."""

        @classmethod
        def reset(cls) -> None:
            """Reset the stub API state between tests."""
            cls.device_list_result = {"data": []}
            cls.device_list_error = None
            cls.device_detail_results = {}
            cls.device_detail_error = None
            cls.instances = []

    api_mod.JackeryAPI = JackeryAPI
    api_mod.JackeryAuthenticationError = JackeryAuthenticationError

    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.const", const_mod)
    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.api", api_mod)


stubbed_modules: dict[str, object] = {}
install_homeassistant_stubs(stubbed_modules)
install_package_stubs(stubbed_modules)
integration = load_module(
    TEST_PACKAGE,
    PACKAGE_ROOT / "__init__.py",
    stubbed_modules,
    package=True,
)
api = sys.modules[f"{TEST_PACKAGE}.api"]


def tearDownModule() -> None:
    """Restore sys.modules entries replaced by test-only stubs."""
    restore_stubbed_modules(stubbed_modules)


class AsyncSetupEntryTests(unittest.IsolatedAsyncioTestCase):
    """Validate config entry setup error handling and coordinator refreshes."""

    def setUp(self) -> None:
        api.JackeryAPI.reset()
        integration.DataUpdateCoordinator.instances = []
        integration.dt_util.now = lambda: "2026-04-18T19:00:00+01:00"

    @staticmethod
    def _make_hass():
        """Create a minimal Home Assistant stub."""
        return types.SimpleNamespace(
            data={},
            async_add_executor_job=AsyncMock(side_effect=lambda func, *args: func(*args)),
            config_entries=types.SimpleNamespace(
                async_forward_entry_setups=AsyncMock(),
                async_unload_platforms=AsyncMock(return_value=True),
            ),
        )

    @staticmethod
    def _make_entry():
        """Create a minimal config entry stub."""
        return types.SimpleNamespace(
            entry_id="entry-1",
            data={"username": "user@example.com", "password": "hunter2"},
        )

    async def test_setup_entry_raises_auth_failed_when_device_list_auth_fails(
        self,
    ) -> None:
        """Authentication failures should trigger Home Assistant reauth handling."""
        hass = self._make_hass()
        entry = self._make_entry()
        api.JackeryAPI.device_list_error = api.JackeryAuthenticationError("bad creds")

        with self.assertRaises(integration.ConfigEntryAuthFailed):
            await integration.async_setup_entry(hass, entry)

        hass.config_entries.async_forward_entry_setups.assert_not_awaited()

    async def test_setup_entry_raises_not_ready_for_transient_device_list_failure(
        self,
    ) -> None:
        """Transient device list failures should tell Home Assistant to retry."""
        hass = self._make_hass()
        entry = self._make_entry()
        api.JackeryAPI.device_list_error = RuntimeError("cloud offline")

        with self.assertRaises(integration.ConfigEntryNotReady):
            await integration.async_setup_entry(hass, entry)

        hass.config_entries.async_forward_entry_setups.assert_not_awaited()

    async def test_setup_entry_succeeds_without_devices(self) -> None:
        """An empty account should stay loaded instead of failing setup outright."""
        hass = self._make_hass()
        entry = self._make_entry()

        result = await integration.async_setup_entry(hass, entry)

        self.assertTrue(result)
        self.assertEqual(hass.data["jackery"][entry.entry_id]["devices"], [])
        self.assertEqual(hass.data["jackery"][entry.entry_id]["coordinators"], {})
        self.assertEqual(integration.DataUpdateCoordinator.instances, [])
        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
            entry,
            integration.PLATFORMS,
        )

    async def test_setup_entry_copies_properties_before_adding_last_updated(
        self,
    ) -> None:
        """Coordinator refreshes should not mutate the raw API payload."""
        hass = self._make_hass()
        entry = self._make_entry()
        raw_properties = {"rb": 42, "ip": 15, "oac": 1}
        api.JackeryAPI.device_list_result = {
            "data": [{"devId": "device-1", "devName": "Explorer 240"}]
        }
        api.JackeryAPI.device_detail_results = {
            "device-1": {"data": {"properties": raw_properties}}
        }

        result = await integration.async_setup_entry(hass, entry)

        self.assertTrue(result)
        coordinator = hass.data["jackery"][entry.entry_id]["coordinators"]["device-1"]
        self.assertEqual(
            coordinator.data,
            {
                "rb": 42,
                "ip": 15,
                "oac": 1,
                "last_updated": "2026-04-18T19:00:00+01:00",
            },
        )
        self.assertEqual(raw_properties, {"rb": 42, "ip": 15, "oac": 1})

    async def test_setup_entry_raises_auth_failed_when_first_refresh_auth_fails(
        self,
    ) -> None:
        """Coordinator auth failures should propagate as config entry auth errors."""
        hass = self._make_hass()
        entry = self._make_entry()
        api.JackeryAPI.device_list_result = {
            "data": [
                {
                    "devId": "device-1",
                    "devName": "Explorer 240",
                }
            ]
        }
        api.JackeryAPI.device_detail_error = api.JackeryAuthenticationError(
            "token expired"
        )

        with self.assertRaises(integration.ConfigEntryAuthFailed):
            await integration.async_setup_entry(hass, entry)

        hass.config_entries.async_forward_entry_setups.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
