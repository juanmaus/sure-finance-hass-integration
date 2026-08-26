"""Tests for the dict-based financial calculator."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from custom_components.sure_finance.financial_calculator import (
    _parse_decimal,
    calculate_financial_summary,
    calculate_monthly_cashflow,
    get_account_balances,
)
from tests.conftest import SLIM_CATEGORY, make_transaction


class TestParseDecimal:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("$418.40", Decimal("418.40")),
            ("₡5.450,00", Decimal("5450.00")),
            ("-₡71.265,92", Decimal("-71265.92")),
            ("$0.00", Decimal("0")),
            ("(1,234.56)", Decimal("-1234.56")),
            ("1234", Decimal("1234")),
            (12.5, Decimal("12.5")),
            (Decimal("7"), Decimal("7")),
        ],
    )
    def test_parses_localised_money(self, raw, expected):
        assert _parse_decimal(raw) == expected

    @pytest.mark.parametrize("raw", [None, "", "abc", {}, []])
    def test_unparseable_becomes_zero(self, raw):
        """Never raises — a bad amount must not take down a whole refresh."""
        assert _parse_decimal(raw) == Decimal("0")


class TestFinancialSummary:
    def test_splits_assets_and_liabilities(self, accounts, transactions):
        summary = calculate_financial_summary(accounts, transactions, "USD")

        assert summary["total_assets"] == 150.0
        assert summary["total_liabilities"] == 678855.10
        assert summary["net_worth"] == pytest.approx(150.0 - 678855.10)
        assert summary["currency"] == "USD"

    def test_income_and_expense_totals(self, accounts, transactions):
        summary = calculate_financial_summary(accounts, transactions, "USD")

        assert summary["total_cashflow"] == 100000.0
        assert summary["total_outflow"] == pytest.approx(25000.50 + 5000.00)

    def test_handles_no_transactions(self, accounts):
        summary = calculate_financial_summary(accounts, None, "USD")

        assert summary["total_cashflow"] == 0.0
        assert summary["total_outflow"] == 0.0

    def test_unknown_classification_is_ignored(self):
        accounts = [{"balance": "$5.00", "classification": "unknown"}]
        summary = calculate_financial_summary(accounts, [], "USD")

        assert summary["total_assets"] == 0.0
        assert summary["total_liabilities"] == 0.0


class TestAccountBalances:
    def test_maps_api_accounts(self, accounts):
        balances = get_account_balances(accounts, "USD")

        assert len(balances) == 2
        liability = balances[0]
        assert liability["account_name"] == "Bac VISA Pricesmart"
        assert liability["classification"] == "liability"
        assert liability["balance"] == -678855.10
        assert liability["currency"] == "CRC"

    def test_defaults_missing_classification_to_asset(self):
        balances = get_account_balances([{"id": "x", "name": "n", "balance": "$1.00"}], "EUR")

        assert balances[0]["classification"] == "asset"
        assert balances[0]["currency"] == "EUR"


class TestMonthlyCashflow:
    def test_includes_transactions_dated_the_first(self, transactions):
        """Regression: a month_start carrying a time-of-day dropped the 1st.

        Transaction dates have no time component, so they parse to midnight.
        """
        now = datetime(2026, 8, 25, 23, 36)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = calculate_monthly_cashflow(transactions, month_start, now, "USD")

        assert result["total_income"] == 100000.0

    def test_time_bearing_month_start_would_drop_it(self, transactions):
        """Documents the old behaviour this integration used to have."""
        now = datetime(2026, 8, 25, 23, 36)

        result = calculate_monthly_cashflow(transactions, now.replace(day=1), now, "USD")

        assert result["total_income"] == 0.0

    def test_groups_by_category_name(self, transactions):
        now = datetime(2026, 8, 25, 23, 36)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = calculate_monthly_cashflow(transactions, month_start, now, "USD")

        assert result["income_by_category"] == {"Income": 100000.0}
        assert result["expenses_by_category"] == {
            "Groceries": 25000.50,
            "Uncategorized": 5000.0,
        }
        assert result["net_cashflow"] == pytest.approx(100000.0 - 30000.50)

    def test_null_category_becomes_uncategorized(self):
        tx = make_transaction(date="2026-08-10", amount="-100", classification="expense")
        result = calculate_monthly_cashflow(
            [tx], datetime(2026, 8, 1), datetime(2026, 8, 31), "USD"
        )

        assert result["expenses_by_category"] == {"Uncategorized": 100.0}

    def test_slim_category_without_classification_is_fine(self):
        """The v1 pydantic models required category.classification; the API omits it."""
        tx = make_transaction(
            date="2026-08-10", amount="500", classification="income", category=SLIM_CATEGORY
        )

        result = calculate_monthly_cashflow(
            [tx], datetime(2026, 8, 1), datetime(2026, 8, 31), "USD"
        )

        assert result["income_by_category"] == {"Income": 500.0}

    def test_iso_timestamp_dates(self):
        tx = make_transaction(
            date="2026-08-10T14:30:00Z", amount="200", classification="income"
        )
        result = calculate_monthly_cashflow(
            [tx], datetime(2026, 8, 1), datetime(2026, 8, 31), "USD"
        )

        assert result["total_income"] == 200.0

    @pytest.mark.parametrize("bad_date", [None, "", "not-a-date"])
    def test_undateable_transactions_are_skipped(self, bad_date):
        tx = make_transaction(date=bad_date, amount="200", classification="income")
        result = calculate_monthly_cashflow(
            [tx], datetime(2026, 8, 1), datetime(2026, 8, 31), "USD"
        )

        assert result["total_income"] == 0.0

    def test_out_of_range_transactions_excluded(self, transactions):
        result = calculate_monthly_cashflow(
            transactions, datetime(2026, 9, 1), datetime(2026, 9, 30), "USD"
        )

        assert result["total_income"] == 0.0
        assert result["total_expenses"] == 0.0
