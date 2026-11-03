"""The Jackery integration."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .api import JackeryAPI, JackeryAuthenticationError
from .const import BINARY_SENSOR_DESCRIPTIONS, DOMAIN, POLLING_INTERVAL_SEC, SENSOR_DESCRIPTIONS
from .protocol import (
    CLOUD_OFFLINE_TIME_KEY,
    CLOUD_STATUS_KEYS,
    CONTROL_SPECS,
    is_cloud_online,
    is_transfer_switch_device,
    parse_cloud_status,
)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.TEXT,
]
_LOGGER = logging.getLogger(__name__)

# Ignore short cloud reconnect blips before asking the user to intervene.
OFFLINE_ISSUE_DELAY = timedelta(minutes=10)


def _offline_issue_id(device_id: str) -> str:
    return f"device_offline_{device_id}"


def _sync_offline_issue(
    hass: HomeAssistant,
    device_id: str,
    device_name: str,
    properties: dict,
    offline_seen: list,
) -> None:
    """Raise a Repair issue once a device has been offline long enough, clear it when back."""
    issue_id = _offline_issue_id(device_id)
    if is_cloud_online(properties):
        offline_seen[0] = None
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return

    now = dt_util.utcnow()
    since = properties.get(CLOUD_OFFLINE_TIME_KEY)
    if not isinstance(since, datetime):
        if offline_seen[0] is None:
            offline_seen[0] = now
        since = offline_seen[0]
    if now - since < OFFLINE_ISSUE_DELAY:
        return

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="device_offline",
        translation_placeholders={
            "device_name": device_name,
            "offline_since": dt_util.as_local(since).strftime("%Y-%m-%d %H:%M"),
        },
    )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Jackery integration."""
    # For config flow based integrations, this function should return True
    # to allow the integration to be discovered and configured via the UI
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jackery from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api = JackeryAPI(
        account=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    try:
        device_list_response = await hass.async_add_executor_job(api.get_device_list)
        devices = device_list_response.get("data", [])
    except JackeryAuthenticationError as err:
        raise ConfigEntryAuthFailed(
            f"Authentication failed while fetching Jackery devices: {err}"
        ) from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to fetch Jackery devices: {err}") from err

    await api.start_mqtt_session()

    if not devices:
        _LOGGER.warning("No Jackery devices found for this account.")

    # Build set of all property keys that have known entity descriptors for
    # unknown-property detection after first coordinator refresh.
    _known_keys: frozenset[str] = frozenset(
        {d.key for d in SENSOR_DESCRIPTIONS}
        | {d.key for d in BINARY_SENSOR_DESCRIPTIONS}
        | set(CONTROL_SPECS)
        | {f"{s}_pack_{i}_rb" for s in ("ac1", "ac2") for i in range(1, 6)}
        | {"last_updated", "_plans", "_circuits", "uo"}
        | CLOUD_STATUS_KEYS
    )

    coordinators = {}
    for device in devices:
        device_id = device["devId"]
        device_name = device.get("devName", f"Jackery Device {device_id}")
        device_sn = device.get("devSn", "")
        is_transfer_switch = is_transfer_switch_device(device)

        _LOGGER.debug(
            "Setting up device: %s (id=%s, sn=%s, modelCode=%s, type=%s)",
            device_name,
            device_id,
            device_sn or "(none)",
            device.get("modelCode"),
            "Transfer Switch" if is_transfer_switch else "portable",
        )

        # Persistent plan cache - survives across coordinator update cycles.
        # Populated by MQTT query on a throttled schedule; injected into every
        # coordinator update so plan entities always have data.
        plan_cache: dict[str, list[dict]] = {"plans": []}
        circuit_cache: dict[str, list[dict]] = {"circuits": []}

        # A DNS/HTTP blip should keep entities available (showing last values)
        # instead of greying out the whole device on a single failed poll.
        properties_cache: dict[str, dict] = {"properties": {}}
        last_success_time: list = [None]
        offline_seen_time: list = [None]
        http_failure_streak = [0]
        plan_poll_counter = [0]
        circuit_poll_counter = [0]
        PLAN_QUERY_EVERY_N = 5  # query plans every Nth poll (~5 min at 60s)
        CIRCUIT_QUERY_EVERY_N = 10  # query circuits every Nth poll (~10 min)
        MAX_HTTP_FAILURES = 15  # tolerate ~15 min of blips before going unavailable

        async def _async_update_data(
            api_client=api,
            dev_id=device_id,
            dev_name=device_name,
            dev_sn=device_sn,
            is_box=is_transfer_switch,
            _counter=plan_poll_counter,
            _cir_counter=circuit_poll_counter,
            _plan_cache=plan_cache,
            _circuit_cache=circuit_cache,
            _props_cache=properties_cache,
            _last_success=last_success_time,
            _offline_seen=offline_seen_time,
            _failures=http_failure_streak,
        ):
            """Fetch data from API endpoint.

            On a HTTP failure, fall back to the last successful
            properties payload (up to MAX_HTTP_FAILURES consecutive misses) so
            entities stay available with their last-known values rather than all
            going unavailable on a single blip.
            """
            stale = False
            try:
                data = await asyncio.wait_for(
                    hass.async_add_executor_job(api_client.get_device_detail, dev_id),
                    timeout=10,
                )
                properties = dict(data.get("data", {}).get("properties", {}))
                properties.update(parse_cloud_status(data.get("data", {}).get("device")))
                # Cache a copy of the raw payload for fallback reuse.
                _props_cache["properties"] = dict(properties)
                _last_success[0] = dt_util.now()
                _failures[0] = 0
            except JackeryAuthenticationError as err:
                raise ConfigEntryAuthFailed(
                    f"Authentication failed while refreshing Jackery device {dev_id}: {err}"
                ) from err
            except Exception as err:
                _failures[0] += 1
                if _props_cache["properties"] and _failures[0] <= MAX_HTTP_FAILURES:
                    _LOGGER.warning(
                        "HTTP refresh failed for %s (%d/%d), using last-known data: %s",
                        dev_id,
                        _failures[0],
                        MAX_HTTP_FAILURES,
                        err,
                    )
                    properties = dict(_props_cache["properties"])
                    stale = True
                else:
                    raise UpdateFailed(f"Error communicating with API: {err}") from err

            if is_box:
                # Skip live MQTT queries while the HTTP path is failing The
                # cached plans/circuits are still injected below.
                if not stale:
                    _counter[0] += 1
                    if _counter[0] >= PLAN_QUERY_EVERY_N:
                        _counter[0] = 0
                        try:
                            plans = await api_client.async_query_transfer_switch_plans(dev_sn)
                            # Only update cache if we got actual plan data
                            if plans:
                                _plan_cache["plans"] = plans
                        except Exception:
                            _LOGGER.debug(
                                "Plan query failed for %s, keeping cached data",
                                dev_sn,
                            )

                    _cir_counter[0] += 1
                    if _cir_counter[0] >= CIRCUIT_QUERY_EVERY_N:
                        _cir_counter[0] = 0
                        try:
                            circuits = await api_client.async_query_transfer_switch_circuits(dev_sn)
                            # Only replace cache with a full metadata response.
                            # Partial actionId=1 pushes lack "nm" and must not overwrite.
                            if circuits and "nm" in circuits[0]:
                                _LOGGER.debug(
                                    "Circuit cache updated with %d circuits for %s",
                                    len(circuits), dev_sn,
                                )
                                _circuit_cache["circuits"] = circuits
                            elif circuits:
                                _LOGGER.warning(
                                    "Circuit query for %s returned %d entries with no 'nm' key - nm-guard blocked overwrite (actionId=1 leak?)",
                                    dev_sn, len(circuits),
                                )
                        except Exception:
                            _LOGGER.debug(
                                "Circuit query failed for %s, keeping cached data",
                                dev_sn,
                            )
                # Always inject cached plans/circuits so entities keep their data
                properties["_plans"] = _plan_cache["plans"]
                properties["_circuits"] = _circuit_cache["circuits"]

            # Flatten nested fault dict so sensors can access
            # individual fault fields as top-level keys (fz_gs, fz_ol, etc.)
            fz = properties.get("fz")
            if isinstance(fz, dict):
                for fk, fv in fz.items():
                    properties[f"fz_{fk}"] = fv

            # Flatten nested battery slot dicts (ac1, ac2) so sensors
            # can access them as ac1_rb, ac1_op, ac2_rb, etc.
            for slot in ("ac1", "ac2"):
                ac = properties.get(slot)
                if isinstance(ac, dict):
                    for ak, av in ac.items():
                        if not isinstance(av, (dict, list)):
                            properties[f"{slot}_{ak}"] = av
                    # Battery pack list: store count, raw list, and per-pack rb/sn
                    bp = ac.get("bp")
                    if isinstance(bp, list):
                        properties[f"{slot}_bp_count"] = len(bp)
                        properties[f"{slot}_bp"] = bp
                        for i, pack in enumerate(bp):
                            pack_num = i + 1
                            properties[f"{slot}_pack_{pack_num}_rb"] = pack.get("rb")
                            properties[f"{slot}_pack_{pack_num}_sn"] = pack.get("sn", "")
                    # The Transfer Switch's ac1/ac2 sub-object doesn't report its own
                    # solar input - borrow it from the connected portable's own
                    # `acpsp` property (matched by serial number) so each slot shows
                    # solar input for whatever device is actually plugged into it.
                    connected_sn = ac.get("sn")
                    if connected_sn:
                        for other_device in devices:
                            if other_device.get("devSn") != connected_sn:
                                continue
                            other_coordinator = coordinators.get(other_device["devId"])
                            if other_coordinator and other_coordinator.data:
                                solar = other_coordinator.data.get("acpsp")
                                if solar is not None:
                                    properties[f"{slot}_acpsp"] = solar
                            break

            # last_updated reflects the last *successful* HTTP fetch so a stale
            # fallback is timestamped for the UI.
            properties["last_updated"] = _last_success[0] or dt_util.now()
            if not stale:
                _sync_offline_issue(hass, dev_id, dev_name, properties, _offline_seen)
            return properties

        # Pre-seed plan and circuit caches before first coordinator refresh
        # so entities are created on the initial setup pass.
        if is_transfer_switch and device_sn:
            try:
                plans = await api.async_query_transfer_switch_plans(device_sn)
                if plans:
                    plan_cache["plans"] = plans
                    _LOGGER.debug("Pre-loaded %d plans for %s", len(plans), device_sn)
                else:
                    _LOGGER.debug("Initial plan query returned empty for %s", device_sn)
            except Exception:
                _LOGGER.debug("Initial plan query failed for %s, will retry", device_sn)
            try:
                circuits = await api.async_query_transfer_switch_circuits(device_sn)
                if circuits:
                    circuit_cache["circuits"] = circuits
                    _LOGGER.debug("Pre-loaded %d circuits for %s", len(circuits), device_sn)
                else:
                    _LOGGER.debug("Initial circuit query returned empty for %s", device_sn)
            except Exception:
                _LOGGER.debug("Initial circuit query failed for %s, will retry", device_sn)

        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"Jackery {device_name}",
            update_method=_async_update_data,
            update_interval=timedelta(seconds=POLLING_INTERVAL_SEC),
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators[device_id] = coordinator

        if coordinator.data:
            # Re-check after first refresh in case modelCode was unrecognised.
            if not is_transfer_switch and is_transfer_switch_device(device, coordinator.data):
                is_transfer_switch = True
                _LOGGER.info(
                    "Device %s (modelCode=%s) reclassified as Transfer Switch "
                    "based on reported properties - modelCode list may need updating.",
                    device_name,
                    device.get("modelCode"),
                )

            reported = {k for k in coordinator.data if not k.startswith("_")}
            _LOGGER.debug(
                "Device %s reported %d properties: %s",
                device_name,
                len(reported),
                sorted(reported),
            )
            unknown = reported - _known_keys - {"last_updated"}
            if unknown:
                _LOGGER.info(
                    "Device %s reports %d unmapped propert%s: %s - "
                    "consider adding entity descriptors for these.",
                    device_name,
                    len(unknown),
                    "y" if len(unknown) == 1 else "ies",
                    sorted(unknown),
                )

        if is_transfer_switch and device_sn:
            # Real-time circuit power + total op/ip from Transfer Switch actionId=1 pushes.
            api.register_push_handler(
                device_sn,
                _make_circuit_push_handler(circuit_cache, coordinator),
            )
        elif device_sn:
            # Real-time scalar fields (acpsp, ip, it, …) from portable device pushes.
            api.register_push_handler(
                device_sn,
                _make_device_push_handler(coordinator),
            )

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinators": coordinators,
        "devices": devices,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register plan services (idempotent - only registers once per domain)
    if not hass.services.has_service(DOMAIN, "create_plan"):
        _register_plan_services(hass)

    return True


def _make_device_push_handler(coordinator) -> callable:
    """Return a push handler that merges scalar DevicePropertyChange fields."""
    def _handle(data: dict) -> None:
        if data.get("messageType") != "DevicePropertyChange":
            return
        body = data.get("body")
        if not isinstance(body, dict) or coordinator.data is None:
            return
        changed = False
        new_data = dict(coordinator.data)
        for key, val in body.items():
            if isinstance(val, (int, float)) and new_data.get(key) != val:
                new_data[key] = val
                changed = True
        if changed:
            coordinator.data = new_data
            coordinator.async_update_listeners()
    return _handle


def _make_circuit_push_handler(circuit_cache: dict, coordinator) -> callable:
    """Return a push handler that merges Transfer Switch push data."""
    def _handle(data: dict) -> None:
        if data.get("actionId") != 1:
            return
        body = data.get("body")
        if not isinstance(body, dict) or coordinator.data is None:
            return

        changed = False
        new_data = dict(coordinator.data)

        # Merge top-level power fields without waiting for the next HTTP poll.
        for field in ("op", "ip"):
            val = body.get(field)
            if val is not None and new_data.get(field) != val:
                new_data[field] = val
                changed = True

        # Merge per-circuit pc values from partial push.
        if "cir" in body:
            cached = circuit_cache["circuits"]
            if cached:
                updates = {
                    c["idx"]: c["pc"]
                    for c in body["cir"]
                    if "idx" in c and "pc" in c
                }
                cir_changed = False
                for circuit in cached:
                    new_pc = updates.get(circuit["idx"])
                    if new_pc is not None and circuit.get("pc") != new_pc:
                        circuit["pc"] = new_pc
                        cir_changed = True
                if cir_changed:
                    new_data["_circuits"] = list(cached)
                    changed = True
                    _LOGGER.debug("Circuit push: updated pc for %d circuits", len(updates))

        if changed:
            # Direct assignment avoids resetting the coordinator's scheduled HTTP poll timer
            coordinator.data = new_data
            coordinator.async_update_listeners()
    return _handle


def _find_transfer_switch(hass: HomeAssistant) -> tuple[JackeryAPI, str, str] | None:
    """Find the first Transfer Switch device across all config entries."""
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if not isinstance(entry_data, dict):
            continue
        api = entry_data.get("api")
        for device in entry_data.get("devices", []):
            if device.get("modelCode") == 2001:
                return api, device["devId"], device["devSn"]
    return None


def _register_plan_services(hass: HomeAssistant) -> None:
    """Register jackery.create_plan, jackery.update_plan, jackery.delete_plan."""
    _LOGGER.info("Registering plan CRUD services")

    async def _refresh_plans_now(api: JackeryAPI, dev_sn: str) -> None:
        """Query fresh plans from device and push into coordinator data."""
        # Give the device time to finish processing the CRUD command
        await asyncio.sleep(2)
        try:
            plans = await api.async_query_transfer_switch_plans(dev_sn)
        except Exception:
            _LOGGER.debug("Post-CRUD plan refresh failed for %s", dev_sn)
            plans = None
        if not plans:
            _LOGGER.debug("Post-CRUD plan query returned empty for %s, keeping cached data", dev_sn)
            return
        for entry_data in hass.data.get(DOMAIN, {}).values():
            if not isinstance(entry_data, dict):
                continue
            for coordinator in entry_data.get("coordinators", {}).values():
                if coordinator.data and coordinator.data.get("_plans") is not None:
                    new_data = dict(coordinator.data)
                    new_data["_plans"] = plans
                    coordinator.async_set_updated_data(new_data)

    async def _handle_create_plan(call: ServiceCall) -> None:
        _LOGGER.info("create_plan service called with: %s", call.data)
        result = _find_transfer_switch(hass)
        if result is None:
            raise HomeAssistantError("No Transfer Switch found")
        api, dev_id, dev_sn = result

        plan = {
            "pid": str(int(time.time())),
            "tt": int(call.data["type"]),
            "st": call.data["start_time"],
            "et": call.data["end_time"],
            "sw": 1 if call.data.get("enabled", True) else 0,
            "lps": call.data["days"],
        }
        await api.async_create_transfer_switch_plan(dev_id, dev_sn, plan)
        await _refresh_plans_now(api, dev_sn)

    async def _handle_update_plan(call: ServiceCall) -> None:
        _LOGGER.info("update_plan service called with: %s", call.data)
        result = _find_transfer_switch(hass)
        if result is None:
            raise HomeAssistantError("No Transfer Switch found")
        api, dev_id, dev_sn = result

        pid = call.data["plan_id"]

        # Find existing plan in coordinator data so we send a full plan dict
        existing_plan = None
        coordinator = None
        for entry_data in hass.data.get(DOMAIN, {}).values():
            if not isinstance(entry_data, dict):
                continue
            for coord in entry_data.get("coordinators", {}).values():
                if coord.data and coord.data.get("_plans") is not None:
                    for p in coord.data["_plans"]:
                        if str(p.get("pid")) == str(pid):
                            existing_plan = p
                            coordinator = coord
                            break

        if existing_plan is None:
            raise HomeAssistantError(f"Plan {pid} not found in coordinator data")

        # Start from full existing plan, apply requested changes
        plan = dict(existing_plan)
        if "type" in call.data:
            plan["tt"] = int(call.data["type"])
        if "start_time" in call.data:
            plan["st"] = call.data["start_time"]
        if "end_time" in call.data:
            plan["et"] = call.data["end_time"]
        if "enabled" in call.data:
            plan["sw"] = 1 if call.data["enabled"] else 0
        if "days" in call.data:
            plan["lps"] = call.data["days"]

        await api.async_update_transfer_switch_plan(dev_id, dev_sn, plan)

        # Optimistic update: patch coordinator data in place
        if coordinator is not None:
            for p in coordinator.data.get("_plans", []):
                if str(p.get("pid")) == str(pid):
                    p.update(plan)
                    break
            coordinator.async_set_updated_data(coordinator.data)

    async def _handle_delete_plan(call: ServiceCall) -> None:
        _LOGGER.info("delete_plan service called with: %s", call.data)
        result = _find_transfer_switch(hass)
        if result is None:
            raise HomeAssistantError("No Transfer Switch found")
        api, dev_id, dev_sn = result
        _LOGGER.info("Deleting plan %s on device %s", call.data["plan_id"], dev_sn)

        await api.async_delete_transfer_switch_plan(
            dev_id, dev_sn, call.data["plan_id"],
        )
        await _refresh_plans_now(api, dev_sn)

    hass.services.async_register(DOMAIN, "create_plan", _handle_create_plan)
    hass.services.async_register(DOMAIN, "update_plan", _handle_update_plan)
    hass.services.async_register(DOMAIN, "delete_plan", _handle_delete_plan)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    domain_data = hass.data.get(DOMAIN)
    entry_data = domain_data.get(entry.entry_id) if domain_data is not None else None
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if entry_data is not None:
            await entry_data["api"].async_close()
        if domain_data is not None:
            domain_data.pop(entry.entry_id, None)

    return unload_ok
