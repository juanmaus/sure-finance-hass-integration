"""Financial calculation logic (integration copy)."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import (
    Account,
    AccountBalance,
    AccountClassification,
    CashflowItem,
    CashflowSummary,
    FinancialSummary,
    Transaction,
    TransactionType
)

logger = logging.getLogger(__name__)


class FinancialCalculator:
    def __init__(self, currency: str = "USD"):
        self.currency = currency

    def calculate_financial_summary(self, accounts: List[Account], transactions: Optional[List[Transaction]] = None) -> FinancialSummary:
        summary = FinancialSummary(currency=self.currency)
        for account in accounts:
            balance = Decimal(str(account.balance or 0))
            if account.classification == AccountClassification.ASSET:
                summary.total_assets += balance
            elif account.classification == AccountClassification.LIABILITY:
                summary.total_liabilities += abs(balance)
        summary.net_worth = summary.total_assets - summary.total_liabilities
        if transactions:
            for transaction in transactions:
                amount = Decimal(str(transaction.amount))
                if transaction.classification == TransactionType.INCOME.value:
                    summary.total_cashflow += amount
                elif transaction.classification == TransactionType.EXPENSE.value:
                    summary.total_outflow += abs(amount)
        return summary

    def calculate_cashflow_summary(self, transactions: List[Transaction], period_start: datetime, period_end: datetime) -> CashflowSummary:
        summary = CashflowSummary(period_start=period_start, period_end=period_end, currency=self.currency)
        period_transactions = [t for t in transactions if period_start <= t.date <= period_end]
        for transaction in period_transactions:
            amount = Decimal(str(transaction.amount))
            category_name = transaction.category.name if transaction.category else "Uncategorized"
            if transaction.classification == TransactionType.INCOME.value:
                summary.total_income += amount
                summary.income_by_category[category_name] = summary.income_by_category.get(category_name, Decimal("0")) + amount
            elif transaction.classification == TransactionType.EXPENSE.value:
                amount_abs = abs(amount)
                summary.total_expenses += amount_abs
                summary.expenses_by_category[category_name] = summary.expenses_by_category.get(category_name, Decimal("0")) + amount_abs
        summary.net_cashflow = summary.total_income - summary.total_expenses
        return summary

    def get_account_balances(self, accounts: List[Account]) -> List[AccountBalance]:
        balances: List[AccountBalance] = []
        for account in accounts:
            balances.append(AccountBalance(
                account_id=account.id,
                account_name=account.name,
                balance=Decimal(str(account.balance or 0)),
                currency=account.currency or self.currency,
                classification=account.classification or AccountClassification.ASSET,
                last_updated=account.updated_at or datetime.utcnow()
            ))
        return balances

    def get_cashflow_items(self, transactions: List[Transaction], transaction_type: Optional[TransactionType] = None) -> List[CashflowItem]:
        items: List[CashflowItem] = []
        for transaction in transactions:
            if transaction_type:
                if transaction_type == TransactionType.INCOME and transaction.classification != TransactionType.INCOME.value:
                    continue
                elif transaction_type == TransactionType.EXPENSE and transaction.classification != TransactionType.EXPENSE.value:
                    continue
            items.append(CashflowItem(
                date=transaction.date,
                amount=Decimal(str(transaction.amount)),
                currency=transaction.currency,
                category=transaction.category.name if transaction.category else None,
                merchant=transaction.merchant.name if transaction.merchant else None,
                description=transaction.name,
                transaction_id=transaction.id
            ))
        return items

    def calculate_monthly_trends(self, transactions: List[Transaction], months: int = 12) -> Dict[str, CashflowSummary]:
        end_date = datetime.utcnow()
        trends: Dict[str, CashflowSummary] = {}
        for _ in range(months):
            month_end = end_date.replace(day=1) - timedelta(days=1)
            month_start = month_end.replace(day=1)
            month_key = month_start.strftime("%Y-%m")
            trends[month_key] = self.calculate_cashflow_summary(transactions, month_start, month_end)
            end_date = month_start - timedelta(days=1)
        return trends

    def calculate_category_breakdown(self, transactions: List[Transaction], transaction_type: TransactionType) -> Dict[str, Decimal]:
        breakdown: Dict[str, Decimal] = defaultdict(Decimal)
        for transaction in transactions:
            if transaction_type == TransactionType.INCOME and transaction.classification != TransactionType.INCOME.value:
                continue
            elif transaction_type == TransactionType.EXPENSE and transaction.classification != TransactionType.EXPENSE.value:
                continue
            category_name = transaction.category.name if transaction.category else "Uncategorized"
            amount = abs(Decimal(str(transaction.amount)))
            breakdown[category_name] += amount
        return dict(breakdown)

    def calculate_liability_summary(self, accounts: List[Account]) -> Tuple[Decimal, List[AccountBalance]]:
        total_liabilities = Decimal("0")
        liability_accounts: List[AccountBalance] = []
        for account in accounts:
            if account.classification == AccountClassification.LIABILITY:
                balance = abs(Decimal(str(account.balance or 0)))
                total_liabilities += balance
                liability_accounts.append(AccountBalance(
                    account_id=account.id,
                    account_name=account.name,
                    balance=balance,
                    currency=account.currency or self.currency,
                    classification=AccountClassification.LIABILITY,
                    last_updated=account.updated_at or datetime.utcnow()
                ))
        return total_liabilities, liability_accounts

    def calculate_savings_rate(self, income: Decimal, expenses: Decimal) -> Decimal:
        if income <= 0:
            return Decimal("0")
        savings = income - expenses
        rate = (savings / income) * 100
        return max(Decimal("0"), min(Decimal("100"), rate))

    def detect_recurring_transactions(self, transactions: List[Transaction], threshold_days: int = 35) -> Dict[str, List[Transaction]]:
        grouped: Dict[str, List[Transaction]] = defaultdict(list)
        for transaction in transactions:
            if transaction.merchant:
                amount_rounded = round(Decimal(str(transaction.amount)), 0)
                key = f"{transaction.merchant.name}_{amount_rounded}"
                grouped[key].append(transaction)
        recurring: Dict[str, List[Transaction]] = {}
        for key, trans_list in grouped.items():
            if len(trans_list) >= 2:
                trans_list.sort(key=lambda t: t.date)
                is_recurring = True
                for i in range(1, len(trans_list)):
                    days_diff = (trans_list[i].date - trans_list[i-1].date).days
                    if days_diff > threshold_days:
                        is_recurring = False
                        break
                if is_recurring:
                    recurring[key] = trans_list
        return recurring
