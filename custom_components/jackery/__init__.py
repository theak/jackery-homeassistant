"""The Jackery integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .api import JackeryAPI, JackeryAuthenticationError
from .const import DOMAIN, POLLING_INTERVAL_SEC
from .features import expected_entity_domain_for_key, expected_unique_ids

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]
_LOGGER = logging.getLogger(__name__)


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
        # Get the list of devices to set up coordinators for each one
        device_list_response = await hass.async_add_executor_job(api.get_device_list)
        devices = device_list_response.get("data", [])
        if not devices:
            _LOGGER.warning("No Jackery devices found for this account.")
            return False
    except JackeryAuthenticationError as err:
        _LOGGER.error("Authentication failed while fetching device list: %s", err)
        return False
    except Exception as err:
        _LOGGER.error("Failed to fetch device list: %s", err)
        return False

    coordinators = {}
    expected_ids: set[str] = set()
    device_registry = dr.async_get(hass)
    for device in devices:
        device_id = device["devId"]
        device_name = device.get("devName", f"Jackery Device {device_id}")

        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            manufacturer="Jackery",
            model=(
                device.get("devModel")
                or device.get("productType")
                or device.get("modelName")
                or device_name
            ),
            name=device_name,
            serial_number=device.get("devSn"),
        )

        async def _async_update_data(api_client=api, dev_id=device_id):
            """Fetch data from API endpoint."""
            try:
                async with async_timeout.timeout(10):
                    data = await hass.async_add_executor_job(
                        api_client.get_device_detail, dev_id
                    )
                    properties = data.get("data", {}).get("properties", {})
                    properties["last_updated"] = dt_util.now()
                    return properties
            except JackeryAuthenticationError as err:
                raise UpdateFailed(f"Authentication error: {err}")
            except Exception as err:
                raise UpdateFailed(f"Error communicating with API: {err}")

        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"Jackery {device_name}",
            update_method=_async_update_data,
            update_interval=timedelta(seconds=POLLING_INTERVAL_SEC),
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators[device_id] = coordinator
        expected_ids.update(expected_unique_ids(device_id, coordinator.data))

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinators": coordinators,
        "devices": devices,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _cleanup_stale_entities(hass, entry, expected_ids)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _cleanup_stale_entities(
    hass: HomeAssistant, entry: ConfigEntry, expected_ids: set[str]
) -> None:
    """Remove entities that no longer match the current device capabilities."""
    entity_registry = er.async_get(hass)
    entries = list(er.async_entries_for_config_entry(entity_registry, entry.entry_id))
    for entity_entry in entries:
        if entity_entry.platform != DOMAIN:
            continue
        if entity_entry.unique_id not in expected_ids:
            entity_registry.async_remove(entity_entry.entity_id)
            continue

        _, _, property_key = entity_entry.unique_id.partition("_")
        expected_domain = expected_entity_domain_for_key(property_key)
        actual_domain, _, _ = entity_entry.entity_id.partition(".")
        if expected_domain is not None and actual_domain != expected_domain:
            entity_registry.async_remove(entity_entry.entity_id)
