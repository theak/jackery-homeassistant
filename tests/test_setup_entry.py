"""Tests for Jackery config entry setup behavior."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
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
    issue_registry_mod = ensure_stub_module("homeassistant.helpers.issue_registry")
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

        def async_set_updated_data(self, data) -> None:
            self.data = data

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
    dt_mod.now = lambda: "2026-04-18T19:00:00+01:00"
    dt_mod.utcnow = lambda: datetime.now(timezone.utc)
    dt_mod.as_local = lambda value: value

    homeassistant.helpers = helpers
    homeassistant.util = util
    helpers.update_coordinator = update_coordinator_mod
    helpers.issue_registry = issue_registry_mod
    util.dt = dt_mod


def install_package_stubs(stubbed_modules: dict[str, object]) -> None:
    """Install the minimal Jackery package structure for relative imports."""
    package_mod = types.ModuleType(TEST_PACKAGE)
    package_mod.__path__ = [str(PACKAGE_ROOT)]
    _install_stub_module(stubbed_modules, TEST_PACKAGE, package_mod)

    const_mod = types.ModuleType(f"{TEST_PACKAGE}.const")
    const_mod.DOMAIN = "jackery"
    const_mod.POLLING_INTERVAL_SEC = 60
    const_mod.SENSOR_DESCRIPTIONS = ()
    const_mod.BINARY_SENSOR_DESCRIPTIONS = ()

    protocol_mod = types.ModuleType(f"{TEST_PACKAGE}.protocol")
    protocol_mod.CONTROL_SPECS = {}
    protocol_mod.CONTROL_SPECS_BY_SLUG = {}
    protocol_mod.is_transfer_switch_device = lambda device_info=None, properties=None: (
        (device_info or {}).get("modelCode") == 2001
    )
    real_protocol = load_module(
        f"{TEST_PACKAGE}_real_protocol", PACKAGE_ROOT / "protocol.py", stubbed_modules
    )
    for name in (
        "CLOUD_OFFLINE_TIME_KEY",
        "CLOUD_STATUS_KEYS",
        "is_cloud_online",
        "parse_cloud_status",
        "timezone_command",
    ):
        setattr(protocol_mod, name, getattr(real_protocol, name))

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
        plans_result: list = []
        plans_error: Exception | None = None
        circuits_result: list = []
        circuits_error: Exception | None = None
        plans_query_calls: list = []
        circuits_query_calls: list = []
        create_plan_calls: list = []
        update_plan_calls: list = []
        delete_plan_calls: list = []

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

        async def start_mqtt_session(self) -> None:
            """No-op stub for persistent MQTT session startup."""

        def register_push_handler(self, device_sn: str, handler: callable) -> None:
            """No-op stub - push handlers not exercised in setup tests."""

        async def async_query_transfer_switch_plans(self, device_sn: str) -> list:
            type(self).plans_query_calls.append(device_sn)
            if type(self).plans_error is not None:
                raise type(self).plans_error
            return list(type(self).plans_result)

        async def async_query_transfer_switch_circuits(self, device_sn: str) -> list:
            type(self).circuits_query_calls.append(device_sn)
            if type(self).circuits_error is not None:
                raise type(self).circuits_error
            return list(type(self).circuits_result)

        async def async_create_transfer_switch_plan(
            self, device_id: str, device_sn: str, plan: dict
        ) -> None:
            type(self).create_plan_calls.append((device_id, device_sn, plan))

        async def async_update_transfer_switch_plan(
            self, device_id: str, device_sn: str, plan: dict
        ) -> None:
            type(self).update_plan_calls.append((device_id, device_sn, plan))

        async def async_delete_transfer_switch_plan(
            self, device_id: str, device_sn: str, pid: str
        ) -> None:
            type(self).delete_plan_calls.append((device_id, device_sn, pid))

        @classmethod
        def reset(cls) -> None:
            """Reset the stub API state between tests."""
            cls.device_list_result = {"data": []}
            cls.device_list_error = None
            cls.device_detail_results = {}
            cls.device_detail_error = None
            cls.instances = []
            cls.plans_result = []
            cls.plans_error = None
            cls.circuits_result = []
            cls.circuits_error = None
            cls.plans_query_calls = []
            cls.circuits_query_calls = []
            cls.create_plan_calls = []
            cls.update_plan_calls = []
            cls.delete_plan_calls = []

    api_mod.JackeryAPI = JackeryAPI
    api_mod.JackeryAuthenticationError = JackeryAuthenticationError

    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.const", const_mod)
    _install_stub_module(stubbed_modules, f"{TEST_PACKAGE}.protocol", protocol_mod)
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
            services=types.SimpleNamespace(
                has_service=lambda *a: False,
                async_register=lambda *a, **kw: None,
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

    async def test_coordinator_keeps_last_known_data_on_transient_http_failure(
        self,
    ) -> None:
        """A transient HTTP failure should reuse the last good payload."""
        hass = self._make_hass()
        entry = self._make_entry()
        api.JackeryAPI.device_list_result = {
            "data": [{"devId": "device-1", "devName": "Explorer 240"}]
        }
        api.JackeryAPI.device_detail_results = {
            "device-1": {"data": {"properties": {"rb": 42, "ip": 15, "oac": 1}}}
        }

        await integration.async_setup_entry(hass, entry)
        coordinator = hass.data["jackery"][entry.entry_id]["coordinators"]["device-1"]

        # Next poll fails at the HTTP layer.
        api.JackeryAPI.device_detail_error = ConnectionError("dns blip")
        refreshed = await coordinator.update_method()

        # Entities keep their last-known values instead of going unavailable.
        self.assertEqual(refreshed["rb"], 42)
        self.assertEqual(refreshed["ip"], 15)
        self.assertEqual(refreshed["oac"], 1)

    async def test_coordinator_raises_after_persistent_http_failures(self) -> None:
        """Once the failure streak exceeds the tolerance, refresh should fail."""
        hass = self._make_hass()
        entry = self._make_entry()
        api.JackeryAPI.device_list_result = {
            "data": [{"devId": "device-1", "devName": "Explorer 240"}]
        }
        api.JackeryAPI.device_detail_results = {
            "device-1": {"data": {"properties": {"rb": 42}}}
        }

        await integration.async_setup_entry(hass, entry)
        coordinator = hass.data["jackery"][entry.entry_id]["coordinators"]["device-1"]

        api.JackeryAPI.device_detail_error = ConnectionError("outage")
        # Tolerate up to MAX_HTTP_FAILURES misses, then raise UpdateFailed.
        for _ in range(15):
            await coordinator.update_method()
        with self.assertRaises(integration.UpdateFailed):
            await coordinator.update_method()

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


class TransferSwitchCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    """Validate Transfer Switch coordinator caching and MQTT-gate behaviour."""

    _TS_DEVICE = {
        "devId": "ts-1",
        "devName": "Transfer Switch",
        "devSn": "ts-sn",
        "modelCode": 2001,
    }

    def setUp(self) -> None:
        api.JackeryAPI.reset()
        integration.DataUpdateCoordinator.instances = []
        integration.dt_util.now = lambda: "2026-04-18T19:00:00+01:00"

    @staticmethod
    def _make_hass():
        return types.SimpleNamespace(
            data={},
            async_add_executor_job=AsyncMock(side_effect=lambda func, *args: func(*args)),
            config_entries=types.SimpleNamespace(
                async_forward_entry_setups=AsyncMock(),
                async_unload_platforms=AsyncMock(return_value=True),
            ),
            services=types.SimpleNamespace(
                has_service=lambda *a: False,
                async_register=lambda *a, **kw: None,
            ),
        )

    async def _setup_ts(self):
        hass = self._make_hass()
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"username": "user@example.com", "password": "hunter2"},
        )
        api.JackeryAPI.device_list_result = {"data": [self._TS_DEVICE]}
        api.JackeryAPI.device_detail_results = {
            "ts-1": {"data": {"properties": {"op": 100, "ip": 50}}}
        }
        await integration.async_setup_entry(hass, entry)
        coordinator = hass.data["jackery"]["entry-1"]["coordinators"]["ts-1"]
        return coordinator

    async def test_mqtt_queries_skipped_when_http_poll_is_stale(self) -> None:
        """MQTT circuit/plan queries must not run while the HTTP poll is failing."""
        api.JackeryAPI.plans_result = [
            {"pid": "p1", "tt": 0, "st": "22:00", "et": "06:00", "sw": 1, "lps": 127}
        ]
        api.JackeryAPI.circuits_result = [
            {"idx": 1, "nm": "T2ZmaWNl", "pc": 100, "sw": 1, "sph": 0, "pr": 1}
        ]
        coordinator = await self._setup_ts()

        plan_calls = len(api.JackeryAPI.plans_query_calls)
        circuit_calls = len(api.JackeryAPI.circuits_query_calls)

        api.JackeryAPI.device_detail_error = ConnectionError("dns blip")
        # Run enough polls to exceed both PLAN_QUERY_EVERY_N and CIRCUIT_QUERY_EVERY_N
        for _ in range(12):
            await coordinator.update_method()

        self.assertEqual(len(api.JackeryAPI.plans_query_calls), plan_calls)
        self.assertEqual(len(api.JackeryAPI.circuits_query_calls), circuit_calls)

    async def test_plan_cache_preserved_when_query_returns_empty(self) -> None:
        """An empty plan-query response must not wipe the cached plan list."""
        api.JackeryAPI.plans_result = [
            {"pid": "p1", "tt": 0, "st": "22:00", "et": "06:00", "sw": 1, "lps": 127}
        ]
        coordinator = await self._setup_ts()

        self.assertEqual(len(coordinator.data["_plans"]), 1)

        api.JackeryAPI.plans_result = []
        # Drive 4 more polls so the plan counter reaches PLAN_QUERY_EVERY_N (5)
        for _ in range(4):
            await coordinator.update_method()

        self.assertEqual(len(coordinator.data["_plans"]), 1)
        self.assertEqual(coordinator.data["_plans"][0]["pid"], "p1")

    async def test_circuit_cache_preserved_when_query_returns_empty(self) -> None:
        """An empty circuit-query response must not wipe the cached circuit list."""
        api.JackeryAPI.circuits_result = [
            {"idx": 1, "nm": "T2ZmaWNl", "pc": 100, "sw": 1, "sph": 0, "pr": 1}
        ]
        coordinator = await self._setup_ts()

        self.assertEqual(len(coordinator.data["_circuits"]), 1)

        api.JackeryAPI.circuits_result = []
        # Drive 9 more polls so the circuit counter reaches CIRCUIT_QUERY_EVERY_N (10)
        for _ in range(9):
            await coordinator.update_method()

        self.assertEqual(len(coordinator.data["_circuits"]), 1)
        self.assertIn("nm", coordinator.data["_circuits"][0])

    async def test_circuit_nm_guard_blocks_cache_overwrite(self) -> None:
        """Circuit data lacking 'nm' must not replace the named-circuit cache."""
        api.JackeryAPI.circuits_result = [
            {"idx": 1, "nm": "T2ZmaWNl", "pc": 100, "sw": 1, "sph": 0, "pr": 1}
        ]
        coordinator = await self._setup_ts()

        # Simulate a response without nm (e.g. a rogue actionId=1 leak through the api filter)
        api.JackeryAPI.circuits_result = [{"idx": 1, "pc": 200}]
        for _ in range(9):
            await coordinator.update_method()

        self.assertIn("nm", coordinator.data["_circuits"][0])
        self.assertEqual(coordinator.data["_circuits"][0]["pc"], 100)


class CloudStatusTests(unittest.IsolatedAsyncioTestCase):
    """Validate cloud online status parsing and the offline Repair issue."""

    def setUp(self) -> None:
        api.JackeryAPI.reset()
        integration.DataUpdateCoordinator.instances = []
        integration.dt_util.now = lambda: "2026-04-18T19:00:00+01:00"
        integration.dt_util.utcnow = lambda: datetime.now(timezone.utc)
        integration.dt_util.as_local = lambda value: value
        self.created: list = []
        self.deleted: list = []
        integration.ir.IssueSeverity = types.SimpleNamespace(WARNING="warning")
        integration.ir.async_create_issue = (
            lambda hass, domain, issue_id, **kwargs: self.created.append(
                (domain, issue_id, kwargs)
            )
        )
        integration.ir.async_delete_issue = (
            lambda hass, domain, issue_id: self.deleted.append((domain, issue_id))
        )

    @staticmethod
    def _ms(value: datetime) -> int:
        return int(value.timestamp() * 1000)

    async def _setup(self, device_block):
        hass = AsyncSetupEntryTests._make_hass()
        entry = AsyncSetupEntryTests._make_entry()
        api.JackeryAPI.device_list_result = {
            "data": [{"devId": "device-1", "devName": "Explorer 5000 Plus"}]
        }
        api.JackeryAPI.device_detail_results = {
            "device-1": {"data": {"device": device_block, "properties": {"rb": 54}}}
        }
        await integration.async_setup_entry(hass, entry)
        return hass.data["jackery"][entry.entry_id]["coordinators"]["device-1"]

    async def test_cloud_status_added_to_coordinator_data(self) -> None:
        offline_at = datetime(2026, 10, 10, 21, 58, 37, tzinfo=timezone.utc)
        online_at = datetime(2026, 10, 3, 15, 27, 1, tzinfo=timezone.utc)
        coordinator = await self._setup(
            {
                "onlineStatus": 0,
                "onlineTime": self._ms(online_at),
                "offlineTime": self._ms(offline_at),
                "deviceSecret": "secret",
            }
        )

        self.assertIs(coordinator.data["cloud_online"], False)
        self.assertEqual(coordinator.data["cloud_offline_time"], offline_at)
        self.assertEqual(coordinator.data["cloud_online_time"], online_at)
        self.assertNotIn("deviceSecret", coordinator.data)
        self.assertEqual(coordinator.data["rb"], 54)

    async def test_issue_raised_when_offline_past_delay(self) -> None:
        offline_at = datetime.now(timezone.utc) - timedelta(hours=2)
        await self._setup({"onlineStatus": 0, "offlineTime": self._ms(offline_at)})

        self.assertEqual(len(self.created), 1)
        domain, issue_id, kwargs = self.created[0]
        self.assertEqual((domain, issue_id), ("jackery", "device_offline_device-1"))
        self.assertEqual(kwargs["translation_key"], "device_offline")
        self.assertFalse(kwargs["is_fixable"])
        self.assertEqual(
            kwargs["translation_placeholders"]["device_name"], "Explorer 5000 Plus"
        )

    async def test_issue_not_raised_for_short_offline_blip(self) -> None:
        offline_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        await self._setup({"onlineStatus": 0, "offlineTime": self._ms(offline_at)})

        self.assertEqual(self.created, [])

    async def test_issue_cleared_when_device_back_online(self) -> None:
        offline_at = datetime.now(timezone.utc) - timedelta(hours=2)
        coordinator = await self._setup(
            {"onlineStatus": 0, "offlineTime": self._ms(offline_at)}
        )
        api.JackeryAPI.device_detail_results["device-1"]["data"]["device"] = {
            "onlineStatus": 1
        }

        data = await coordinator.update_method()

        self.assertIs(data["cloud_online"], True)
        self.assertIn(("jackery", "device_offline_device-1"), self.deleted)

    async def test_issue_untouched_while_http_poll_is_stale(self) -> None:
        coordinator = await self._setup({"onlineStatus": 1})
        self.deleted.clear()
        api.JackeryAPI.device_detail_error = ConnectionError("dns blip")

        data = await coordinator.update_method()

        self.assertIs(data["cloud_online"], True)
        self.assertEqual(self.created, [])
        self.assertEqual(self.deleted, [])


class PlanServiceTests(unittest.IsolatedAsyncioTestCase):
    """Validate Transfer Switch plan CRUD service handlers."""

    _TS_DEVICE = {
        "devId": "ts-1",
        "devName": "Transfer Switch",
        "devSn": "ts-sn",
        "modelCode": 2001,
    }

    def setUp(self) -> None:
        api.JackeryAPI.reset()
        integration.DataUpdateCoordinator.instances = []
        integration.dt_util.now = lambda: "2026-04-18T19:00:00+01:00"

    @staticmethod
    def _make_hass_with_services():
        """Return (hass, captured_services) capturing registered service handlers."""
        captured: dict = {}

        def capture(domain, name, handler):
            captured[name] = handler

        hass = types.SimpleNamespace(
            data={},
            async_add_executor_job=AsyncMock(side_effect=lambda func, *args: func(*args)),
            config_entries=types.SimpleNamespace(
                async_forward_entry_setups=AsyncMock(),
                async_unload_platforms=AsyncMock(return_value=True),
            ),
            services=types.SimpleNamespace(
                has_service=lambda *a: False,
                async_register=capture,
            ),
        )
        return hass, captured

    async def _setup_ts_with_services(self, plans=None):
        hass, services = self._make_hass_with_services()
        entry = types.SimpleNamespace(
            entry_id="entry-1",
            data={"username": "user@example.com", "password": "hunter2"},
        )
        api.JackeryAPI.device_list_result = {"data": [self._TS_DEVICE]}
        api.JackeryAPI.device_detail_results = {
            "ts-1": {"data": {"properties": {"op": 0}}}
        }
        if plans is not None:
            api.JackeryAPI.plans_result = plans
        await integration.async_setup_entry(hass, entry)
        coordinator = hass.data["jackery"]["entry-1"]["coordinators"]["ts-1"]
        return hass, services, coordinator

    async def test_create_plan_sends_correct_command(self) -> None:
        """create_plan must build the right plan dict and call the API."""
        _, services, _ = await self._setup_ts_with_services()
        call = types.SimpleNamespace(data={
            "type": 0,
            "start_time": "22:00",
            "end_time": "06:00",
            "enabled": True,
            "days": 127,
        })

        with unittest.mock.patch("asyncio.sleep", new_callable=AsyncMock):
            await services["create_plan"](call)

        self.assertEqual(len(api.JackeryAPI.create_plan_calls), 1)
        _, dev_sn, plan = api.JackeryAPI.create_plan_calls[0]
        self.assertEqual(dev_sn, "ts-sn")
        self.assertEqual(plan["tt"], 0)
        self.assertEqual(plan["st"], "22:00")
        self.assertEqual(plan["et"], "06:00")
        self.assertEqual(plan["sw"], 1)
        self.assertEqual(plan["lps"], 127)
        self.assertIn("pid", plan)

    async def test_update_plan_merges_fields_and_patches_coordinator(self) -> None:
        """update_plan must apply only the supplied fields and update coordinator data."""
        existing = {"pid": "42", "tt": 0, "st": "22:00", "et": "06:00", "sw": 1, "lps": 127}
        _, services, coordinator = await self._setup_ts_with_services(plans=[existing])

        call = types.SimpleNamespace(data={"plan_id": "42", "start_time": "23:00"})
        await services["update_plan"](call)

        self.assertEqual(len(api.JackeryAPI.update_plan_calls), 1)
        _, dev_sn, merged = api.JackeryAPI.update_plan_calls[0]
        self.assertEqual(dev_sn, "ts-sn")
        self.assertEqual(merged["pid"], "42")
        self.assertEqual(merged["st"], "23:00")   # updated
        self.assertEqual(merged["et"], "06:00")   # unchanged
        self.assertEqual(merged["tt"], 0)          # unchanged

        self.assertEqual(coordinator.data["_plans"][0]["st"], "23:00")

    async def test_update_plan_raises_when_plan_not_found(self) -> None:
        """update_plan must raise HomeAssistantError when the pid is absent."""
        _, services, _ = await self._setup_ts_with_services(plans=[])

        call = types.SimpleNamespace(data={"plan_id": "nonexistent"})
        with self.assertRaises(integration.HomeAssistantError):
            await services["update_plan"](call)

    async def test_delete_plan_sends_correct_pid(self) -> None:
        """delete_plan must forward the plan_id to the API delete method."""
        _, services, _ = await self._setup_ts_with_services()
        call = types.SimpleNamespace(data={"plan_id": "99"})

        with unittest.mock.patch("asyncio.sleep", new_callable=AsyncMock):
            await services["delete_plan"](call)

        self.assertEqual(len(api.JackeryAPI.delete_plan_calls), 1)
        _, dev_sn, pid = api.JackeryAPI.delete_plan_calls[0]
        self.assertEqual(dev_sn, "ts-sn")
        self.assertEqual(pid, "99")


if __name__ == "__main__":
    unittest.main()
