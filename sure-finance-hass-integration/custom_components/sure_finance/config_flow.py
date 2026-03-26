"""Config flow for Sure Finance integration (no cache)."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api_client import SureFinanceClient, AuthenticationError

_LOGGER = logging.getLogger(__name__)

DOMAIN = "sure_finance"

SCHEMA_USER = vol.Schema(
    {
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
        vol.Optional("cache_duration", default=3600): vol.All(  # kept for compatibility
            vol.Coerce(int), vol.Range(min=300, max=86400)
        ),
    }
)


async def _validate(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    client = SureFinanceClient(api_key=data[CONF_API_KEY], base_url=data.get("host"))
    try:
        await client.connect()
        await client.get_accounts()
        await client.close()
    except AuthenticationError:
        raise ValueError("invalid_auth")
    except Exception as err:
        _LOGGER.error("Unexpected error validating Sure Finance: %s", err)
        raise ValueError("cannot_connect")

    return {"title": "Sure Finance"}


class SureFinanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate(self.hass, user_input)
                await self.async_set_unique_id(f"sure_finance_{hash(user_input[CONF_API_KEY])}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)
            except ValueError as exc:
                if str(exc) == "invalid_auth":
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(step_id="user", data_schema=SCHEMA_USER, errors=errors)
