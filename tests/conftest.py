"""Pytest configuration and shared fixtures."""

import asyncio
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from aiohttp import ClientSession, ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from custom_components.sure_finance.api_client import SureFinanceClient
from custom_components.sure_finance.cache_manager import CacheManager
from custom_components.sure_finance.data_manager import DataManager
from custom_components.sure_finance.financial_calculator import FinancialCalculator
from custom_components.sure_finance.models import (
    Account,
    AccountClassification,
    Category,
    CategoryClassification,
    Merchant,
    Tag,
    Transaction,
    TransactionType,
)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config = MagicMock()
    hass.config.path.return_value = "/tmp/test_cache"
    hass.services = MagicMock()
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Mock config entry."""
    return ConfigEntry(
        version=1,
        domain="sure_finance",
        title="Sure Finance",
        data={
            "api_key": "test_api_key",
            "host": "https://app.sure.am",
            "update_interval": 300,
            "currency": "USD",
            "cache_duration": 3600,
            "enable_cashflow_sensor": True,
            "enable_outflow_sensor": True,
            "enable_liability_sensor": True,
            "enable_account_sensors": True,
        },
        source="user",
        entry_id="test_entry_id",
    )


@pytest.fixture
def sample_accounts():
    """Sample account data for testing."""
    return [
        Account(
            id=uuid4(),
            name="Checking Account",
            account_type="checking",
            balance=Decimal("5000.00"),
            currency="USD",
            classification=AccountClassification.ASSET,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Account(
            id=uuid4(),
            name="Savings Account",
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


@pytest.fixture
def sample_categories():
    """Sample category data for testing."""
    return [
        Category(
            id=uuid4(),
            name="Groceries",
            classification=CategoryClassification.EXPENSE,
            color="#FF0000",
            icon="grocery",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Category(
            id=uuid4(),
            name="Salary",
            classification=CategoryClassification.INCOME,
            color="#00FF00",
            icon="salary",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Category(
            id=uuid4(),
            name="Utilities",
            classification=CategoryClassification.EXPENSE,
            color="#0000FF",
            icon="utilities",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def sample_merchants():
    """Sample merchant data for testing."""
    return [
        Merchant(
            id=uuid4(),
            name="Walmart",
            type="FamilyMerchant",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Merchant(
            id=uuid4(),
            name="Amazon",
            type="FamilyMerchant",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def sample_tags():
    """Sample tag data for testing."""
    return [
        Tag(
            id=uuid4(),
            name="Business",
            color="#FF0000",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Tag(
            id=uuid4(),
            name="Personal",
            color="#00FF00",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def sample_transactions(sample_accounts, sample_categories, sample_merchants, sample_tags):
    """Sample transaction data for testing."""
    return [
        Transaction(
            id=uuid4(),
            date=datetime.utcnow() - timedelta(days=1),
            amount=Decimal("-50.00"),
            currency="USD",
            name="Grocery Shopping",
            classification=TransactionType.EXPENSE.value,
            account=sample_accounts[0],
            category=sample_categories[0],
            merchant=sample_merchants[0],
            tags=[sample_tags[1]],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Transaction(
            id=uuid4(),
            date=datetime.utcnow() - timedelta(days=2),
            amount=Decimal("3000.00"),
            currency="USD",
            name="Monthly Salary",
            classification=TransactionType.INCOME.value,
            account=sample_accounts[0],
            category=sample_categories[1],
            tags=[sample_tags[0]],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        Transaction(
            id=uuid4(),
            date=datetime.utcnow() - timedelta(days=3),
            amount=Decimal("-150.00"),
            currency="USD",
            name="Electric Bill",
            classification=TransactionType.EXPENSE.value,
            account=sample_accounts[0],
            category=sample_categories[2],
            tags=[sample_tags[1]],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def mock_api_response_accounts():
    """Mock API response for accounts."""
    return {
        "accounts": [
            {
                "id": str(uuid4()),
                "name": "Checking Account",
                "account_type": "checking",
                "balance": "5000.00",
                "currency": "USD",
                "classification": "asset",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            {
                "id": str(uuid4()),
                "name": "Credit Card",
                "account_type": "credit",
                "balance": "-2500.00",
                "currency": "USD",
                "classification": "liability",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        ],
        "pagination": {
            "page": 1,
            "per_page": 25,
            "total_count": 2,
            "total_pages": 1,
        },
    }


@pytest.fixture
def mock_api_response_transactions():
    """Mock API response for transactions."""
    return {
        "transactions": [
            {
                "id": str(uuid4()),
                "date": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "amount": "-50.00",
                "currency": "USD",
                "name": "Grocery Shopping",
                "classification": "expense",
                "account": {
                    "id": str(uuid4()),
                    "name": "Checking Account",
                    "account_type": "checking",
                    "balance": "5000.00",
                    "currency": "USD",
                    "classification": "asset",
                },
                "category": {
                    "id": str(uuid4()),
                    "name": "Groceries",
                    "classification": "expense",
                    "color": "#FF0000",
                    "icon": "grocery",
                },
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 25,
            "total_count": 1,
            "total_pages": 1,
        },
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.scan_iter.return_value = []
    redis_mock.close.return_value = None
    return redis_mock


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def mock_cache_manager(temp_cache_dir, mock_redis):
    """Mock cache manager with temporary directory."""
    cache_manager = CacheManager(
        cache_dir=temp_cache_dir,
        default_ttl=3600
    )
    cache_manager._redis = mock_redis
    return cache_manager


@pytest.fixture
def mock_api_client():
    """Mock API client."""
    client = MagicMock(spec=SureFinanceClient)
    client.connect = AsyncMock()
    client.close = AsyncMock()
    client.get_accounts = AsyncMock()
    client.get_transactions = AsyncMock()
    client.get_categories = AsyncMock()
    client.get_merchants = AsyncMock()
    client.get_tags = AsyncMock()
    client.get_all_pages = AsyncMock()
    return client


@pytest.fixture
def mock_financial_calculator():
    """Mock financial calculator."""
    return FinancialCalculator(currency="USD")


@pytest.fixture
def mock_data_manager(mock_api_client, mock_cache_manager, mock_financial_calculator):
    """Mock data manager."""
    return DataManager(
        api_client=mock_api_client,
        cache_manager=mock_cache_manager,
        calculator=mock_financial_calculator,
        update_interval=300
    )


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session."""
    session = AsyncMock(spec=ClientSession)
    response = AsyncMock()
    response.status = 200
    response.json.return_value = {"test": "data"}
    response.content_length = 100
    session.request.return_value.__aenter__.return_value = response
    return session


@pytest.fixture
def api_error_responses():
    """Common API error response scenarios."""
    return {
        "auth_error": {
            "status": 401,
            "data": {"error": "Invalid API key"}
        },
        "rate_limit": {
            "status": 429,
            "data": {"error": "Rate limit exceeded", "retry_after": 60}
        },
        "server_error": {
            "status": 500,
            "data": {"error": "Internal server error"}
        },
        "not_found": {
            "status": 404,
            "data": {"error": "Resource not found"}
        }
    }


@pytest.fixture
def currency_test_cases():
    """Test cases for currency parsing."""
    return [
        ("$1,234.56", Decimal("1234.56")),
        ("1.234,56€", Decimal("1234.56")),
        ("(500.00)", Decimal("-500.00")),
        ("$-1,000.00", Decimal("-1000.00")),
        ("1000", Decimal("1000")),
        ("", None),
        (None, None),
        ("invalid", None),
    ]


@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing."""
    accounts = []
    transactions = []
    
    # Generate 100 accounts
    for i in range(100):
        account = Account(
            id=uuid4(),
            name=f"Account {i}",
            account_type="checking",
            balance=Decimal(f"{1000 + i * 100}.00"),
            currency="USD",
            classification=AccountClassification.ASSET,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        accounts.append(account)
    
    # Generate 1000 transactions
    for i in range(1000):
        transaction = Transaction(
            id=uuid4(),
            date=datetime.utcnow() - timedelta(days=i % 30),
            amount=Decimal(f"{-50 - (i % 100)}.00"),
            currency="USD",
            name=f"Transaction {i}",
            classification=TransactionType.EXPENSE.value,
            account=accounts[i % len(accounts)],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        transactions.append(transaction)
    
    return {"accounts": accounts, "transactions": transactions}


# Test utilities
class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, status: int, data: Dict[str, Any], content_length: int = 100):
        self.status = status
        self.data = data
        self.content_length = content_length
    
    async def json(self):
        return self.data
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def create_mock_response(status: int, data: Dict[str, Any]) -> MockResponse:
    """Create a mock HTTP response."""
    return MockResponse(status, data)


def assert_decimal_equal(actual: Decimal, expected: Decimal, places: int = 2):
    """Assert that two Decimal values are equal within specified decimal places."""
    assert abs(actual - expected) < Decimal(f"0.{'0' * (places - 1)}1")


def create_test_cache_file(cache_dir: Path, key: str, data: Any, expires_at: datetime):
    """Create a test cache file."""
    import pickle
    cache_file = cache_dir / f"{key}.cache"
    with open(cache_file, "wb") as f:
        pickle.dump({"value": data, "expires_at": expires_at}, f)
    return cache_file
