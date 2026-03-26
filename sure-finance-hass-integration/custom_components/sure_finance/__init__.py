"""Sure Finance Home Assistant Integration (no cache).

Creates sensor entities by querying the Sure Finance API directly on each update.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api_client import SureFinanceClient, AuthenticationError
from .financial_calculator import FinancialCalculator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "sure_finance"
PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Sure Finance component (namespace)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sure Finance from a config entry (no cache)."""
    cfg = entry.data

    # Create API client
    api_client = SureFinanceClient(
        api_key=cfg["api_key"],
        base_url=cfg.get("host") or cfg.get("base_url"),
        timeout=30,
    )

    # Verify connection
    try:
        await api_client.connect()
        await api_client.get_accounts()  # simple call to validate
    except AuthenticationError:
        _LOGGER.error("Invalid API key for Sure Finance")
        return False
    except Exception as err:
        _LOGGER.error("Failed to connect to Sure Finance API: %s", err)
        raise ConfigEntryNotReady from err

    # Financial calculator
    calculator = FinancialCalculator(currency=cfg.get("currency", "USD"))

    # Store instances for platforms
    hass.data[DOMAIN][entry.entry_id] = {
        "api_client": api_client,
        "calculator": calculator,
    }

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services (refresh only; no cache to clear)
    await async_setup_services(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["api_client"].close()
        # coordinator removed by platform when unloading

        if not hass.data[DOMAIN]:
            await async_remove_services(hass)

    return unload_ok


async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register Sure Finance services."""

    async def refresh_data(call):
        """Trigger sensors to refresh now."""
        coord = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        if coord:
            await coord.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh_data", refresh_data)


async def async_remove_services(hass: HomeAssistant) -> None:
    """Remove Sure Finance services."""
    hass.services.async_remove(DOMAIN, "refresh_data")
