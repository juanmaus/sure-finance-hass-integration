"""Tests for the update coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.sure_finance.api_client import APIError
from custom_components.sure_finance.coordinator import SureFinanceDataCoordinator


def build_coordinator(accounts, transactions, side_effect=None):
    client = MagicMock()

    async def get_all_pages(endpoint_func, **kwargs):
        if side_effect is not None:
            raise side_effect
        return accounts if endpoint_func is client.get_accounts else transactions

    client.get_all_pages = AsyncMock(side_effect=get_all_pages)

    coordinator = SureFinanceDataCoordinator.__new__(SureFinanceDataCoordinator)
    coordinator.client = client
    coordinator.currency = "USD"
    return coordinator


class TestUpdateData:
    @pytest.mark.asyncio
    async def test_builds_expected_payload(self, accounts, transactions):
        coordinator = build_coordinator(accounts, transactions)

        data = await coordinator._async_update_data()

        assert set(data) == {"summary", "balances", "monthly_cashflow", "last_update"}
        assert data["summary"]["total_assets"] == 150.0
        assert len(data["balances"]) == 2

    @pytest.mark.asyncio
    async def test_month_start_is_midnight(self, accounts, transactions):
        """The 1st-of-month transaction must survive into monthly_cashflow."""
        coordinator = build_coordinator(accounts, transactions)

        data = await coordinator._async_update_data()

        assert data["monthly_cashflow"]["period_start"].endswith("T00:00:00")

    @pytest.mark.asyncio
    async def test_api_error_becomes_update_failed(self, accounts, transactions):
        """UpdateFailed is what HA translates into ConfigEntryNotReady on first refresh."""
        coordinator = build_coordinator(accounts, transactions, side_effect=APIError("boom", 500))

        with pytest.raises(UpdateFailed, match="Error communicating with Sure Finance API"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_empty_account_list(self):
        coordinator = build_coordinator([], [])

        data = await coordinator._async_update_data()

        assert data["balances"] == []
        assert data["summary"]["net_worth"] == 0.0
