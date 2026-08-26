"""Tests for the config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol

from custom_components.sure_finance import config_flow as config_flow_module
from custom_components.sure_finance.api_client import AuthenticationError
from custom_components.sure_finance.config_flow import (
    SCHEMA_USER,
    SureFinanceConfigFlow,
    _validate,
)


class TestSchema:
    def test_defaults(self):
        result = SCHEMA_USER({"api_key": "secret"})

        assert result["host"] == "https://app.sure.am"
        assert result["update_interval"] == 300
        assert result["currency"] == "USD"
        assert result["enable_cashflow_sensor"] is True

    def test_api_key_required(self):
        with pytest.raises(vol.Invalid):
            SCHEMA_USER({})

    @pytest.mark.parametrize("interval", [59, 3601])
    def test_update_interval_bounds(self, interval):
        with pytest.raises(vol.Invalid):
            SCHEMA_USER({"api_key": "k", "update_interval": interval})

    def test_cache_duration_no_longer_offered(self):
        """There is no cache any more, so the field must not resurface."""
        assert "cache_duration" not in {str(k) for k in SCHEMA_USER.schema}


class TestValidate:
    @pytest.mark.asyncio
    async def test_success(self):
        client = MagicMock()
        client.connect = AsyncMock()
        client.get_accounts = AsyncMock(return_value={"accounts": []})
        client.close = AsyncMock()

        with patch.object(config_flow_module, "SureFinanceClient", return_value=client):
            result = await _validate(MagicMock(), {"api_key": "secret"})

        assert result == {"title": "Sure Finance"}
        client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_auth(self):
        client = MagicMock()
        client.connect = AsyncMock()
        client.get_accounts = AsyncMock(side_effect=AuthenticationError("bad", 401))

        with patch.object(config_flow_module, "SureFinanceClient", return_value=client):
            with pytest.raises(ValueError, match="invalid_auth"):
                await _validate(MagicMock(), {"api_key": "bad"})

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        client = MagicMock()
        client.connect = AsyncMock(side_effect=OSError("network down"))

        with patch.object(config_flow_module, "SureFinanceClient", return_value=client):
            with pytest.raises(ValueError, match="cannot_connect"):
                await _validate(MagicMock(), {"api_key": "k"})


class TestFlowSteps:
    @staticmethod
    def build_flow():
        flow = SureFinanceConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(side_effect=lambda **kw: {"type": "create", **kw})
        flow.async_show_form = MagicMock(side_effect=lambda **kw: {"type": "form", **kw})
        return flow

    @pytest.mark.asyncio
    async def test_shows_form_initially(self):
        result = await self.build_flow().async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    @pytest.mark.asyncio
    async def test_creates_entry(self):
        flow = self.build_flow()
        user_input = {"api_key": "secret", "currency": "USD"}

        with patch.object(
            config_flow_module, "_validate", AsyncMock(return_value={"title": "Sure Finance"})
        ):
            result = await flow.async_step_user(user_input)

        assert result["type"] == "create"
        assert result["title"] == "Sure Finance"
        assert result["data"] == user_input

    @pytest.mark.parametrize(
        "error,expected",
        [("invalid_auth", "invalid_auth"), ("cannot_connect", "cannot_connect")],
    )
    @pytest.mark.asyncio
    async def test_surfaces_validation_errors(self, error, expected):
        flow = self.build_flow()

        with patch.object(config_flow_module, "_validate", AsyncMock(side_effect=ValueError(error))):
            result = await flow.async_step_user({"api_key": "k"})

        assert result["errors"] == {"base": expected}

    @pytest.mark.asyncio
    async def test_unexpected_error(self):
        flow = self.build_flow()

        with patch.object(config_flow_module, "_validate", AsyncMock(side_effect=RuntimeError)):
            result = await flow.async_step_user({"api_key": "k"})

        assert result["errors"] == {"base": "unknown"}
