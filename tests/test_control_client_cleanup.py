"""Regression tests for control client cleanup paths."""

from __future__ import annotations

import asyncio
import builtins
import importlib.util
import json
import sys
import time
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
    issue_registry_mod = ensure_stub_module("homeassistant.helpers.issue_registry")
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
    core_mod.ServiceCall = type("ServiceCall", (), {})
    exceptions_mod.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    exceptions_mod.ConfigEntryNotReady = ConfigEntryNotReady
    exceptions_mod.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
    update_coordinator_mod.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator_mod.UpdateFailed = UpdateFailed
    issue_registry_mod.IssueSeverity = types.SimpleNamespace(WARNING="warning")
    issue_registry_mod.async_create_issue = lambda *args, **kwargs: None
    issue_registry_mod.async_delete_issue = lambda *args, **kwargs: None
    dt_mod.now = lambda: None

    homeassistant.helpers = helpers
    homeassistant.util = util
    helpers.update_coordinator = update_coordinator_mod
    helpers.issue_registry = issue_registry_mod
    util.dt = dt_mod


def install_package_stubs(stubbed_modules: dict[str, object]) -> None:
    """Install a throwaway package for loading the integration package."""
    package_mod = types.ModuleType(TEST_PACKAGE)
    package_mod.__path__ = [str(PACKAGE_ROOT)]
    _install_stub_module(stubbed_modules, TEST_PACKAGE, package_mod)

    const_mod = types.ModuleType(f"{TEST_PACKAGE}.const")
    const_mod.DOMAIN = "jackery"
    const_mod.POLLING_INTERVAL_SEC = 60
    const_mod.SENSOR_DESCRIPTIONS = ()
    const_mod.BINARY_SENSOR_DESCRIPTIONS = ()
    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.const", const_mod)

    protocol_mod = types.ModuleType(f"{TEST_PACKAGE}.protocol")
    protocol_mod.CONTROL_SPECS = {}
    protocol_mod.CONTROL_SPECS_BY_SLUG = {}
    protocol_mod.is_transfer_switch_device = lambda device_info=None, properties=None: (
        (device_info or {}).get("modelCode") == 2001
    )
    protocol_mod.CLOUD_OFFLINE_TIME_KEY = "cloud_offline_time"
    protocol_mod.CLOUD_STATUS_KEYS = frozenset()
    protocol_mod.is_cloud_online = lambda properties: True
    protocol_mod.parse_cloud_status = lambda device: {}
    protocol_mod.timezone_command = lambda *args: (1, {}, None)
    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.protocol", protocol_mod)


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

    async def test_portable_property_routes_through_persistent_session(self) -> None:
        """async_set_device_property must use the persistent MQTT session, not the
        socketry control client, to avoid competing MQTT connections (10403 loop).
        """
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api.async_send_device_command = AsyncMock()
        jackery_api._mqtt_session = types.SimpleNamespace()  # non-None sentinel

        await jackery_api.async_set_device_property("device-1", "serial-1", "ac", 1)

        # Must delegate to the persistent-session command path, never socketry Client()
        jackery_api.async_send_device_command.assert_awaited_once_with(
            "device-1", "serial-1", 4, {"oac": 1}
        )

    async def test_get_control_client_closes_uncached_client_when_fetch_fails(self) -> None:
        """A fetch failure should close the new control client and avoid caching it."""
        socketry_error = type("SocketryError", (Exception,), {})
        failed_client = types.SimpleNamespace(
            fetch_devices=AsyncMock(side_effect=socketry_error("fetch failed")),
            stop=AsyncMock(),
        )

        mock_client_class = unittest.mock.Mock(return_value=failed_client)
        api.socketry = types.SimpleNamespace(
            Client=mock_client_class,
        )
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._mqtt_user_id = "test-user"
        jackery_api._mqtt_password_b64 = "cGFzc3dvcmQ="
        jackery_api._token = "test-token"

        with self.assertRaises(socketry_error):
            await jackery_api._async_get_control_client()

        mock_client_class.assert_called_once()
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

        mock_client_class = unittest.mock.Mock(return_value=failed_client)
        api.socketry = types.SimpleNamespace(
            Client=mock_client_class,
        )
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._mqtt_user_id = "test-user"
        jackery_api._mqtt_password_b64 = "cGFzc3dvcmQ="
        jackery_api._token = "test-token"

        with self.assertRaises(asyncio.CancelledError):
            await jackery_api._async_get_control_client()

        mock_client_class.assert_called_once()
        failed_client.fetch_devices.assert_awaited_once()
        failed_client.stop.assert_awaited_once()
        self.assertIsNone(jackery_api._control_client)

    async def test_portable_property_write_key_override(self) -> None:
        """sltb reads as 'sltb' but must be written as 'slt' in the MQTT body."""
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api.async_send_device_command = AsyncMock()
        jackery_api._mqtt_session = types.SimpleNamespace()

        await jackery_api.async_set_device_property("device-1", "serial-1", "screen-timeout", 10)

        jackery_api.async_send_device_command.assert_awaited_once_with(
            "device-1", "serial-1", 8, {"slt": 10}
        )

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

    async def test_portable_property_raises_without_mqtt_session(self) -> None:
        """async_set_device_property must raise RuntimeError when no MQTT session
        is available, surfacing the misconfiguration clearly instead of opening a
        competing socketry connection that would trigger 10403 cascades.
        """
        jackery_api = api.JackeryAPI("user@example.com", "password")
        # _mqtt_session is None by default (not started)

        with self.assertRaises(RuntimeError, msg="MQTT session not started"):
            await jackery_api.async_set_device_property("device-1", "serial-1", "ac", 1)

    async def test_circuit_query_uses_session_and_ignores_actionid_1(self) -> None:
        """async_query_transfer_switch_circuits must route through the MQTT session
        and supply a matcher that rejects actionId=1 partial push messages."""
        device_sn = "test-sn"
        jackery_api = api.JackeryAPI("user@example.com", "password")

        captured_matcher = [None]

        async def fake_publish_and_wait(payload, matcher, timeout=10.0):
            captured_matcher[0] = matcher
            return {
                "deviceSn": device_sn,
                "actionId": 7,
                "body": {"cir": [
                    {"idx": 1, "nm": "T2ZmaWNl", "pc": 150, "sw": 1, "sph": 0, "pr": 1},
                    {"idx": 2, "nm": "dGVzdA==", "pc": 0, "sw": 1, "sph": 0, "pr": 0},
                ]},
            }

        jackery_api._mqtt_session = types.SimpleNamespace(
            publish_and_wait=fake_publish_and_wait
        )

        circuits = await jackery_api.async_query_transfer_switch_circuits(device_sn)

        # Correct full response returned
        self.assertEqual(len(circuits), 2)
        self.assertTrue(all("nm" in c for c in circuits))

        # Matcher must reject actionId=1 partial push
        partial_push = {
            "deviceSn": device_sn,
            "actionId": 1,
            "body": {"cir": [{"idx": 1, "pc": 150}]},
        }
        self.assertFalse(captured_matcher[0](partial_push))

        # Matcher must accept actionId=7 full response
        full_response = {
            "deviceSn": device_sn,
            "actionId": 7,
            "body": {"cir": [{"nm": "T2ZmaWNl"}]},
        }
        self.assertTrue(captured_matcher[0](full_response))


class MqttSessionTests(unittest.IsolatedAsyncioTestCase):
    """Validate JackeryMqttSession dispatch, reconnect, and lifecycle."""

    def _make_session(self):
        """Return a JackeryMqttSession backed by a minimal API stub."""
        stub_api = types.SimpleNamespace(
            _build_mqtt_params=unittest.mock.Mock(
                return_value=({"hostname": "mqtt.test", "port": 8883}, "test-user")
            ),
        )
        return api.JackeryMqttSession(stub_api)

    async def test_dispatch_resolves_pending_future_when_matcher_matches(self) -> None:
        """_dispatch must resolve the pending future when matcher returns True."""
        session = self._make_session()
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        session._pending_future = future
        session._pending_matcher = lambda data: data.get("hit") is True

        session._dispatch(
            types.SimpleNamespace(payload=json.dumps({"hit": True}).encode())
        )

        self.assertTrue(future.done())
        self.assertEqual(future.result()["hit"], True)

    async def test_dispatch_ignores_message_when_matcher_does_not_match(self) -> None:
        """_dispatch must not resolve the future if matcher returns False."""
        session = self._make_session()
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        session._pending_future = future
        session._pending_matcher = lambda data: data.get("hit") is True

        session._dispatch(
            types.SimpleNamespace(payload=json.dumps({"hit": False}).encode())
        )

        self.assertFalse(future.done())

    async def test_fail_pending_sets_exception_on_outstanding_future(self) -> None:
        """_fail_pending must fail any in-flight future and clear state."""
        session = self._make_session()
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        session._pending_future = future
        session._pending_matcher = lambda _: True
        err = RuntimeError("test disconnect")

        session._fail_pending(err)

        self.assertTrue(future.done())
        self.assertIs(future.exception(), err)
        self.assertIsNone(session._pending_future)
        self.assertIsNone(session._pending_matcher)

    async def test_fail_pending_is_noop_when_no_future(self) -> None:
        """_fail_pending must not raise when no future is outstanding."""
        session = self._make_session()
        session._fail_pending(RuntimeError("should not matter"))

    async def test_stop_cancels_loop_task_and_fails_pending(self) -> None:
        """stop() must cancel the background task and fail any pending future."""
        session = self._make_session()

        # Patch aiomqtt.Client to block forever so _run_loop stays in the connect attempt
        async def _block_forever(**kw):
            await asyncio.sleep(3600)

        class _BlockingCM:
            async def __aenter__(self):
                await asyncio.sleep(3600)

            async def __aexit__(self, *a):
                return False

        original_aiomqtt = api.aiomqtt
        api.aiomqtt = types.SimpleNamespace(Client=lambda **kw: _BlockingCM())
        try:
            await session.start()
            # Plant a pending future
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            session._pending_future = future
            session._pending_matcher = lambda _: True

            await session.stop()

            self.assertIsNone(session._loop_task)
            self.assertTrue(future.done())
        finally:
            api.aiomqtt = original_aiomqtt

    async def test_session_connects_and_resolves_publish_and_wait(self) -> None:
        """publish_and_wait must publish and resolve when the session is connected."""
        session = self._make_session()
        device_sn = "sn-1"
        response_data = {"deviceSn": device_sn, "actionId": 7, "body": {"cir": []}}

        published = []

        class _FakeClient:
            async def publish(self, topic, payload, *, qos=0):
                published.append(json.loads(payload))
                # Dispatch the matching response synchronously during publish
                session._dispatch(
                    types.SimpleNamespace(payload=json.dumps(response_data).encode())
                )

        # Set up the session as if fully connected
        session._client = _FakeClient()
        session._user_id = "test-user"
        session._connected.set()

        result = await session.publish_and_wait(
            {"deviceSn": device_sn, "actionId": 7, "body": {}},
            matcher=lambda d: d.get("deviceSn") == device_sn and d.get("actionId") == 7,
            timeout=5.0,
        )

        self.assertEqual(result["deviceSn"], device_sn)
        self.assertEqual(len(published), 1)

    async def test_publish_and_wait_raises_on_timeout(self) -> None:
        """publish_and_wait must raise TimeoutError when no matching response arrives."""
        session = self._make_session()
        session._connected.set()

        published = []

        class _FakeClient:
            async def publish(self, topic, payload, *, qos=0):
                published.append(payload)
                # Never dispatch a response - let it time out

        session._client = _FakeClient()
        session._user_id = "test-user"

        with self.assertRaises(TimeoutError):
            await session.publish_and_wait(
                {"deviceSn": "sn", "actionId": 7},
                matcher=lambda _: False,
                timeout=0.05,
            )

        self.assertEqual(len(published), 1)

    async def test_reconnect_delays_double_up_to_cap(self) -> None:
        """Reconnect delay must double on each failure up to _MAX_RECONNECT_DELAY."""
        session = self._make_session()
        self.assertEqual(session._reconnect_delay, 1.0)
        # Simulate repeated failures
        for expected in [2.0, 4.0, 8.0, 16.0, 30.0, 30.0]:
            session._reconnect_delay = min(session._reconnect_delay * 2, session._MAX_RECONNECT_DELAY)
            self.assertEqual(session._reconnect_delay, expected)


class HttpSessionTests(unittest.TestCase):
    """Validate token-expiry recovery in JackeryAPI._get_request."""

    def setUp(self) -> None:
        self.original_requests_get = api.requests.get

    def tearDown(self) -> None:
        api.requests.get = self.original_requests_get

    def _make_response(self, json_data: dict) -> object:
        resp = unittest.mock.Mock()
        resp.raise_for_status = lambda: None
        resp.json.return_value = json_data
        return resp

    def test_get_request_relogins_and_retries_on_10402(self) -> None:
        """10402 (token expired) must trigger re-login and a second HTTP request."""
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._token = "old-token"

        api.requests.get = unittest.mock.Mock(side_effect=[
            self._make_response({"code": 10402, "msg": "token expired"}),
            self._make_response({"code": 0, "data": {"rb": 85}}),
        ])

        def refresh_token():
            jackery_api._token = "fresh-token"
            return True

        jackery_api.login = unittest.mock.Mock(side_effect=refresh_token)

        result = jackery_api._get_request("/v1/device/property")

        jackery_api.login.assert_called_once()
        self.assertEqual(api.requests.get.call_count, 2)
        self.assertEqual(
            api.requests.get.call_args_list[1].kwargs["headers"]["token"],
            "fresh-token",
        )
        self.assertEqual(result["data"]["rb"], 85)

    def test_get_request_relogins_and_retries_on_10403(self) -> None:
        """10403 (session displaced) must be handled identically to 10402."""
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._token = "old-token"

        api.requests.get = unittest.mock.Mock(side_effect=[
            self._make_response({"code": 10403, "msg": "Account logged in elsewhere"}),
            self._make_response({"code": 0, "data": {"rb": 70}}),
        ])

        def refresh_token():
            jackery_api._token = "fresh-token"
            return True

        jackery_api.login = unittest.mock.Mock(side_effect=refresh_token)

        result = jackery_api._get_request("/v1/device/property")

        jackery_api.login.assert_called_once()
        self.assertEqual(api.requests.get.call_count, 2)
        self.assertEqual(
            api.requests.get.call_args_list[1].kwargs["headers"]["token"],
            "fresh-token",
        )
        self.assertEqual(result["data"]["rb"], 70)

    def test_get_request_raises_auth_error_when_relogin_fails(self) -> None:
        """If re-login fails after 10402/10403, JackeryAuthenticationError must be raised."""
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._token = "old-token"

        api.requests.get = unittest.mock.Mock(
            return_value=self._make_response({"code": 10403, "msg": "displaced"})
        )
        jackery_api.login = unittest.mock.Mock(return_value=False)

        with self.assertRaises(api.JackeryAuthenticationError):
            jackery_api._get_request("/v1/device/property")

        jackery_api.login.assert_called_once()
        self.assertEqual(api.requests.get.call_count, 1)

    def test_login_skips_inner_when_recently_refreshed(self) -> None:
        """Concurrent login callers must reuse credentials refreshed within 5 s."""
        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._token = "existing-token"
        jackery_api._last_login_time = time.monotonic() - 1.0  # 1 second ago

        mock_inner = unittest.mock.Mock(return_value=True)
        jackery_api._login_inner = mock_inner

        result = jackery_api.login()

        self.assertTrue(result)
        mock_inner.assert_not_called()

    def test_redact_masks_credentials_and_device_secrets(self) -> None:
        """Debug logging must not expose tokens, MQTT passwords, or device secrets."""
        payload = {
            "code": 0,
            "token": "tok",
            "data": {
                "mqttPassWord": "mqtt",
                "device": {"deviceSecret": "s", "randomSalt": "r", "onlineStatus": 0},
                "properties": {"rb": 54},
                "list": [{"deviceSecret": "s2"}],
            },
        }

        redacted = api._redact(payload)

        self.assertEqual(redacted["token"], "**REDACTED**")
        self.assertEqual(redacted["data"]["mqttPassWord"], "**REDACTED**")
        self.assertEqual(redacted["data"]["device"]["deviceSecret"], "**REDACTED**")
        self.assertEqual(redacted["data"]["device"]["randomSalt"], "**REDACTED**")
        self.assertEqual(redacted["data"]["list"][0]["deviceSecret"], "**REDACTED**")
        self.assertEqual(redacted["data"]["device"]["onlineStatus"], 0)
        self.assertEqual(redacted["data"]["properties"], {"rb": 54})
        self.assertEqual(payload["data"]["device"]["deviceSecret"], "s")


class HttpSessionAsyncTests(unittest.IsolatedAsyncioTestCase):
    """Validate async MQTT command retry with credential refresh."""

    def setUp(self) -> None:
        self.original_aiomqtt = api.aiomqtt

    def tearDown(self) -> None:
        api.aiomqtt = self.original_aiomqtt

    async def test_mqtt_command_routes_through_persistent_session(self) -> None:
        """async_send_device_command must publish via _mqtt_session."""
        device_sn = "ts-sn"
        action_id = 9

        published_payloads = []
        captured_matcher = [None]

        async def fake_publish_and_wait(payload, matcher, timeout=10.0):
            published_payloads.append(payload)
            captured_matcher[0] = matcher
            return {
                "deviceSn": device_sn,
                "actionId": action_id,
                "body": {"result": "ok"},
            }

        jackery_api = api.JackeryAPI("user@example.com", "password")
        jackery_api._mqtt_session = types.SimpleNamespace(
            publish_and_wait=fake_publish_and_wait
        )

        await jackery_api.async_send_device_command(
            "device-1", device_sn, action_id, {"cmd": 12, "idx": 1, "sw": 1}
        )

        self.assertEqual(len(published_payloads), 1)
        self.assertEqual(published_payloads[0]["actionId"], action_id)
        self.assertEqual(published_payloads[0]["deviceSn"], device_sn)
        self.assertEqual(published_payloads[0]["body"], {"cmd": 12, "idx": 1, "sw": 1})

        # Matcher must accept actionId echo from device, reject actionId=1 push
        self.assertTrue(captured_matcher[0]({"deviceSn": device_sn, "actionId": action_id}))
        self.assertFalse(captured_matcher[0]({"deviceSn": device_sn, "actionId": 1}))


class DeviceResolutionTests(unittest.TestCase):
    """Validate Socketry control device lookup logic."""

    def test_resolve_control_device_falls_back_to_device_sn(self) -> None:
        """Device lookup must fall back to devSn when devId does not match."""
        expected = types.SimpleNamespace(name="target")
        client = types.SimpleNamespace(
            devices=[{"devId": "999-other", "devSn": "target-sn"}],
            device=lambda serial: expected if serial == "target-sn" else None,
        )

        result = api.JackeryAPI._resolve_control_device(
            client, "999-different", "target-sn"
        )

        self.assertIs(result, expected)

    def test_resolve_control_device_raises_when_no_match(self) -> None:
        """KeyError must be raised when neither devId nor devSn matches."""
        client = types.SimpleNamespace(
            devices=[{"devId": "wrong-id", "devSn": "wrong-sn"}],
            device=lambda serial: None,
        )

        with self.assertRaises(KeyError):
            api.JackeryAPI._resolve_control_device(
                client, "not-found", "also-not-found"
            )


if __name__ == "__main__":
    unittest.main()
