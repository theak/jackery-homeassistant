"""The Jackery integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .api import JackeryAPI, JackeryAuthenticationError
from .const import DOMAIN, POLLING_INTERVAL_SEC

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.TEXT,
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
        device_list_response = await hass.async_add_executor_job(api.get_device_list)
        devices = device_list_response.get("data", [])
    except JackeryAuthenticationError as err:
        raise ConfigEntryAuthFailed(
            f"Authentication failed while fetching Jackery devices: {err}"
        ) from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to fetch Jackery devices: {err}") from err

    if not devices:
        _LOGGER.warning("No Jackery devices found for this account.")

    coordinators = {}
    for device in devices:
        device_id = device["devId"]
        device_name = device.get("devName", f"Jackery Device {device_id}")

        async def _async_update_data(api_client=api, dev_id=device_id):
            """Fetch data from API endpoint."""
            try:
                async with asyncio.timeout(10):
                    data = await hass.async_add_executor_job(
                        api_client.get_device_detail, dev_id
                    )
                    properties = dict(data.get("data", {}).get("properties", {}))
                    properties["last_updated"] = dt_util.now()
                    return properties
            except JackeryAuthenticationError as err:
                raise ConfigEntryAuthFailed(
                    f"Authentication failed while refreshing Jackery device {dev_id}: {err}"
                ) from err
            except Exception as err:
                raise UpdateFailed(f"Error communicating with API: {err}") from err

        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"Jackery {device_name}",
            update_method=_async_update_data,
            update_interval=timedelta(seconds=POLLING_INTERVAL_SEC),
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators[device_id] = coordinator

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinators": coordinators,
        "devices": devices,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


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
