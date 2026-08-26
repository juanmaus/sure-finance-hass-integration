"""Sure Finance Home Assistant Integration.

Creates sensor entities by querying the Sure Finance API directly on each update.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .api_client import AuthenticationError, SureFinanceClient
from .const import (
    DEFAULT_CURRENCY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SERVICE_REFRESH_DATA,
)
from .coordinator import SureFinanceDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Sure Finance component (namespace)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sure Finance from a config entry."""
    cfg = entry.data

    api_client = SureFinanceClient(
        api_key=cfg["api_key"],
        base_url=cfg.get("host") or cfg.get("base_url"),
        timeout=30,
    )

    coordinator = SureFinanceDataCoordinator(
        hass,
        api_client,
        currency=cfg.get("currency", DEFAULT_CURRENCY),
        update_interval_s=cfg.get("update_interval", DEFAULT_UPDATE_INTERVAL),
    )

    # The first fetch happens here rather than in the sensor platform, so that a
    # failing API surfaces as ConfigEntryNotReady from entry setup. Raising it
    # from inside async_forward_entry_setups is an error in Home Assistant.
    try:
        await api_client.connect()
        await coordinator.async_config_entry_first_refresh()
    except AuthenticationError:
        await api_client.close()
        _LOGGER.error("Invalid API key for Sure Finance")
        return False
    except Exception:
        # Always drop the aiohttp session; HA retries setup and would otherwise
        # leak one ClientSession per attempt.
        await api_client.close()
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api_client": api_client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["api_client"].close()

        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH_DATA)

    return unload_ok


def _async_setup_services(hass: HomeAssistant) -> None:
    """Register Sure Finance services (once, shared by all entries)."""
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH_DATA):
        return

    async def refresh_data(call: ServiceCall) -> None:
        """Refresh every configured Sure Finance entry now."""
        for entry_data in hass.data.get(DOMAIN, {}).values():
            await entry_data["coordinator"].async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH_DATA, refresh_data)
