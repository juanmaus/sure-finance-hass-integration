"""Tests for Sure Finance Financial Calculator."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from custom_components.sure_finance.financial_calculator import FinancialCalculator
from custom_components.sure_finance.models import (
    Account,
    AccountBalance,
    AccountClassification,
    CashflowItem,
    CashflowSummary,
    Category,
    CategoryClassification,
    FinancialSummary,
    Merchant,
    Transaction,
    TransactionType,
)


class TestFinancialCalculator:
    """Test suite for FinancialCalculator."""
    
    @pytest.fixture
    def calculator(self):
        """Create a test calculator instance."""
        return FinancialCalculator(currency="USD")
    
    def test_initialization(self):
        """Test calculator initialization with different currencies."""
        # Test default USD
        calc_usd = FinancialCalculator()
        assert calc_usd.currency == "USD"
        
        # Test custom currency
        calc_eur = FinancialCalculator(currency="EUR")
        assert calc_eur.currency == "EUR"
    
    def test_calculate_financial_summary_basic(self, calculator, sample_accounts):
        """Test basic financial summary calculation."""
        # Modify sample accounts for testing
        accounts = [
            Account(
                id=uuid4(),
                name="Checking",
                account_type="checking",
                balance=Decimal("5000.00"),
                currency="USD",
                classification=AccountClassification.ASSET,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Account(
                id=uuid4(),
                name="Savings",
                account_type="savings",
                balance=Decimal("15000.00"),
                currency="USD",
                classification=AccountClassification.ASSET,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Account(
                id=uuid4(),
                name="Credit Card",
                account_type="credit",
                balance=Decimal("-2500.00"),
                currency="USD",
                classification=AccountClassification.LIABILITY,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        summary = calculator.calculate_financial_summary(accounts)
        
        # Verify calculations
        assert summary.total_assets == Decimal("20000.00")
        assert summary.total_liabilities == Decimal("2500.00")  # Absolute value
        assert summary.net_worth == Decimal("17500.00")
        assert summary.currency == "USD"
        assert isinstance(summary.last_updated, datetime)
    
    def test_calculate_financial_summary_with_transactions(self, calculator, sample_accounts, sample_transactions):
        """Test financial summary calculation including transaction data."""
        # Create transactions with known amounts
        transactions = [
            Transaction(
                id=uuid4(),
                date=datetime.utcnow() - timedelta(days=1),
                amount=Decimal("3000.00"),  # Income
                currency="USD",
                name="Salary",
                classification=TransactionType.INCOME.value,
                account=sample_accounts[0],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Transaction(
                id=uuid4(),
                date=datetime.utcnow() - timedelta(days=2),
                amount=Decimal("-150.00"),  # Expense
                currency="USD",
                name="Groceries",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Transaction(
                id=uuid4(),
                date=datetime.utcnow() - timedelta(days=3),
                amount=Decimal("-75.00"),  # Expense
                currency="USD",
                name="Gas",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        summary = calculator.calculate_financial_summary(sample_accounts, transactions)
        
        # Verify transaction calculations
        assert summary.total_cashflow == Decimal("3000.00")
        assert summary.total_outflow == Decimal("225.00")  # 150 + 75
    
    def test_calculate_financial_summary_edge_cases(self, calculator):
        """Test financial summary calculation with edge cases."""
        # Test with empty accounts
        summary = calculator.calculate_financial_summary([])
        assert summary.total_assets == Decimal("0")
        assert summary.total_liabilities == Decimal("0")
        assert summary.net_worth == Decimal("0")
        
        # Test with None balances
        accounts_with_none = [
            Account(
                id=uuid4(),
                name="Test Account",
                account_type="checking",
                balance=None,
                currency="USD",
                classification=AccountClassification.ASSET,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]
        
        summary = calculator.calculate_financial_summary(accounts_with_none)
        assert summary.total_assets == Decimal("0")
    
    def test_calculate_cashflow_summary(self, calculator, sample_accounts, sample_categories):
        """Test cashflow summary calculation for a specific period."""
        period_start = datetime(2023, 6, 1)
        period_end = datetime(2023, 6, 30)
        
        # Create transactions within and outside the period
        transactions = [
            # Within period - Income
            Transaction(
                id=uuid4(),
                date=datetime(2023, 6, 15),
                amount=Decimal("3000.00"),
                currency="USD",
                name="Salary",
                classification=TransactionType.INCOME.value,
                account=sample_accounts[0],
                category=sample_categories[1],  # Salary category
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            # Within period - Expense
            Transaction(
                id=uuid4(),
                date=datetime(2023, 6, 20),
                amount=Decimal("-200.00"),
                currency="USD",
                name="Groceries",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                category=sample_categories[0],  # Groceries category
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            # Outside period - should be ignored
            Transaction(
                id=uuid4(),
                date=datetime(2023, 5, 31),
                amount=Decimal("-100.00"),
                currency="USD",
                name="Previous Month",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        summary = calculator.calculate_cashflow_summary(transactions, period_start, period_end)
        
        # Verify period filtering and calculations
        assert summary.period_start == period_start
        assert summary.period_end == period_end
        assert summary.total_income == Decimal("3000.00")
        assert summary.total_expenses == Decimal("200.00")
        assert summary.net_cashflow == Decimal("2800.00")
        assert summary.currency == "USD"
        
        # Verify category breakdowns
        assert "Salary" in summary.income_by_category
        assert summary.income_by_category["Salary"] == Decimal("3000.00")
        assert "Groceries" in summary.expenses_by_category
        assert summary.expenses_by_category["Groceries"] == Decimal("200.00")
    
    def test_calculate_cashflow_summary_no_category(self, calculator, sample_accounts):
        """Test cashflow summary with transactions that have no category."""
        period_start = datetime(2023, 6, 1)
        period_end = datetime(2023, 6, 30)
        
        transactions = [
            Transaction(
                id=uuid4(),
                date=datetime(2023, 6, 15),
                amount=Decimal("-100.00"),
                currency="USD",
                name="Uncategorized Expense",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                category=None,  # No category
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        summary = calculator.calculate_cashflow_summary(transactions, period_start, period_end)
        
        # Should categorize as "Uncategorized"
        assert "Uncategorized" in summary.expenses_by_category
        assert summary.expenses_by_category["Uncategorized"] == Decimal("100.00")
    
    def test_get_account_balances(self, calculator, sample_accounts):
        """Test account balance extraction."""
        balances = calculator.get_account_balances(sample_accounts)
        
        assert len(balances) == len(sample_accounts)
        
        for i, balance in enumerate(balances):
            assert isinstance(balance, AccountBalance)
            assert balance.account_id == sample_accounts[i].id
            assert balance.account_name == sample_accounts[i].name
            assert balance.balance == Decimal(str(sample_accounts[i].balance or 0))
            assert balance.currency == sample_accounts[i].currency or "USD"
            assert balance.classification == sample_accounts[i].classification or AccountClassification.ASSET
            assert isinstance(balance.last_updated, datetime)
    
    def test_get_cashflow_items(self, calculator, sample_transactions):
        """Test cashflow item extraction from transactions."""
        # Test all transactions
        items = calculator.get_cashflow_items(sample_transactions)
        
        assert len(items) == len(sample_transactions)
        
        for i, item in enumerate(items):
            assert isinstance(item, CashflowItem)
            assert item.transaction_id == sample_transactions[i].id
            assert item.amount == Decimal(str(sample_transactions[i].amount))
            assert item.description == sample_transactions[i].name
        
        # Test filtered by transaction type
        income_items = calculator.get_cashflow_items(sample_transactions, TransactionType.INCOME)
        expense_items = calculator.get_cashflow_items(sample_transactions, TransactionType.EXPENSE)
        
        # Verify filtering
        income_count = sum(1 for tx in sample_transactions if tx.classification == TransactionType.INCOME.value)
        expense_count = sum(1 for tx in sample_transactions if tx.classification == TransactionType.EXPENSE.value)
        
        assert len(income_items) == income_count
        assert len(expense_items) == expense_count
    
    def test_calculate_monthly_trends(self, calculator, sample_accounts):
        """Test monthly trend calculation."""
        # Create transactions spanning multiple months
        transactions = []
        base_date = datetime.utcnow().replace(day=15)  # Middle of month
        
        for i in range(6):  # 6 months of data
            month_date = base_date - timedelta(days=30 * i)
            
            # Income transaction
            transactions.append(
                Transaction(
                    id=uuid4(),
                    date=month_date,
                    amount=Decimal("3000.00"),
                    currency="USD",
                    name=f"Salary {i}",
                    classification=TransactionType.INCOME.value,
                    account=sample_accounts[0],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )
            
            # Expense transaction
            transactions.append(
                Transaction(
                    id=uuid4(),
                    date=month_date,
                    amount=Decimal("-500.00"),
                    currency="USD",
                    name=f"Expense {i}",
                    classification=TransactionType.EXPENSE.value,
                    account=sample_accounts[0],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )
        
        trends = calculator.calculate_monthly_trends(transactions, months=3)
        
        # Should return 3 months of data
        assert len(trends) == 3
        
        # Each trend should be a CashflowSummary
        for month_key, summary in trends.items():
            assert isinstance(summary, CashflowSummary)
            assert isinstance(month_key, str)
            # Month key should be in YYYY-MM format
            assert len(month_key) == 7
            assert month_key[4] == "-"
    
    def test_calculate_category_breakdown(self, calculator, sample_accounts, sample_categories):
        """Test category breakdown calculation."""
        transactions = [
            # Groceries expenses
            Transaction(
                id=uuid4(),
                date=datetime.utcnow(),
                amount=Decimal("-100.00"),
                currency="USD",
                name="Grocery 1",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                category=sample_categories[0],  # Groceries
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Transaction(
                id=uuid4(),
                date=datetime.utcnow(),
                amount=Decimal("-150.00"),
                currency="USD",
                name="Grocery 2",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                category=sample_categories[0],  # Groceries
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            # Utilities expense
            Transaction(
                id=uuid4(),
                date=datetime.utcnow(),
                amount=Decimal("-75.00"),
                currency="USD",
                name="Electric Bill",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                category=sample_categories[2],  # Utilities
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            # Income (should be ignored for expense breakdown)
            Transaction(
                id=uuid4(),
                date=datetime.utcnow(),
                amount=Decimal("3000.00"),
                currency="USD",
                name="Salary",
                classification=TransactionType.INCOME.value,
                account=sample_accounts[0],
                category=sample_categories[1],  # Salary
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        # Test expense breakdown
        expense_breakdown = calculator.calculate_category_breakdown(transactions, TransactionType.EXPENSE)
        
        assert "Groceries" in expense_breakdown
        assert expense_breakdown["Groceries"] == Decimal("250.00")  # 100 + 150
        assert "Utilities" in expense_breakdown
        assert expense_breakdown["Utilities"] == Decimal("75.00")
        assert "Salary" not in expense_breakdown  # Income category should not appear
        
        # Test income breakdown
        income_breakdown = calculator.calculate_category_breakdown(transactions, TransactionType.INCOME)
        
        assert "Salary" in income_breakdown
        assert income_breakdown["Salary"] == Decimal("3000.00")
        assert "Groceries" not in income_breakdown  # Expense category should not appear
    
    def test_calculate_liability_summary(self, calculator):
        """Test liability summary calculation."""
        accounts = [
            # Asset accounts (should be ignored)
            Account(
                id=uuid4(),
                name="Checking",
                account_type="checking",
                balance=Decimal("5000.00"),
                currency="USD",
                classification=AccountClassification.ASSET,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            # Liability accounts
            Account(
                id=uuid4(),
                name="Credit Card",
                account_type="credit",
                balance=Decimal("-2500.00"),
                currency="USD",
                classification=AccountClassification.LIABILITY,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Account(
                id=uuid4(),
                name="Mortgage",
                account_type="loan",
                balance=Decimal("-150000.00"),
                currency="USD",
                classification=AccountClassification.LIABILITY,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        total_liabilities, liability_accounts = calculator.calculate_liability_summary(accounts)
        
        # Verify total (absolute values)
        assert total_liabilities == Decimal("152500.00")
        
        # Verify liability accounts list
        assert len(liability_accounts) == 2
        
        for liability in liability_accounts:
            assert isinstance(liability, AccountBalance)
            assert liability.classification == AccountClassification.LIABILITY
            assert liability.balance > 0  # Should be positive (absolute value)
    
    def test_calculate_savings_rate(self, calculator):
        """Test savings rate calculation."""
        # Test normal case
        income = Decimal("5000.00")
        expenses = Decimal("3000.00")
        rate = calculator.calculate_savings_rate(income, expenses)
        
        expected_rate = Decimal("40.00")  # (5000 - 3000) / 5000 * 100 = 40%
        assert rate == expected_rate
        
        # Test zero income
        rate = calculator.calculate_savings_rate(Decimal("0"), Decimal("100"))
        assert rate == Decimal("0")
        
        # Test negative income
        rate = calculator.calculate_savings_rate(Decimal("-100"), Decimal("50"))
        assert rate == Decimal("0")
        
        # Test expenses greater than income (negative savings)
        rate = calculator.calculate_savings_rate(Decimal("1000"), Decimal("1500"))
        assert rate == Decimal("0")  # Should be clamped to 0
        
        # Test 100% savings rate
        rate = calculator.calculate_savings_rate(Decimal("1000"), Decimal("0"))
        assert rate == Decimal("100.00")
        
        # Test rate clamping above 100%
        rate = calculator.calculate_savings_rate(Decimal("1000"), Decimal("-500"))  # Negative expenses
        assert rate == Decimal("100.00")  # Should be clamped to 100
    
    def test_detect_recurring_transactions(self, calculator, sample_accounts, sample_merchants):
        """Test recurring transaction detection."""
        base_date = datetime(2023, 6, 1)
        
        # Create recurring transactions (same merchant, similar amount, regular intervals)
        recurring_transactions = [
            Transaction(
                id=uuid4(),
                date=base_date,
                amount=Decimal("-100.00"),
                currency="USD",
                name="Netflix Subscription",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                merchant=sample_merchants[0],  # Same merchant
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Transaction(
                id=uuid4(),
                date=base_date + timedelta(days=30),
                amount=Decimal("-100.00"),  # Same amount
                currency="USD",
                name="Netflix Subscription",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                merchant=sample_merchants[0],  # Same merchant
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Transaction(
                id=uuid4(),
                date=base_date + timedelta(days=60),
                amount=Decimal("-100.00"),  # Same amount
                currency="USD",
                name="Netflix Subscription",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                merchant=sample_merchants[0],  # Same merchant
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        # Create non-recurring transactions
        non_recurring_transactions = [
            Transaction(
                id=uuid4(),
                date=base_date,
                amount=Decimal("-50.00"),
                currency="USD",
                name="One-time Purchase",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                merchant=sample_merchants[1],  # Different merchant
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        all_transactions = recurring_transactions + non_recurring_transactions
        
        recurring = calculator.detect_recurring_transactions(all_transactions, threshold_days=35)
        
        # Should detect the recurring Netflix transactions
        assert len(recurring) == 1
        
        # Get the recurring group
        recurring_group = list(recurring.values())[0]
        assert len(recurring_group) == 3
        
        # Verify all transactions in the group are the Netflix ones
        for tx in recurring_group:
            assert tx.merchant.name == sample_merchants[0].name
            assert tx.amount == Decimal("-100.00")
    
    def test_detect_recurring_transactions_threshold(self, calculator, sample_accounts, sample_merchants):
        """Test recurring transaction detection with different thresholds."""
        base_date = datetime(2023, 6, 1)
        
        # Create transactions with 40-day intervals
        transactions = [
            Transaction(
                id=uuid4(),
                date=base_date,
                amount=Decimal("-100.00"),
                currency="USD",
                name="Subscription",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                merchant=sample_merchants[0],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Transaction(
                id=uuid4(),
                date=base_date + timedelta(days=40),
                amount=Decimal("-100.00"),
                currency="USD",
                name="Subscription",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                merchant=sample_merchants[0],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        # With threshold of 35 days, should not be detected as recurring
        recurring_strict = calculator.detect_recurring_transactions(transactions, threshold_days=35)
        assert len(recurring_strict) == 0
        
        # With threshold of 45 days, should be detected as recurring
        recurring_loose = calculator.detect_recurring_transactions(transactions, threshold_days=45)
        assert len(recurring_loose) == 1
    
    def test_detect_recurring_transactions_no_merchant(self, calculator, sample_accounts):
        """Test recurring transaction detection with transactions that have no merchant."""
        base_date = datetime(2023, 6, 1)
        
        transactions = [
            Transaction(
                id=uuid4(),
                date=base_date,
                amount=Decimal("-100.00"),
                currency="USD",
                name="No Merchant Transaction",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                merchant=None,  # No merchant
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Transaction(
                id=uuid4(),
                date=base_date + timedelta(days=30),
                amount=Decimal("-100.00"),
                currency="USD",
                name="No Merchant Transaction",
                classification=TransactionType.EXPENSE.value,
                account=sample_accounts[0],
                merchant=None,  # No merchant
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        # Should not detect recurring transactions without merchant info
        recurring = calculator.detect_recurring_transactions(transactions)
        assert len(recurring) == 0


class TestFinancialCalculatorEdgeCases:
    """Test suite for edge cases and boundary conditions."""
    
    def test_empty_data_handling(self):
        """Test calculator behavior with empty data sets."""
        calculator = FinancialCalculator()
        
        # Empty accounts
        summary = calculator.calculate_financial_summary([])
        assert summary.total_assets == Decimal("0")
        assert summary.total_liabilities == Decimal("0")
        assert summary.net_worth == Decimal("0")
        
        # Empty transactions
        period_start = datetime(2023, 1, 1)
        period_end = datetime(2023, 1, 31)
        cashflow = calculator.calculate_cashflow_summary([], period_start, period_end)
        assert cashflow.total_income == Decimal("0")
        assert cashflow.total_expenses == Decimal("0")
        assert cashflow.net_cashflow == Decimal("0")
        
        # Empty category breakdown
        breakdown = calculator.calculate_category_breakdown([], TransactionType.EXPENSE)
        assert len(breakdown) == 0
    
    def test_large_numbers(self):
        """Test calculator with very large financial numbers."""
        calculator = FinancialCalculator()
        
        # Create account with very large balance
        large_account = Account(
            id=uuid4(),
            name="Large Account",
            account_type="investment",
            balance=Decimal("999999999999.99"),  # Nearly 1 trillion
            currency="USD",
            classification=AccountClassification.ASSET,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        summary = calculator.calculate_financial_summary([large_account])
        assert summary.total_assets == Decimal("999999999999.99")
        assert summary.net_worth == Decimal("999999999999.99")
    
    def test_precision_handling(self):
        """Test decimal precision in calculations."""
        calculator = FinancialCalculator()
        
        # Create accounts with precise decimal values
        accounts = [
            Account(
                id=uuid4(),
                name="Precise Account 1",
                account_type="checking",
                balance=Decimal("1234.567"),
                currency="USD",
                classification=AccountClassification.ASSET,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Account(
                id=uuid4(),
                name="Precise Account 2",
                account_type="savings",
                balance=Decimal("9876.543"),
                currency="USD",
                classification=AccountClassification.ASSET,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        summary = calculator.calculate_financial_summary(accounts)
        assert summary.total_assets == Decimal("11111.110")
    
    def test_currency_consistency(self):
        """Test that currency is properly propagated through calculations."""
        calculator = FinancialCalculator(currency="EUR")
        
        account = Account(
            id=uuid4(),
            name="EUR Account",
            account_type="checking",
            balance=Decimal("1000.00"),
            currency="EUR",
            classification=AccountClassification.ASSET,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        summary = calculator.calculate_financial_summary([account])
        assert summary.currency == "EUR"
        
        # Test cashflow summary
        period_start = datetime(2023, 1, 1)
        period_end = datetime(2023, 1, 31)
        cashflow = calculator.calculate_cashflow_summary([], period_start, period_end)
        assert cashflow.currency == "EUR"
    
    def test_mixed_classifications(self):
        """Test handling of accounts with mixed or unusual classifications."""
        calculator = FinancialCalculator()
        
        accounts = [
            Account(
                id=uuid4(),
                name="Asset Account",
                account_type="checking",
                balance=Decimal("1000.00"),
                currency="USD",
                classification=AccountClassification.ASSET,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Account(
                id=uuid4(),
                name="Liability Account",
                account_type="credit",
                balance=Decimal("-500.00"),
                currency="USD",
                classification=AccountClassification.LIABILITY,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Account(
                id=uuid4(),
                name="Income Account",
                account_type="income",
                balance=Decimal("2000.00"),
                currency="USD",
                classification=AccountClassification.INCOME,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            Account(
                id=uuid4(),
                name="Expense Account",
                account_type="expense",
                balance=Decimal("-300.00"),
                currency="USD",
                classification=AccountClassification.EXPENSE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        
        summary = calculator.calculate_financial_summary(accounts)
        
        # Only ASSET and LIABILITY should be included in net worth calculation
        assert summary.total_assets == Decimal("1000.00")
        assert summary.total_liabilities == Decimal("500.00")  # Absolute value
        assert summary.net_worth == Decimal("500.00")
