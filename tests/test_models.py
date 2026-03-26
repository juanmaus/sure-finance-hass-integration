"""Tests for Sure Finance Pydantic Models."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

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
    Tag,
    Transaction,
    TransactionType,
    _parse_decimal,
)


class TestDecimalParsing:
    """Test suite for decimal parsing utility function."""
    
    def test_parse_decimal_valid_inputs(self, currency_test_cases):
        """Test decimal parsing with valid currency formats."""
        for input_value, expected in currency_test_cases:
            result = _parse_decimal(input_value)
            if expected is None:
                assert result is None
            else:
                assert result == expected
    
    def test_parse_decimal_numeric_types(self):
        """Test decimal parsing with numeric types."""
        # Test int
        assert _parse_decimal(1000) == Decimal("1000")
        assert _parse_decimal(-500) == Decimal("-500")
        assert _parse_decimal(0) == Decimal("0")
        
        # Test float
        assert _parse_decimal(1234.56) == Decimal("1234.56")
        assert _parse_decimal(-789.12) == Decimal("-789.12")
        
        # Test Decimal
        original = Decimal("999.99")
        assert _parse_decimal(original) == original
    
    def test_parse_decimal_string_formats(self):
        """Test decimal parsing with various string formats."""
        test_cases = [
            # Basic formats
            ("1000", Decimal("1000")),
            ("1000.50", Decimal("1000.50")),
            ("-500.25", Decimal("-500.25")),
            
            # With currency symbols
            ("$1,234.56", Decimal("1234.56")),
            ("€2.345,67", Decimal("2345.67")),
            ("£999.99", Decimal("999.99")),
            ("¥1000", Decimal("1000")),
            
            # Parentheses for negative
            ("(500.00)", Decimal("-500.00")),
            ("($1,234.56)", Decimal("-1234.56")),
            
            # European format
            ("1.234,56", Decimal("1234.56")),
            ("12.345.678,90", Decimal("12345678.90")),
            
            # With spaces
            (" 1000.50 ", Decimal("1000.50")),
            ("$ 1,234.56", Decimal("1234.56")),
            
            # Trailing minus
            ("1000-", Decimal("-1000")),
            ("1,234.56-", Decimal("-1234.56")),
        ]
        
        for input_str, expected in test_cases:
            result = _parse_decimal(input_str)
            assert result == expected, f"Failed for input: {input_str}"
    
    def test_parse_decimal_edge_cases(self):
        """Test decimal parsing with edge cases."""
        # Empty and None
        assert _parse_decimal(None) is None
        assert _parse_decimal("") is None
        assert _parse_decimal(" ") is None
        
        # Invalid strings
        assert _parse_decimal("invalid") is None
        assert _parse_decimal("abc123") is None
        assert _parse_decimal("12.34.56") is None
        
        # Multiple currency symbols
        assert _parse_decimal("$$123.45") == Decimal("123.45")
        
        # Only symbols
        assert _parse_decimal("$") is None
        assert _parse_decimal("€") is None
    
    def test_parse_decimal_large_numbers(self):
        """Test decimal parsing with very large numbers."""
        large_number = "999,999,999,999.99"
        result = _parse_decimal(large_number)
        assert result == Decimal("999999999999.99")
        
        # Scientific notation (should fail gracefully)
        assert _parse_decimal("1.23e10") is None
    
    def test_parse_decimal_precision(self):
        """Test decimal parsing maintains precision."""
        test_cases = [
            ("123.456789", Decimal("123.456789")),
            ("0.000001", Decimal("0.000001")),
            ("999999.999999", Decimal("999999.999999")),
        ]
        
        for input_str, expected in test_cases:
            result = _parse_decimal(input_str)
            assert result == expected


class TestBaseEntity:
    """Test suite for BaseEntity model."""
    
    def test_account_creation(self):
        """Test Account model creation and validation."""
        account_id = uuid4()
        now = datetime.utcnow()
        
        account = Account(
            id=account_id,
            name="Test Checking Account",
            account_type="checking",
            balance=Decimal("5000.00"),
            currency="USD",
            classification=AccountClassification.ASSET,
            created_at=now,
            updated_at=now
        )
        
        assert account.id == account_id
        assert account.name == "Test Checking Account"
        assert account.account_type == "checking"
        assert account.balance == Decimal("5000.00")
        assert account.currency == "USD"
        assert account.classification == AccountClassification.ASSET
        assert account.created_at == now
        assert account.updated_at == now
    
    def test_account_balance_parsing(self):
        """Test Account balance field parsing."""
        # Test string balance parsing
        account = Account(
            id=uuid4(),
            name="Test Account",
            account_type="checking",
            balance="$1,234.56",
            currency="USD",
            classification=AccountClassification.ASSET
        )
        
        assert account.balance == Decimal("1234.56")
        
        # Test None balance
        account_none = Account(
            id=uuid4(),
            name="Test Account",
            account_type="checking",
            balance=None,
            currency="USD",
            classification=AccountClassification.ASSET
        )
        
        assert account_none.balance is None
    
    def test_account_optional_fields(self):
        """Test Account with optional fields."""
        # Minimal account
        account = Account(
            id=uuid4(),
            name="Minimal Account",
            account_type="checking"
        )
        
        assert account.balance is None
        assert account.currency is None
        assert account.classification is None
        assert account.created_at is None
        assert account.updated_at is None


class TestCategory:
    """Test suite for Category model."""
    
    def test_category_creation(self):
        """Test Category model creation."""
        category_id = uuid4()
        parent_id = uuid4()
        
        category = Category(
            id=category_id,
            name="Groceries",
            classification=CategoryClassification.EXPENSE,
            color="#FF0000",
            icon="grocery-cart",
            parent_id=parent_id,
            subcategories_count=5
        )
        
        assert category.id == category_id
        assert category.name == "Groceries"
        assert category.classification == CategoryClassification.EXPENSE
        assert category.color == "#FF0000"
        assert category.icon == "grocery-cart"
        assert category.parent_id == parent_id
        assert category.subcategories_count == 5
    
    def test_category_with_parent(self):
        """Test Category with parent relationship."""
        parent_category = Category(
            id=uuid4(),
            name="Food",
            classification=CategoryClassification.EXPENSE,
            color="#00FF00",
            icon="food"
        )
        
        child_category = Category(
            id=uuid4(),
            name="Groceries",
            classification=CategoryClassification.EXPENSE,
            color="#FF0000",
            icon="grocery-cart",
            parent=parent_category
        )
        
        assert child_category.parent == parent_category
        assert child_category.parent.name == "Food"
    
    def test_category_classifications(self):
        """Test Category classification enum."""
        # Test income category
        income_cat = Category(
            id=uuid4(),
            name="Salary",
            classification=CategoryClassification.INCOME,
            color="#00FF00",
            icon="money"
        )
        
        assert income_cat.classification == CategoryClassification.INCOME
        assert income_cat.classification.value == "income"
        
        # Test expense category
        expense_cat = Category(
            id=uuid4(),
            name="Rent",
            classification=CategoryClassification.EXPENSE,
            color="#FF0000",
            icon="home"
        )
        
        assert expense_cat.classification == CategoryClassification.EXPENSE
        assert expense_cat.classification.value == "expense"


class TestTransaction:
    """Test suite for Transaction model."""
    
    def test_transaction_creation(self, sample_accounts, sample_categories, sample_merchants, sample_tags):
        """Test Transaction model creation."""
        transaction_id = uuid4()
        transaction_date = datetime.utcnow()
        
        transaction = Transaction(
            id=transaction_id,
            date=transaction_date,
            amount=Decimal("-150.75"),
            currency="USD",
            name="Grocery Shopping",
            notes="Weekly groceries",
            classification=TransactionType.EXPENSE.value,
            account=sample_accounts[0],
            category=sample_categories[0],
            merchant=sample_merchants[0],
            tags=sample_tags
        )
        
        assert transaction.id == transaction_id
        assert transaction.date == transaction_date
        assert transaction.amount == Decimal("-150.75")
        assert transaction.currency == "USD"
        assert transaction.name == "Grocery Shopping"
        assert transaction.notes == "Weekly groceries"
        assert transaction.classification == TransactionType.EXPENSE.value
        assert transaction.account == sample_accounts[0]
        assert transaction.category == sample_categories[0]
        assert transaction.merchant == sample_merchants[0]
        assert transaction.tags == sample_tags
    
    def test_transaction_amount_parsing(self, sample_accounts):
        """Test Transaction amount field parsing."""
        # Test string amount parsing
        transaction = Transaction(
            id=uuid4(),
            date=datetime.utcnow(),
            amount="-$1,234.56",
            currency="USD",
            name="Test Transaction",
            classification=TransactionType.EXPENSE.value,
            account=sample_accounts[0]
        )
        
        assert transaction.amount == Decimal("-1234.56")
    
    def test_transaction_optional_fields(self, sample_accounts):
        """Test Transaction with optional fields."""
        # Minimal transaction
        transaction = Transaction(
            id=uuid4(),
            date=datetime.utcnow(),
            amount=Decimal("100.00"),
            currency="USD",
            name="Minimal Transaction",
            classification=TransactionType.INCOME.value,
            account=sample_accounts[0]
        )
        
        assert transaction.notes is None
        assert transaction.category is None
        assert transaction.merchant is None
        assert transaction.tags == []
        assert transaction.transfer is None
    
    def test_transaction_with_transfer(self, sample_accounts):
        """Test Transaction with transfer information."""
        from custom_components.sure_finance.models import Transfer
        
        transfer = Transfer(
            id=uuid4(),
            amount=Decimal("500.00"),
            currency="USD",
            other_account=sample_accounts[1]
        )
        
        transaction = Transaction(
            id=uuid4(),
            date=datetime.utcnow(),
            amount=Decimal("-500.00"),
            currency="USD",
            name="Transfer to Savings",
            classification=TransactionType.OUTFLOW.value,
            account=sample_accounts[0],
            transfer=transfer
        )
        
        assert transaction.transfer == transfer
        assert transaction.transfer.other_account == sample_accounts[1]


class TestFinancialSummary:
    """Test suite for FinancialSummary model."""
    
    def test_financial_summary_creation(self):
        """Test FinancialSummary model creation."""
        summary = FinancialSummary(
            total_cashflow=Decimal("5000.00"),
            total_outflow=Decimal("3000.00"),
            total_assets=Decimal("100000.00"),
            total_liabilities=Decimal("25000.00"),
            net_worth=Decimal("75000.00"),
            currency="USD"
        )
        
        assert summary.total_cashflow == Decimal("5000.00")
        assert summary.total_outflow == Decimal("3000.00")
        assert summary.total_assets == Decimal("100000.00")
        assert summary.total_liabilities == Decimal("25000.00")
        assert summary.net_worth == Decimal("75000.00")
        assert summary.currency == "USD"
        assert isinstance(summary.last_updated, datetime)
    
    def test_financial_summary_defaults(self):
        """Test FinancialSummary default values."""
        summary = FinancialSummary()
        
        assert summary.total_cashflow == Decimal("0")
        assert summary.total_outflow == Decimal("0")
        assert summary.total_assets == Decimal("0")
        assert summary.total_liabilities == Decimal("0")
        assert summary.net_worth == Decimal("0")
        assert summary.currency == "USD"
        assert isinstance(summary.last_updated, datetime)
    
    def test_financial_summary_decimal_parsing(self):
        """Test FinancialSummary decimal field parsing."""
        summary = FinancialSummary(
            total_cashflow="$5,000.00",
            total_outflow="($3,000.00)",
            total_assets="100,000.00",
            total_liabilities="25000",
            net_worth="75,000.00"
        )
        
        assert summary.total_cashflow == Decimal("5000.00")
        assert summary.total_outflow == Decimal("-3000.00")
        assert summary.total_assets == Decimal("100000.00")
        assert summary.total_liabilities == Decimal("25000")
        assert summary.net_worth == Decimal("75000.00")


class TestCashflowSummary:
    """Test suite for CashflowSummary model."""
    
    def test_cashflow_summary_creation(self):
        """Test CashflowSummary model creation."""
        period_start = datetime(2023, 6, 1)
        period_end = datetime(2023, 6, 30)
        
        summary = CashflowSummary(
            period_start=period_start,
            period_end=period_end,
            total_income=Decimal("5000.00"),
            total_expenses=Decimal("3000.00"),
            net_cashflow=Decimal("2000.00"),
            income_by_category={
                "Salary": Decimal("4000.00"),
                "Freelance": Decimal("1000.00")
            },
            expenses_by_category={
                "Groceries": Decimal("800.00"),
                "Utilities": Decimal("200.00"),
                "Entertainment": Decimal("2000.00")
            },
            currency="USD"
        )
        
        assert summary.period_start == period_start
        assert summary.period_end == period_end
        assert summary.total_income == Decimal("5000.00")
        assert summary.total_expenses == Decimal("3000.00")
        assert summary.net_cashflow == Decimal("2000.00")
        assert summary.currency == "USD"
        
        # Test category breakdowns
        assert summary.income_by_category["Salary"] == Decimal("4000.00")
        assert summary.income_by_category["Freelance"] == Decimal("1000.00")
        assert summary.expenses_by_category["Groceries"] == Decimal("800.00")
        assert summary.expenses_by_category["Utilities"] == Decimal("200.00")
        assert summary.expenses_by_category["Entertainment"] == Decimal("2000.00")
    
    def test_cashflow_summary_defaults(self):
        """Test CashflowSummary default values."""
        period_start = datetime(2023, 6, 1)
        period_end = datetime(2023, 6, 30)
        
        summary = CashflowSummary(
            period_start=period_start,
            period_end=period_end
        )
        
        assert summary.total_income == Decimal("0")
        assert summary.total_expenses == Decimal("0")
        assert summary.net_cashflow == Decimal("0")
        assert summary.income_by_category == {}
        assert summary.expenses_by_category == {}
        assert summary.currency == "USD"


class TestAccountBalance:
    """Test suite for AccountBalance model."""
    
    def test_account_balance_creation(self):
        """Test AccountBalance model creation."""
        account_id = uuid4()
        last_updated = datetime.utcnow()
        
        balance = AccountBalance(
            account_id=account_id,
            account_name="Test Checking Account",
            balance=Decimal("5000.00"),
            currency="USD",
            classification=AccountClassification.ASSET,
            last_updated=last_updated
        )
        
        assert balance.account_id == account_id
        assert balance.account_name == "Test Checking Account"
        assert balance.balance == Decimal("5000.00")
        assert balance.currency == "USD"
        assert balance.classification == AccountClassification.ASSET
        assert balance.last_updated == last_updated
    
    def test_account_balance_parsing(self):
        """Test AccountBalance balance field parsing."""
        balance = AccountBalance(
            account_id=uuid4(),
            account_name="Test Account",
            balance="$2,500.75",
            currency="USD",
            classification=AccountClassification.ASSET,
            last_updated=datetime.utcnow()
        )
        
        assert balance.balance == Decimal("2500.75")


class TestCashflowItem:
    """Test suite for CashflowItem model."""
    
    def test_cashflow_item_creation(self):
        """Test CashflowItem model creation."""
        transaction_id = uuid4()
        item_date = datetime.utcnow()
        
        item = CashflowItem(
            date=item_date,
            amount=Decimal("-150.00"),
            currency="USD",
            category="Groceries",
            merchant="Walmart",
            description="Weekly grocery shopping",
            transaction_id=transaction_id
        )
        
        assert item.date == item_date
        assert item.amount == Decimal("-150.00")
        assert item.currency == "USD"
        assert item.category == "Groceries"
        assert item.merchant == "Walmart"
        assert item.description == "Weekly grocery shopping"
        assert item.transaction_id == transaction_id
    
    def test_cashflow_item_optional_fields(self):
        """Test CashflowItem with optional fields."""
        item = CashflowItem(
            date=datetime.utcnow(),
            amount=Decimal("100.00"),
            currency="USD",
            description="Test transaction",
            transaction_id=uuid4()
        )
        
        assert item.category is None
        assert item.merchant is None
    
    def test_cashflow_item_amount_parsing(self):
        """Test CashflowItem amount field parsing."""
        item = CashflowItem(
            date=datetime.utcnow(),
            amount="($75.50)",
            currency="USD",
            description="Test expense",
            transaction_id=uuid4()
        )
        
        assert item.amount == Decimal("-75.50")


class TestMerchantAndTag:
    """Test suite for Merchant and Tag models."""
    
    def test_merchant_creation(self):
        """Test Merchant model creation."""
        merchant_id = uuid4()
        
        merchant = Merchant(
            id=merchant_id,
            name="Amazon",
            type="FamilyMerchant"
        )
        
        assert merchant.id == merchant_id
        assert merchant.name == "Amazon"
        assert merchant.type == "FamilyMerchant"
    
    def test_merchant_optional_type(self):
        """Test Merchant with optional type field."""
        merchant = Merchant(
            id=uuid4(),
            name="Local Store"
        )
        
        assert merchant.type is None
    
    def test_tag_creation(self):
        """Test Tag model creation."""
        tag_id = uuid4()
        
        tag = Tag(
            id=tag_id,
            name="Business",
            color="#FF0000"
        )
        
        assert tag.id == tag_id
        assert tag.name == "Business"
        assert tag.color == "#FF0000"


class TestEnumValues:
    """Test suite for enum values and validation."""
    
    def test_transaction_type_enum(self):
        """Test TransactionType enum values."""
        assert TransactionType.INCOME.value == "income"
        assert TransactionType.EXPENSE.value == "expense"
        assert TransactionType.INFLOW.value == "inflow"
        assert TransactionType.OUTFLOW.value == "outflow"
    
    def test_account_classification_enum(self):
        """Test AccountClassification enum values."""
        assert AccountClassification.ASSET.value == "asset"
        assert AccountClassification.LIABILITY.value == "liability"
        assert AccountClassification.INCOME.value == "income"
        assert AccountClassification.EXPENSE.value == "expense"
    
    def test_category_classification_enum(self):
        """Test CategoryClassification enum values."""
        assert CategoryClassification.INCOME.value == "income"
        assert CategoryClassification.EXPENSE.value == "expense"


class TestModelValidation:
    """Test suite for model validation and error handling."""
    
    def test_required_field_validation(self):
        """Test validation of required fields."""
        # Test Account without required fields
        with pytest.raises(ValidationError):
            Account()  # Missing id and name
        
        # Test Transaction without required fields
        with pytest.raises(ValidationError):
            Transaction()  # Missing multiple required fields
        
        # Test Category without required fields
        with pytest.raises(ValidationError):
            Category()  # Missing id, name, classification, color, icon
    
    def test_uuid_field_validation(self):
        """Test UUID field validation."""
        # Valid UUID
        valid_id = uuid4()
        account = Account(
            id=valid_id,
            name="Test Account",
            account_type="checking"
        )
        assert account.id == valid_id
        
        # Invalid UUID string
        with pytest.raises(ValidationError):
            Account(
                id="invalid-uuid",
                name="Test Account",
                account_type="checking"
            )
    
    def test_enum_field_validation(self):
        """Test enum field validation."""
        # Valid enum value
        account = Account(
            id=uuid4(),
            name="Test Account",
            account_type="checking",
            classification=AccountClassification.ASSET
        )
        assert account.classification == AccountClassification.ASSET
        
        # Invalid enum value
        with pytest.raises(ValidationError):
            Account(
                id=uuid4(),
                name="Test Account",
                account_type="checking",
                classification="invalid_classification"
            )
    
    def test_decimal_field_validation(self):
        """Test decimal field validation and parsing."""
        # Valid decimal string
        summary = FinancialSummary(
            total_assets="1000.50"
        )
        assert summary.total_assets == Decimal("1000.50")
        
        # Invalid decimal string (should use original value)
        summary_invalid = FinancialSummary(
            total_assets="invalid_decimal"
        )
        # The validator should handle this gracefully
        assert summary_invalid.total_assets == "invalid_decimal"
    
    def test_datetime_field_validation(self):
        """Test datetime field validation."""
        # Valid datetime
        now = datetime.utcnow()
        account = Account(
            id=uuid4(),
            name="Test Account",
            account_type="checking",
            created_at=now
        )
        assert account.created_at == now
        
        # Invalid datetime
        with pytest.raises(ValidationError):
            Account(
                id=uuid4(),
                name="Test Account",
                account_type="checking",
                created_at="invalid_datetime"
            )


class TestModelSerialization:
    """Test suite for model serialization and deserialization."""
    
    def test_model_dump(self, sample_accounts):
        """Test model serialization to dictionary."""
        account = sample_accounts[0]
        
        dumped = account.model_dump()
        
        assert isinstance(dumped, dict)
        assert dumped["id"] == str(account.id)
        assert dumped["name"] == account.name
        assert dumped["account_type"] == account.account_type
        assert dumped["balance"] == str(account.balance)
        assert dumped["currency"] == account.currency
        assert dumped["classification"] == account.classification.value
    
    def test_model_dump_exclude_none(self):
        """Test model serialization excluding None values."""
        account = Account(
            id=uuid4(),
            name="Test Account",
            account_type="checking"
            # balance, currency, classification are None
        )
        
        dumped = account.model_dump(exclude_none=True)
        
        assert "balance" not in dumped
        assert "currency" not in dumped
        assert "classification" not in dumped
        assert "created_at" not in dumped
        assert "updated_at" not in dumped
    
    def test_model_from_dict(self):
        """Test model creation from dictionary."""
        account_data = {
            "id": str(uuid4()),
            "name": "Test Account",
            "account_type": "checking",
            "balance": "1000.00",
            "currency": "USD",
            "classification": "asset",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        account = Account(**account_data)
        
        assert str(account.id) == account_data["id"]
        assert account.name == account_data["name"]
        assert account.account_type == account_data["account_type"]
        assert account.balance == Decimal("1000.00")
        assert account.currency == account_data["currency"]
        assert account.classification == AccountClassification.ASSET
    
    def test_nested_model_serialization(self, sample_accounts, sample_categories, sample_merchants):
        """Test serialization of models with nested relationships."""
        transaction = Transaction(
            id=uuid4(),
            date=datetime.utcnow(),
            amount=Decimal("-100.00"),
            currency="USD",
            name="Test Transaction",
            classification=TransactionType.EXPENSE.value,
            account=sample_accounts[0],
            category=sample_categories[0],
            merchant=sample_merchants[0]
        )
        
        dumped = transaction.model_dump()
        
        assert isinstance(dumped["account"], dict)
        assert isinstance(dumped["category"], dict)
        assert isinstance(dumped["merchant"], dict)
        
        assert dumped["account"]["name"] == sample_accounts[0].name
        assert dumped["category"]["name"] == sample_categories[0].name
        assert dumped["merchant"]["name"] == sample_merchants[0].name


class TestModelEdgeCases:
    """Test suite for model edge cases and boundary conditions."""
    
    def test_very_large_decimal_values(self):
        """Test models with very large decimal values."""
        large_value = Decimal("999999999999999.99")
        
        summary = FinancialSummary(
            total_assets=large_value,
            total_liabilities=large_value,
            net_worth=Decimal("0")
        )
        
        assert summary.total_assets == large_value
        assert summary.total_liabilities == large_value
    
    def test_very_small_decimal_values(self):
        """Test models with very small decimal values."""
        small_value = Decimal("0.000001")
        
        transaction = Transaction(
            id=uuid4(),
            date=datetime.utcnow(),
            amount=small_value,
            currency="USD",
            name="Micro Transaction",
            classification=TransactionType.INCOME.value,
            account=Account(
                id=uuid4(),
                name="Test Account",
                account_type="checking"
            )
        )
        
        assert transaction.amount == small_value
    
    def test_unicode_string_fields(self):
        """Test models with unicode characters in string fields."""
        unicode_name = "Café München 中文 🏦"
        
        account = Account(
            id=uuid4(),
            name=unicode_name,
            account_type="checking"
        )
        
        assert account.name == unicode_name
        
        # Test serialization preserves unicode
        dumped = account.model_dump()
        assert dumped["name"] == unicode_name
    
    def test_empty_collections(self):
        """Test models with empty collections."""
        transaction = Transaction(
            id=uuid4(),
            date=datetime.utcnow(),
            amount=Decimal("100.00"),
            currency="USD",
            name="Test Transaction",
            classification=TransactionType.INCOME.value,
            account=Account(
                id=uuid4(),
                name="Test Account",
                account_type="checking"
            ),
            tags=[]  # Empty list
        )
        
        assert transaction.tags == []
        
        cashflow = CashflowSummary(
            period_start=datetime(2023, 1, 1),
            period_end=datetime(2023, 1, 31),
            income_by_category={},  # Empty dict
            expenses_by_category={}  # Empty dict
        )
        
        assert cashflow.income_by_category == {}
        assert cashflow.expenses_by_category == {}
