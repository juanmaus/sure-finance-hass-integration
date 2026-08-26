"""Tests for the sensor entities and platform setup."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.sure_finance import sensor as sensor_module
from custom_components.sure_finance.const import DOMAIN
from custom_components.sure_finance.sensor import (
    AccountBalanceSensor,
    CashflowSensor,
    LiabilitySensor,
    MonthlySavingsRateSensor,
    NetWorthSensor,
    OutflowSensor,
    async_setup_entry,
)

COORDINATOR_DATA = {
    "summary": {
        "total_cashflow": 100000.0,
        "total_outflow": 30000.5,
        "total_assets": 150.0,
        "total_liabilities": 678855.1,
        "net_worth": -678705.1,
        "currency": "USD",
        "last_updated": "2026-08-26T05:37:22",
    },
    "balances": [
        {
            "account_id": "acc-1",
            "account_name": "Bac VISA",
            "balance": -678855.1,
            "currency": "CRC",
            "classification": "liability",
            "last_updated": "2026-08-26T05:28:17Z",
        },
        {
            "account_id": "acc-2",
            "account_name": "Bac Colones",
            "balance": 150.0,
            "currency": "USD",
            "classification": "asset",
            "last_updated": "2026-08-26T05:28:17Z",
        },
    ],
    "monthly_cashflow": {
        "total_income": 100000.0,
        "total_expenses": 30000.5,
        "net_cashflow": 69999.5,
        "income_by_category": {"Income": 100000.0},
        "expenses_by_category": {"Groceries": 25000.5, "Uncategorized": 5000.0},
    },
}


@pytest.fixture
def coordinator():
    coord = MagicMock()
    coord.data = COORDINATOR_DATA
    return coord


@pytest.fixture
def empty_coordinator():
    """Coordinator that has never produced data — every sensor must still read."""
    coord = MagicMock()
    coord.data = None
    return coord


class TestSensorValues:
    def test_net_worth(self, coordinator):
        s = NetWorthSensor(coordinator, "net_worth", "Net Worth", "mdi:bank", "USD")

        assert s.native_value == -678705.1
        assert s.unique_id == "sure_finance_net_worth"
        assert s.name == "Sure Finance Net Worth"
        assert s.extra_state_attributes["total_assets"] == 150.0

    def test_cashflow(self, coordinator):
        s = CashflowSensor(coordinator, "total_cashflow", "Total Cashflow", "mdi:cash-plus", "USD")

        assert s.native_value == 100000.0
        assert s.extra_state_attributes["income_by_category"] == {"Income": 100000.0}

    def test_outflow(self, coordinator):
        s = OutflowSensor(coordinator, "total_outflow", "Total Outflow", "mdi:cash-minus", "USD")

        assert s.native_value == 30000.5
        assert s.extra_state_attributes["monthly_expenses"] == 30000.5

    def test_liability_lists_only_liability_accounts(self, coordinator):
        s = LiabilitySensor(coordinator, "total_liability", "Total Liability", "mdi:bank", "USD")

        assert s.native_value == 678855.1
        accounts = s.extra_state_attributes["liability_accounts"]
        assert accounts == [{"name": "Bac VISA", "balance": -678855.1}]

    def test_account_balance(self, coordinator):
        s = AccountBalanceSensor(coordinator, COORDINATOR_DATA["balances"][1])

        assert s.native_value == 150.0
        assert s.unique_id == "sure_finance_account_acc-2"
        assert s.native_unit_of_measurement == "USD"
        assert s.extra_state_attributes["classification"] == "asset"

    def test_account_balance_missing_from_payload(self, coordinator):
        s = AccountBalanceSensor(coordinator, {"account_id": "gone", "account_name": "Closed"})

        assert s.native_value == 0.0
        assert s.extra_state_attributes == {"account_name": "Closed"}

    def test_savings_rate(self, coordinator):
        s = MonthlySavingsRateSensor(coordinator)

        assert s.native_value == 70.0
        assert s.device_class is None
        assert s.native_unit_of_measurement == "%"

    def test_savings_rate_zero_income(self, coordinator):
        coordinator.data = {**COORDINATOR_DATA, "monthly_cashflow": {"total_income": 0}}
        s = MonthlySavingsRateSensor(coordinator)

        assert s.native_value == 0.0


class TestSensorsWithoutData:
    """A failed refresh must not turn attribute access into an exception."""

    @pytest.mark.parametrize(
        "factory",
        [
            lambda c: NetWorthSensor(c, "net_worth", "Net Worth", "mdi:bank", "USD"),
            lambda c: CashflowSensor(c, "cf", "Cashflow", "mdi:cash", "USD"),
            lambda c: OutflowSensor(c, "of", "Outflow", "mdi:cash", "USD"),
            lambda c: LiabilitySensor(c, "li", "Liability", "mdi:bank", "USD"),
            lambda c: MonthlySavingsRateSensor(c),
            lambda c: AccountBalanceSensor(c, {"account_id": "a", "account_name": "A"}),
        ],
    )
    def test_reads_zero_and_does_not_raise(self, empty_coordinator, factory):
        s = factory(empty_coordinator)

        assert s.native_value == 0.0
        assert isinstance(s.extra_state_attributes, dict)


class TestAsyncSetupEntry:
    @staticmethod
    def _run_setup(coordinator, entry_data):
        import asyncio

        hass = MagicMock()
        hass.data = {DOMAIN: {"entry-1": {"coordinator": coordinator}}}
        entry = MagicMock()
        entry.entry_id = "entry-1"
        entry.data = entry_data

        added = []
        asyncio.run(async_setup_entry(hass, entry, lambda s: added.extend(s)))
        return added

    def test_all_sensors_enabled(self, coordinator):
        added = self._run_setup(coordinator, {})

        types = [type(s) for s in added]
        assert NetWorthSensor in types
        assert CashflowSensor in types
        assert OutflowSensor in types
        assert LiabilitySensor in types
        assert MonthlySavingsRateSensor in types
        # One per account in the coordinator payload.
        assert sum(1 for s in added if isinstance(s, AccountBalanceSensor)) == 2

    def test_toggles_are_honoured(self, coordinator):
        added = self._run_setup(
            coordinator,
            {
                "enable_cashflow_sensor": False,
                "enable_outflow_sensor": False,
                "enable_liability_sensor": False,
                "enable_account_sensors": False,
            },
        )

        types = [type(s) for s in added]
        assert types == [NetWorthSensor, MonthlySavingsRateSensor]

    def test_currency_applied(self, coordinator):
        added = self._run_setup(coordinator, {"currency": "EUR", "enable_account_sensors": False})

        net_worth = next(s for s in added if isinstance(s, NetWorthSensor))
        assert net_worth.native_unit_of_measurement == "EUR"

    def test_no_account_sensors_when_payload_empty(self, empty_coordinator):
        added = self._run_setup(empty_coordinator, {})

        assert not any(isinstance(s, AccountBalanceSensor) for s in added)
