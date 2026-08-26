"""Update coordinator for Sure Finance.

Queries the Sure Finance API directly on every refresh; there is no cache layer.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import APIError, SureFinanceClient
from .const import DOMAIN, TRANSACTION_WINDOW_DAYS
from .financial_calculator import (
    calculate_financial_summary,
    calculate_monthly_cashflow,
    get_account_balances,
)

_LOGGER = logging.getLogger(__name__)


class SureFinanceDataCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Fetch accounts and recent transactions and derive the sensor payload."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SureFinanceClient,
        currency: str,
        update_interval_s: int,
    ) -> None:
        self.client = client
        self.currency = currency
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval_s),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        now = datetime.utcnow()
        start = now - timedelta(days=TRANSACTION_WINDOW_DAYS)

        try:
            accounts = await self.client.get_all_pages(self.client.get_accounts, per_page=100)
            transactions = await self.client.get_all_pages(
                self.client.get_transactions,
                per_page=100,
                start_date=start,
                end_date=now,
            )
        except APIError as err:
            raise UpdateFailed(f"Error communicating with Sure Finance API: {err}") from err

        # Midnight on the 1st: transaction dates carry no time component, so a
        # month_start of "now, day=1" would exclude everything dated the 1st.
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return {
            "summary": calculate_financial_summary(accounts, transactions, self.currency),
            "balances": get_account_balances(accounts, self.currency),
            "monthly_cashflow": calculate_monthly_cashflow(
                transactions, month_start, now, self.currency
            ),
            "last_update": now.isoformat(),
        }
