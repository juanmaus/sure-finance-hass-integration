"""Config flow for Sure Finance integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api_client import SureFinanceClient, AuthenticationError

logger = logging.getLogger(__name__)

DOMAIN = "sure_finance"

SCHEMA_USER = vol.Schema({
    vol.Required(CONF_API_KEY): str,
    vol.Optional("host", default="https://app.sure.am"): str,
    vol.Optional("update_interval", default=300): vol.All(
        vol.Coerce(int), vol.Range(min=60, max=3600)
    ),
    vol.Optional("currency", default="USD"): str,
    vol.Optional("enable_cashflow_sensor", default=True): bool,
    vol.Optional("enable_outflow_sensor", default=True): bool,
    vol.Optional("enable_liability_sensor", default=True): bool,
    vol.Optional("enable_account_sensors", default=True): bool,
    vol.Optional("enable_transaction_sensors", default=True): bool,
    vol.Optional("cache_duration", default=3600): vol.All(
        vol.Coerce(int), vol.Range(min=300, max=86400)
    ),
})


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    client = SureFinanceClient(api_key=data[CONF_API_KEY], base_url=data.get("host") or data.get("base_url"))

    try:
        await client.connect()
        await client.get_accounts()
        await client.close()
    except AuthenticationError:
        raise ValueError("invalid_auth")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise ValueError("cannot_connect")
    
    return {"title": "Sure Finance"}


class SureFinanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sure Finance."""
    
    VERSION = 1
    
    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                await self.async_set_unique_id(
                    f"sure_finance_{hash(user_input[CONF_API_KEY])}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input
                )
            except ValueError as e:
                if str(e) == "invalid_auth":
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                logger.exception("Unexpected exception")
                errors["base"] = "unknown"
        
        return self.async_show_form(
            step_id="user",
            data_schema=SCHEMA_USER,
            errors=errors,
            description_placeholders={
                "api_key_url": "https://app.sure.am/settings/api"
            }
        )
    
    async def async_step_import(self, import_data: Dict[str, Any]) -> FlowResult:
        return await self.async_step_user(import_data)
