"""Regression tests for control client cleanup paths."""

from __future__ import annotations

import asyncio
import builtins
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "jackery"
TEST_PACKAGE = "jackery_cleanup_test"
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


def install_dependency_stubs(stubbed_modules: dict[str, object]) -> None:
    """Install minimal third-party and Home Assistant stubs."""
    if not _module_available("requests"):
        requests_mod = types.ModuleType("requests")

        class RequestException(Exception):
            """Stub requests exception."""

        requests_mod.RequestException = RequestException
        _install_stub_module(stubbed_modules, "requests", requests_mod)

    if not _module_available("Cryptodome"):
        cryptodome = types.ModuleType("Cryptodome")
        cryptodome.__path__ = []
        cipher_mod = types.ModuleType("Cryptodome.Cipher")
        public_key_mod = types.ModuleType("Cryptodome.PublicKey")
        util_mod = types.ModuleType("Cryptodome.Util")
        util_mod.__path__ = []
        padding_mod = types.ModuleType("Cryptodome.Util.Padding")

        cipher_mod.AES = types.SimpleNamespace(
            MODE_ECB=1, new=lambda *args, **kwargs: None
        )
        cipher_mod.PKCS1_v1_5 = types.SimpleNamespace(
            new=lambda *args, **kwargs: None
        )
        public_key_mod.RSA = types.SimpleNamespace(
            importKey=lambda *args, **kwargs: None
        )
        padding_mod.pad = lambda data, block_size: data

        _install_stub_module(stubbed_modules, "Cryptodome", cryptodome)
        _install_stub_module(stubbed_modules, "Cryptodome.Cipher", cipher_mod)
        _install_stub_module(
            stubbed_modules, "Cryptodome.PublicKey", public_key_mod
        )
        _install_stub_module(stubbed_modules, "Cryptodome.Util", util_mod)
        _install_stub_module(
            stubbed_modules, "Cryptodome.Util.Padding", padding_mod
        )

    if not _module_available("async_timeout"):
        async_timeout_mod = types.ModuleType("async_timeout")

        class _Timeout:
            async def __aenter__(self):
                return None

            async def __aexit__(self, exc_type, exc, tb):
                return False

        async_timeout_mod.timeout = lambda *args, **kwargs: _Timeout()
        _install_stub_module(stubbed_modules, "async_timeout", async_timeout_mod)

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

        def __init__(self, entry_id: str) -> None:
            self.entry_id = entry_id

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

    class DataUpdateCoordinator:
        """Stub data coordinator."""

    class UpdateFailed(Exception):
        """Stub update failure."""

    class ConfigEntryAuthFailed(Exception):
        """Stub auth failure."""

    class ConfigEntryNotReady(Exception):
        """Stub not-ready failure."""

    config_entries_mod.ConfigEntry = ConfigEntry
    const_mod.CONF_PASSWORD = "password"
    const_mod.CONF_USERNAME = "username"
    const_mod.Platform = Platform
    core_mod.HomeAssistant = HomeAssistant
    exceptions_mod.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    exceptions_mod.ConfigEntryNotReady = ConfigEntryNotReady
    update_coordinator_mod.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator_mod.UpdateFailed = UpdateFailed
    dt_mod.now = lambda: None

    homeassistant.helpers = helpers
    homeassistant.util = util
    helpers.update_coordinator = update_coordinator_mod
    util.dt = dt_mod


def install_package_stubs(stubbed_modules: dict[str, object]) -> None:
    """Install a throwaway package for loading the integration package."""
    package_mod = types.ModuleType(TEST_PACKAGE)
    package_mod.__path__ = [str(PACKAGE_ROOT)]
    _install_stub_module(stubbed_modules, TEST_PACKAGE, package_mod)

    const_mod = types.ModuleType(f"{TEST_PACKAGE}.const")
    const_mod.DOMAIN = "jackery"
    const_mod.POLLING_INTERVAL_SEC = 60
    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.const", const_mod)


dependency_stubs: dict[str, object] = {}
test_package_modules: dict[str, object] = {}
install_dependency_stubs(dependency_stubs)
install_package_stubs(test_package_modules)
try:
    api = load_module(
        f"{TEST_PACKAGE}.api",
        PACKAGE_ROOT / "api.py",
        test_package_modules,
    )
    integration = load_module(
        TEST_PACKAGE,
        PACKAGE_ROOT / "__init__.py",
        test_package_modules,
        package=True,
    )
finally:
    restore_stubbed_modules(dependency_stubs)


def tearDownModule() -> None:
    """Restore sys.modules entries replaced by test-only stubs."""
    restore_stubbed_modules(test_package_modules)


class DependencyStubInstallerTests(unittest.TestCase):
    """Verify dependency stubs extend partial Home Assistant installs."""

    def test_install_dependency_stubs_adds_missing_homeassistant_modules(self) -> None:
        """Pre-existing partial Home Assistant stubs should be completed."""
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
            install_dependency_stubs(local_stubbed_modules)

            self.assertIs(sys.modules["homeassistant"], homeassistant)
            self.assertIs(homeassistant.helpers, helpers)
            self.assertTrue(hasattr(sys.modules["homeassistant.const"], "Platform"))
            self.assertTrue(hasattr(sys.modules["homeassistant.util.dt"], "now"))
            self.assertTrue(hasattr(helpers, "update_coordinator"))
        finally:
            restore_stubbed_modules(local_stubbed_modules)

    def test_api_import_reraises_transitive_socketry_failures(self) -> None:
        """Missing socketry dependencies should not be masked as a missing package."""
        local_stubbed_modules: dict[str, object] = {}
        original_socketry = sys.modules.pop("socketry", _MISSING)

        try:
            install_dependency_stubs(local_stubbed_modules)
            original_import = builtins.__import__

            def import_with_transitive_socketry_failure(
                name, globals=None, locals=None, fromlist=(), level=0
            ):
                if name == "socketry":
                    err = ModuleNotFoundError("No module named 'socketry_dependency'")
                    err.name = "socketry_dependency"
                    raise err
                return original_import(name, globals, locals, fromlist, level)

            with unittest.mock.patch(
                "builtins.__import__",
                side_effect=import_with_transitive_socketry_failure,
            ):
                with self.assertRaises(ModuleNotFoundError) as raised:
                    load_module(
                        "jackery_socketry_import_failure_test",
                        PACKAGE_ROOT / "api.py",
                        local_stubbed_modules,
                    )

            self.assertEqual(raised.exception.name, "socketry_dependency")
        finally:
            restore_stubbed_modules(local_stubbed_modules)
            if original_socketry is _MISSING:
                sys.modules.pop("socketry", None)
            else:
                sys.modules["socketry"] = original_socketry


class ControlClientCleanupTests(unittest.IsolatedAsyncioTestCase):
    """Validate cached Socketry client cleanup during retries and unloads."""

    def setUp(self) -> None:
        self.original_socketry = api.socketry

    def tearDown(self) -> None:
        api.socketry = self.original_socketry

    async def test_retry_stops_discarded_control_client(self) -> None:
        """Retrying a failed control write should close the discarded client."""
        auth_error = type("AuthenticationError", (Exception,), {})
        mqtt_error = type("MqttError", (Exception,), {})
        socketry_error = type("SocketryError", (Exception,), {})

        failed_device = types.SimpleNamespace(
            set_property=AsyncMock(side_effect=auth_error("stale session"))
        )
        recovered_device = types.SimpleNamespace(set_property=AsyncMock())

        failed_client = types.SimpleNamespace(
            fetch_devices=AsyncMock(),
            devices=[{"devId": "device-1", "devSn": "serial-1"}],
            device=lambda serial: failed_device,
            stop=AsyncMock(),
        )
        recovered_client = types.SimpleNamespace(
            fetch_devices=AsyncMock(),
            devices=[{"devId": "device-1", "devSn": "serial-1"}],
            device=lambda serial: recovered_device,
            stop=AsyncMock(),
        )

        api.socketry = types.SimpleNamespace(
            AuthenticationError=auth_error,
            MqttError=mqtt_error,
            SocketryError=socketry_error,
            Client=types.SimpleNamespace(
                login=AsyncMock(side_effect=[failed_client, recovered_client])
            ),
        )
        jackery_api = api.JackeryAPI("user@example.com", "password")

        await jackery_api.async_set_device_property(
            "device-1",
            "serial-1",
            "ac",
            1,
        )

        api.socketry.Client.login.assert_has_awaits(
            [
                unittest.mock.call("user@example.com", "password"),
                unittest.mock.call("user@example.com", "password"),
            ]
        )
        failed_client.fetch_devices.assert_awaited_once()
        recovered_client.fetch_devices.assert_awaited_once()
        failed_client.stop.assert_awaited_once()
        recovered_client.stop.assert_not_awaited()
        recovered_device.set_property.assert_awaited_once_with("ac", 1, wait=True)
        self.assertIs(jackery_api._control_client, recovered_client)

    async def test_get_control_client_closes_uncached_client_when_fetch_fails(self) -> None:
        """A fetch failure should close the new control client and avoid caching it."""
        socketry_error = type("SocketryError", (Exception,), {})
        failed_client = types.SimpleNamespace(
            fetch_devices=AsyncMock(side_effect=socketry_error("fetch failed")),
            stop=AsyncMock(),
        )

        api.socketry = types.SimpleNamespace(
            Client=types.SimpleNamespace(login=AsyncMock(return_value=failed_client))
        )
        jackery_api = api.JackeryAPI("user@example.com", "password")

        with self.assertRaises(socketry_error):
            await jackery_api._async_get_control_client()

        api.socketry.Client.login.assert_awaited_once_with(
            "user@example.com", "password"
        )
        failed_client.fetch_devices.assert_awaited_once()
        failed_client.stop.assert_awaited_once()
        self.assertIsNone(jackery_api._control_client)

    async def test_get_control_client_closes_uncached_client_when_fetch_is_cancelled(
        self,
    ) -> None:
        """Cancellation during device fetch should still close the new client."""
        failed_client = types.SimpleNamespace(
            fetch_devices=AsyncMock(side_effect=asyncio.CancelledError()),
            stop=AsyncMock(),
        )

        api.socketry = types.SimpleNamespace(
            Client=types.SimpleNamespace(login=AsyncMock(return_value=failed_client))
        )
        jackery_api = api.JackeryAPI("user@example.com", "password")

        with self.assertRaises(asyncio.CancelledError):
            await jackery_api._async_get_control_client()

        api.socketry.Client.login.assert_awaited_once_with(
            "user@example.com", "password"
        )
        failed_client.fetch_devices.assert_awaited_once()
        failed_client.stop.assert_awaited_once()
        self.assertIsNone(jackery_api._control_client)

    async def test_retry_resets_cached_control_client_on_final_failure(self) -> None:
        """Final control-write failure should close and clear the cached client."""
        auth_error = type("AuthenticationError", (Exception,), {})
        mqtt_error = type("MqttError", (Exception,), {})
        socketry_error = type("SocketryError", (Exception,), {})

        first_device = types.SimpleNamespace(
            set_property=AsyncMock(side_effect=auth_error("stale session"))
        )
        second_device = types.SimpleNamespace(
            set_property=AsyncMock(side_effect=auth_error("still stale"))
        )

        first_client = types.SimpleNamespace(
            fetch_devices=AsyncMock(),
            devices=[{"devId": "device-1", "devSn": "serial-1"}],
            device=lambda serial: first_device,
            stop=AsyncMock(),
        )
        second_client = types.SimpleNamespace(
            fetch_devices=AsyncMock(),
            devices=[{"devId": "device-1", "devSn": "serial-1"}],
            device=lambda serial: second_device,
            stop=AsyncMock(),
        )

        api.socketry = types.SimpleNamespace(
            AuthenticationError=auth_error,
            MqttError=mqtt_error,
            SocketryError=socketry_error,
            Client=types.SimpleNamespace(
                login=AsyncMock(side_effect=[first_client, second_client])
            ),
        )
        jackery_api = api.JackeryAPI("user@example.com", "password")

        with self.assertRaises(auth_error):
            await jackery_api.async_set_device_property(
                "device-1",
                "serial-1",
                "ac",
                1,
            )

        api.socketry.Client.login.assert_has_awaits(
            [
                unittest.mock.call("user@example.com", "password"),
                unittest.mock.call("user@example.com", "password"),
            ]
        )
        first_client.fetch_devices.assert_awaited_once()
        second_client.fetch_devices.assert_awaited_once()
        first_client.stop.assert_awaited_once()
        second_client.stop.assert_awaited_once()
        first_device.set_property.assert_awaited_once_with("ac", 1, wait=True)
        second_device.set_property.assert_awaited_once_with("ac", 1, wait=True)
        self.assertIsNone(jackery_api._control_client)

    async def test_async_close_stops_cached_control_client(self) -> None:
        """Closing the API should close and clear the cached control client."""
        cached_client = types.SimpleNamespace(stop=AsyncMock())
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._control_client = cached_client

        await jackery_api.async_close()

        cached_client.stop.assert_awaited_once()
        self.assertIsNone(jackery_api._control_client)

    async def test_async_set_device_dp_delegates_to_property_writer(self) -> None:
        """Raw DP writes should reuse the existing property-write path."""
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api.async_set_device_property = AsyncMock()

        await jackery_api.async_set_device_dp(
            "device-1",
            "serial-1",
            108,
            "22:00-06:00,1111111",
        )

        jackery_api.async_set_device_property.assert_awaited_once_with(
            "device-1",
            "serial-1",
            "108",
            "22:00-06:00,1111111",
        )

    async def test_async_close_uses_next_close_method_after_failure(self) -> None:
        """Cleanup should keep trying alternative close methods after failures."""
        cached_client = types.SimpleNamespace(
            stop=AsyncMock(side_effect=RuntimeError("stop failed")),
            disconnect=AsyncMock(),
            close=AsyncMock(),
        )
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._control_client = cached_client

        await jackery_api.async_close()

        cached_client.stop.assert_awaited_once()
        cached_client.disconnect.assert_awaited_once()
        cached_client.close.assert_not_awaited()
        self.assertIsNone(jackery_api._control_client)

    async def test_unload_entry_closes_api_before_removing_entry(self) -> None:
        """Config entry unload should close the cached control client."""
        entry = types.SimpleNamespace(entry_id="entry-1")
        api_client = types.SimpleNamespace(async_close=AsyncMock())
        hass = types.SimpleNamespace(
            data={"jackery": {"entry-1": {"api": api_client}}},
            config_entries=types.SimpleNamespace(
                async_unload_platforms=AsyncMock(return_value=True)
            ),
        )

        unload_ok = await integration.async_unload_entry(hass, entry)

        self.assertTrue(unload_ok)
        hass.config_entries.async_unload_platforms.assert_awaited_once_with(
            entry,
            integration.PLATFORMS,
        )
        api_client.async_close.assert_awaited_once()
        self.assertNotIn("entry-1", hass.data["jackery"])

    async def test_unload_entry_is_idempotent_when_entry_data_is_missing(self) -> None:
        """Config entry unload should tolerate a missing cached entry."""
        entry = types.SimpleNamespace(entry_id="entry-1")
        hass = types.SimpleNamespace(
            data={"jackery": {}},
            config_entries=types.SimpleNamespace(
                async_unload_platforms=AsyncMock(return_value=True)
            ),
        )

        unload_ok = await integration.async_unload_entry(hass, entry)

        self.assertTrue(unload_ok)
        hass.config_entries.async_unload_platforms.assert_awaited_once_with(
            entry,
            integration.PLATFORMS,
        )
        self.assertEqual(hass.data["jackery"], {})


if __name__ == "__main__":
    unittest.main()
