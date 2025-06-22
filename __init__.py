"""The Jackery integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import JackeryAPI, JackeryAuthenticationError
from .const import DOMAIN, POLLING_INTERVAL_SEC

PLATFORMS: list[Platform] = [Platform.SENSOR]
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
    for device in devices:
        device_id = device["devId"]
        device_name = device.get("devName", f"Jackery Device {device_id}")

        async def _async_update_data(api_client=api, dev_id=device_id):
            """Fetch data from API endpoint."""
            try:
                async with async_timeout.timeout(10):
                    data = await hass.async_add_executor_job(
                        api_client.get_device_detail, dev_id
                    )
                    return data.get("data", {}).get("properties", {})
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

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinators": coordinators,
        "devices": devices,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
