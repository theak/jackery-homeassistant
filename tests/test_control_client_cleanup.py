"""Regression tests for control client cleanup paths."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "jackery"
TEST_PACKAGE = "jackery_cleanup_test"


def load_module(module_name: str, path: Path, *, package: bool = False):
    """Load a module directly from the repository."""
    kwargs = {}
    if package:
        kwargs["submodule_search_locations"] = [str(path.parent)]
    spec = importlib.util.spec_from_file_location(module_name, path, **kwargs)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def install_dependency_stubs() -> None:
    """Install minimal third-party and Home Assistant stubs."""
    requests_mod = types.ModuleType("requests")

    class RequestException(Exception):
        """Stub requests exception."""

    requests_mod.RequestException = RequestException
    sys.modules["requests"] = requests_mod

    cryptodome = types.ModuleType("Cryptodome")
    cryptodome.__path__ = []
    cipher_mod = types.ModuleType("Cryptodome.Cipher")
    public_key_mod = types.ModuleType("Cryptodome.PublicKey")
    util_mod = types.ModuleType("Cryptodome.Util")
    util_mod.__path__ = []
    padding_mod = types.ModuleType("Cryptodome.Util.Padding")

    cipher_mod.AES = types.SimpleNamespace(MODE_ECB=1, new=lambda *args, **kwargs: None)
    cipher_mod.PKCS1_v1_5 = types.SimpleNamespace(new=lambda *args, **kwargs: None)
    public_key_mod.RSA = types.SimpleNamespace(importKey=lambda *args, **kwargs: None)
    padding_mod.pad = lambda data, block_size: data

    sys.modules["Cryptodome"] = cryptodome
    sys.modules["Cryptodome.Cipher"] = cipher_mod
    sys.modules["Cryptodome.PublicKey"] = public_key_mod
    sys.modules["Cryptodome.Util"] = util_mod
    sys.modules["Cryptodome.Util.Padding"] = padding_mod

    async_timeout_mod = types.ModuleType("async_timeout")

    class _Timeout:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async_timeout_mod.timeout = lambda *args, **kwargs: _Timeout()
    sys.modules["async_timeout"] = async_timeout_mod

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    util = types.ModuleType("homeassistant.util")
    util.__path__ = []

    config_entries_mod = types.ModuleType("homeassistant.config_entries")
    const_mod = types.ModuleType("homeassistant.const")
    core_mod = types.ModuleType("homeassistant.core")
    update_coordinator_mod = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )
    dt_mod = types.ModuleType("homeassistant.util.dt")

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

    class DataUpdateCoordinator:
        """Stub data coordinator."""

    class UpdateFailed(Exception):
        """Stub update failure."""

    config_entries_mod.ConfigEntry = ConfigEntry
    const_mod.CONF_PASSWORD = "password"
    const_mod.CONF_USERNAME = "username"
    const_mod.Platform = Platform
    core_mod.HomeAssistant = HomeAssistant
    update_coordinator_mod.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator_mod.UpdateFailed = UpdateFailed
    dt_mod.now = lambda: None

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.util"] = util
    sys.modules["homeassistant.config_entries"] = config_entries_mod
    sys.modules["homeassistant.const"] = const_mod
    sys.modules["homeassistant.core"] = core_mod
    sys.modules["homeassistant.helpers.update_coordinator"] = (
        update_coordinator_mod
    )
    sys.modules["homeassistant.util.dt"] = dt_mod


def install_package_stubs() -> None:
    """Install a throwaway package for loading the integration package."""
    package_mod = types.ModuleType(TEST_PACKAGE)
    package_mod.__path__ = [str(PACKAGE_ROOT)]
    sys.modules[TEST_PACKAGE] = package_mod

    const_mod = types.ModuleType(f"{TEST_PACKAGE}.const")
    const_mod.DOMAIN = "jackery"
    const_mod.POLLING_INTERVAL_SEC = 60
    sys.modules[f"{TEST_PACKAGE}.const"] = const_mod


install_dependency_stubs()
install_package_stubs()
api = load_module(f"{TEST_PACKAGE}.api", PACKAGE_ROOT / "api.py")
integration = load_module(TEST_PACKAGE, PACKAGE_ROOT / "__init__.py", package=True)


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

    async def test_async_close_stops_cached_control_client(self) -> None:
        """Closing the API should close and clear the cached control client."""
        cached_client = types.SimpleNamespace(stop=AsyncMock())
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._control_client = cached_client

        await jackery_api.async_close()

        cached_client.stop.assert_awaited_once()
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


if __name__ == "__main__":
    unittest.main()
