"""Sure Finance Home Assistant Integration."""

import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api_client import SureFinanceClient, AuthenticationError
from .cache_manager import CacheManager
from .data_manager import DataManager
from .financial_calculator import FinancialCalculator

logger = logging.getLogger(__name__)

DOMAIN = "sure_finance"
PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Sure Finance component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sure Finance from a config entry."""
    config = entry.data

    # Create API client
    api_client = SureFinanceClient(
        api_key=config["api_key"],
        base_url=config.get("host") or config.get("base_url"),
        timeout=30
    )

    # Test authentication
    try:
        await api_client.connect()
        # Try a simple API call to verify credentials
        await api_client.get_accounts()
    except AuthenticationError:
        logger.error("Invalid API key for Sure Finance")
        return False
    except Exception as e:
        logger.error(f"Failed to connect to Sure Finance API: {e}")
        raise ConfigEntryNotReady from e

    # Create cache manager
    cache_manager = CacheManager(
        cache_dir=hass.config.path("custom_components", DOMAIN, "cache"),
        default_ttl=config.get("cache_duration", 3600)
    )
    await cache_manager.connect_redis()

    # Create financial calculator
    calculator = FinancialCalculator(currency=config.get("currency", "USD"))

    # Create data manager
    data_manager = DataManager(
        api_client=api_client,
        cache_manager=cache_manager,
        calculator=calculator,
        update_interval=config.get("update_interval", 300)
    )

    # Store instances for platforms
    hass.data[DOMAIN][entry.entry_id] = {
        "api_client": api_client,
        "cache_manager": cache_manager,
        "data_manager": data_manager,
        "calculator": calculator
    }

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["api_client"].close()
        await data["cache_manager"].close()

        # Remove services if no more entries
        if not hass.data[DOMAIN]:
            await async_remove_services(hass)

    return unload_ok


async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up Sure Finance services."""

    async def refresh_data(call):
        """Service to manually refresh data."""
        data_manager = hass.data[DOMAIN][entry.entry_id]["data_manager"]
        await data_manager.sync_all_data()

        # Update sensors
        if "coordinator" in hass.data[DOMAIN][entry.entry_id]:
            await hass.data[DOMAIN][entry.entry_id]["coordinator"].async_request_refresh()

    async def clear_cache(call):
        """Service to clear cache."""
        cache_manager = hass.data[DOMAIN][entry.entry_id]["cache_manager"]
        await cache_manager.clear_namespace("accounts")
        await cache_manager.clear_namespace("transactions")
        await cache_manager.clear_namespace("summaries")
        await cache_manager.clear_namespace("cashflow")
        logger.info("Sure Finance cache cleared")

    # Register services
    hass.services.async_register(DOMAIN, "refresh_data", refresh_data)
    hass.services.async_register(DOMAIN, "clear_cache", clear_cache)


async def async_remove_services(hass: HomeAssistant) -> None:
    """Remove Sure Finance services."""
    hass.services.async_remove(DOMAIN, "refresh_data")
    hass.services.async_remove(DOMAIN, "clear_cache")
