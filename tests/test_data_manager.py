"""Tests for Sure Finance Data Manager."""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from custom_components.sure_finance.api_client import APIError, AuthenticationError
from custom_components.sure_finance.data_manager import DataManager
from custom_components.sure_finance.models import (
    Account,
    AccountClassification,
    Category,
    CategoryClassification,
    FinancialSummary,
    Merchant,
    Tag,
    Transaction,
    TransactionType,
)


class TestDataManager:
    """Test suite for DataManager."""
    
    @pytest.fixture
    def data_manager(self, mock_api_client, mock_cache_manager, mock_financial_calculator):
        """Create a test data manager instance."""
        return DataManager(
            api_client=mock_api_client,
            cache_manager=mock_cache_manager,
            calculator=mock_financial_calculator,
            update_interval=300
        )
    
    def test_initialization(self, data_manager):
        """Test data manager initialization."""
        assert data_manager.update_interval == 300
        assert data_manager._last_updates == {}
        assert data_manager.api_client is not None
        assert data_manager.cache is not None
        assert data_manager.calculator is not None
    
    @pytest.mark.asyncio
    async def test_get_accounts_from_cache(self, data_manager, sample_accounts):
        """Test retrieving accounts from cache when available."""
        # Setup cache to return data
        cached_data = [acc.model_dump() for acc in sample_accounts]
        data_manager.cache.get.return_value = cached_data
        
        result = await data_manager.get_accounts()
        
        # Verify cache was checked
        data_manager.cache.get.assert_called_once()
        
        # Verify API was not called
        data_manager.api_client.get_all_pages.assert_not_called()
        
        # Verify result
        assert len(result) == len(sample_accounts)
        assert all(isinstance(acc, Account) for acc in result)
    
    @pytest.mark.asyncio
    async def test_get_accounts_from_api(self, data_manager, sample_accounts):
        """Test retrieving accounts from API when cache is empty."""
        # Setup cache to return None (cache miss)
        data_manager.cache.get.return_value = None
        
        # Setup API to return data
        api_data = [acc.model_dump() for acc in sample_accounts]
        data_manager.api_client.get_all_pages.return_value = api_data
        
        result = await data_manager.get_accounts()
        
        # Verify API was called
        data_manager.api_client.get_all_pages.assert_called_once()
        
        # Verify cache was updated
        data_manager.cache.set.assert_called_once()
        
        # Verify last update was recorded
        assert "accounts" in data_manager._last_updates
        
        # Verify result
        assert len(result) == len(sample_accounts)
        assert all(isinstance(acc, Account) for acc in result)
    
    @pytest.mark.asyncio
    async def test_get_accounts_force_refresh(self, data_manager, sample_accounts):
        """Test force refreshing accounts bypasses cache."""
        # Setup cache to return data
        cached_data = [sample_accounts[0].model_dump()]
        data_manager.cache.get.return_value = cached_data
        
        # Setup API to return different data
        api_data = [acc.model_dump() for acc in sample_accounts]
        data_manager.api_client.get_all_pages.return_value = api_data
        
        result = await data_manager.get_accounts(force_refresh=True)
        
        # Verify API was called despite cache having data
        data_manager.api_client.get_all_pages.assert_called_once()
        
        # Verify result comes from API, not cache
        assert len(result) == len(sample_accounts)
    
    @pytest.mark.asyncio
    async def test_get_accounts_api_error_fallback_to_cache(self, data_manager, sample_accounts):
        """Test fallback to cache when API fails."""
        # Setup cache to return data
        cached_data = [acc.model_dump() for acc in sample_accounts]
        data_manager.cache.get.side_effect = [None, cached_data]  # First call (check), second call (fallback)
        
        # Setup API to raise error
        data_manager.api_client.get_all_pages.side_effect = APIError("API Error")
        
        result = await data_manager.get_accounts()
        
        # Verify API was attempted
        data_manager.api_client.get_all_pages.assert_called_once()
        
        # Verify cache was checked twice (initial check + fallback)
        assert data_manager.cache.get.call_count == 2
        
        # Verify result comes from cache
        assert len(result) == len(sample_accounts)
    
    @pytest.mark.asyncio
    async def test_get_accounts_api_error_no_cache(self, data_manager):
        """Test API error with no cache data available."""
        # Setup cache to return None
        data_manager.cache.get.return_value = None
        
        # Setup API to raise error
        data_manager.api_client.get_all_pages.side_effect = APIError("API Error")
        
        # Should re-raise the API error
        with pytest.raises(APIError):
            await data_manager.get_accounts()
    
    @pytest.mark.asyncio
    async def test_get_transactions_with_date_range(self, data_manager, sample_transactions):
        """Test retrieving transactions with date range filtering."""
        # Setup cache to return None
        data_manager.cache.get.return_value = None
        
        # Setup API to return data
        api_data = [tx.model_dump() for tx in sample_transactions]
        data_manager.api_client.get_all_pages.return_value = api_data
        
        result = await data_manager.get_transactions(days=30)
        
        # Verify API was called with correct parameters
        call_args = data_manager.api_client.get_all_pages.call_args
        assert "date_range" in call_args.kwargs
        date_range = call_args.kwargs["date_range"]
        
        # Verify date range is approximately 30 days
        days_diff = (date_range.end_date - date_range.start_date).days
        assert 29 <= days_diff <= 30  # Allow for slight timing differences
        
        # Verify result
        assert len(result) == len(sample_transactions)
        assert all(isinstance(tx, Transaction) for tx in result)
    
    @pytest.mark.asyncio
    async def test_get_transactions_with_account_filter(self, data_manager, sample_transactions):
        """Test retrieving transactions filtered by account."""
        account_id = str(uuid4())
        
        # Setup cache to return None
        data_manager.cache.get.return_value = None
        
        # Setup API to return data
        api_data = [tx.model_dump() for tx in sample_transactions]
        data_manager.api_client.get_all_pages.return_value = api_data
        
        result = await data_manager.get_transactions(account_id=account_id)
        
        # Verify API was called with account filter
        call_args = data_manager.api_client.get_all_pages.call_args
        assert call_args.kwargs["account_id"] == account_id
        
        # Verify result
        assert len(result) == len(sample_transactions)
    
    @pytest.mark.asyncio
    async def test_get_categories_caching(self, data_manager, sample_categories):
        """Test category retrieval with long-term caching."""
        # Setup cache to return None
        data_manager.cache.get.return_value = None
        
        # Setup API to return data
        api_data = [cat.model_dump() for cat in sample_categories]
        data_manager.api_client.get_all_pages.return_value = api_data
        
        result = await data_manager.get_categories()
        
        # Verify cache was set with long TTL (86400 seconds = 24 hours)
        call_args = data_manager.cache.set.call_args
        assert call_args.kwargs["ttl"] == 86400
        assert call_args.kwargs["namespace"] == "metadata"
        
        # Verify result
        assert len(result) == len(sample_categories)
        assert all(isinstance(cat, Category) for cat in result)
    
    @pytest.mark.asyncio
    async def test_get_merchants(self, data_manager, sample_merchants):
        """Test merchant retrieval."""
        # Setup cache to return None
        data_manager.cache.get.return_value = None
        
        # Setup API to return data
        api_data = [merchant.model_dump() for merchant in sample_merchants]
        data_manager.api_client.get_merchants.return_value = api_data
        
        result = await data_manager.get_merchants()
        
        # Verify API was called
        data_manager.api_client.get_merchants.assert_called_once()
        
        # Verify result
        assert len(result) == len(sample_merchants)
        assert all(isinstance(merchant, Merchant) for merchant in result)
    
    @pytest.mark.asyncio
    async def test_get_tags(self, data_manager, sample_tags):
        """Test tag retrieval."""
        # Setup cache to return None
        data_manager.cache.get.return_value = None
        
        # Setup API to return data
        api_data = [tag.model_dump() for tag in sample_tags]
        data_manager.api_client.get_tags.return_value = api_data
        
        result = await data_manager.get_tags()
        
        # Verify API was called
        data_manager.api_client.get_tags.assert_called_once()
        
        # Verify result
        assert len(result) == len(sample_tags)
        assert all(isinstance(tag, Tag) for tag in result)
    
    @pytest.mark.asyncio
    async def test_get_financial_summary(self, data_manager, sample_accounts, sample_transactions):
        """Test financial summary calculation."""
        # Setup cache to return None for summary
        data_manager.cache.get.return_value = None
        
        # Mock get_accounts and get_transactions to return sample data
        data_manager.get_accounts = AsyncMock(return_value=sample_accounts)
        data_manager.get_transactions = AsyncMock(return_value=sample_transactions)
        
        # Setup calculator to return a summary
        mock_summary = FinancialSummary(
            total_assets=Decimal("20000.00"),
            total_liabilities=Decimal("2500.00"),
            net_worth=Decimal("17500.00"),
            total_cashflow=Decimal("3000.00"),
            total_outflow=Decimal("200.00")
        )
        data_manager.calculator.calculate_financial_summary.return_value = mock_summary
        
        result = await data_manager.get_financial_summary()
        
        # Verify dependencies were called
        data_manager.get_accounts.assert_called_once()
        data_manager.get_transactions.assert_called_once()
        data_manager.calculator.calculate_financial_summary.assert_called_once()
        
        # Verify cache was updated
        data_manager.cache.set.assert_called_once()
        
        # Verify result
        assert isinstance(result, FinancialSummary)
        assert result.net_worth == Decimal("17500.00")
    
    @pytest.mark.asyncio
    async def test_get_monthly_cashflow(self, data_manager, sample_transactions):
        """Test monthly cashflow calculation."""
        year, month = 2023, 6
        
        # Setup cache to return None
        data_manager.cache.get.return_value = None
        
        # Setup API to return transactions
        api_data = [tx.model_dump() for tx in sample_transactions]
        data_manager.api_client.get_all_pages.return_value = api_data
        
        # Setup calculator to return a summary
        from custom_components.sure_finance.models import CashflowSummary
        mock_summary = CashflowSummary(
            period_start=datetime(2023, 6, 1),
            period_end=datetime(2023, 6, 30),
            total_income=Decimal("3000.00"),
            total_expenses=Decimal("200.00"),
            net_cashflow=Decimal("2800.00")
        )
        data_manager.calculator.calculate_cashflow_summary.return_value = mock_summary
        
        result = await data_manager.get_monthly_cashflow(year, month)
        
        # Verify API was called with correct date range
        call_args = data_manager.api_client.get_all_pages.call_args
        date_range = call_args.kwargs["date_range"]
        assert date_range.start_date == datetime(2023, 6, 1)
        assert date_range.end_date == datetime(2023, 6, 30)
        
        # Verify calculator was called
        data_manager.calculator.calculate_cashflow_summary.assert_called_once()
        
        # Verify cache was updated with long TTL
        call_args = data_manager.cache.set.call_args
        assert call_args.kwargs["ttl"] == 86400
        assert call_args.kwargs["namespace"] == "cashflow"
        
        # Verify result
        assert isinstance(result, CashflowSummary)
        assert result.total_income == Decimal("3000.00")
    
    @pytest.mark.asyncio
    async def test_get_monthly_cashflow_december(self, data_manager):
        """Test monthly cashflow calculation for December (year boundary)."""
        year, month = 2023, 12
        
        # Setup cache to return None
        data_manager.cache.get.return_value = None
        
        # Setup API to return empty transactions
        data_manager.api_client.get_all_pages.return_value = []
        
        # Setup calculator to return a summary
        from custom_components.sure_finance.models import CashflowSummary
        mock_summary = CashflowSummary(
            period_start=datetime(2023, 12, 1),
            period_end=datetime(2023, 12, 31),
            total_income=Decimal("0.00"),
            total_expenses=Decimal("0.00"),
            net_cashflow=Decimal("0.00")
        )
        data_manager.calculator.calculate_cashflow_summary.return_value = mock_summary
        
        result = await data_manager.get_monthly_cashflow(year, month)
        
        # Verify API was called with correct date range for December
        call_args = data_manager.api_client.get_all_pages.call_args
        date_range = call_args.kwargs["date_range"]
        assert date_range.start_date == datetime(2023, 12, 1)
        assert date_range.end_date == datetime(2023, 12, 31)
    
    @pytest.mark.asyncio
    async def test_sync_all_data(self, data_manager, sample_accounts, sample_categories, sample_merchants, sample_tags, sample_transactions):
        """Test full data synchronization."""
        # Mock all the individual get methods
        data_manager.get_accounts = AsyncMock(return_value=sample_accounts)
        data_manager.get_categories = AsyncMock(return_value=sample_categories)
        data_manager.get_merchants = AsyncMock(return_value=sample_merchants)
        data_manager.get_tags = AsyncMock(return_value=sample_tags)
        data_manager.get_transactions = AsyncMock(return_value=sample_transactions)
        data_manager.get_financial_summary = AsyncMock()
        
        await data_manager.sync_all_data()
        
        # Verify all methods were called with force_refresh=True
        data_manager.get_accounts.assert_called_once_with(force_refresh=True)
        data_manager.get_categories.assert_called_once_with(force_refresh=True)
        data_manager.get_merchants.assert_called_once_with(force_refresh=True)
        data_manager.get_tags.assert_called_once_with(force_refresh=True)
        data_manager.get_transactions.assert_called_once_with(days=90, force_refresh=True)
        data_manager.get_financial_summary.assert_called_once_with(force_refresh=True)
    
    @pytest.mark.asyncio
    async def test_sync_all_data_error_handling(self, data_manager):
        """Test error handling during full data synchronization."""
        # Mock one method to raise an error
        data_manager.get_accounts = AsyncMock(side_effect=APIError("API Error"))
        data_manager.get_categories = AsyncMock()
        data_manager.get_merchants = AsyncMock()
        data_manager.get_tags = AsyncMock()
        
        # Should re-raise the error
        with pytest.raises(APIError):
            await data_manager.sync_all_data()
    
    def test_needs_update_no_previous_update(self, data_manager):
        """Test needs_update returns True when no previous update exists."""
        assert data_manager.needs_update("accounts") is True
    
    def test_needs_update_recent_update(self, data_manager):
        """Test needs_update returns False for recent updates."""
        # Set a recent update time
        data_manager._last_updates["accounts"] = datetime.utcnow() - timedelta(seconds=100)
        
        # Should not need update (update_interval is 300 seconds)
        assert data_manager.needs_update("accounts") is False
    
    def test_needs_update_old_update(self, data_manager):
        """Test needs_update returns True for old updates."""
        # Set an old update time
        data_manager._last_updates["accounts"] = datetime.utcnow() - timedelta(seconds=400)
        
        # Should need update (update_interval is 300 seconds)
        assert data_manager.needs_update("accounts") is True
    
    @pytest.mark.asyncio
    async def test_periodic_sync_with_updates_needed(self, data_manager):
        """Test periodic sync when updates are needed."""
        # Mock needs_update to return True
        data_manager.needs_update = MagicMock(return_value=True)
        
        # Mock the get methods
        data_manager.get_accounts = AsyncMock()
        data_manager.get_transactions = AsyncMock()
        data_manager.get_financial_summary = AsyncMock()
        
        # Mock cache cleanup
        data_manager.cache.cleanup_expired = MagicMock()
        
        # Run one iteration of periodic sync
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]  # Stop after first iteration
            
            with pytest.raises(asyncio.CancelledError):
                await data_manager.periodic_sync()
        
        # Verify methods were called
        data_manager.get_accounts.assert_called_once_with(force_refresh=True)
        data_manager.get_transactions.assert_called_once_with(days=30, force_refresh=True)
        data_manager.get_financial_summary.assert_called_once_with(force_refresh=True)
        data_manager.cache.cleanup_expired.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_periodic_sync_no_updates_needed(self, data_manager):
        """Test periodic sync when no updates are needed."""
        # Mock needs_update to return False
        data_manager.needs_update = MagicMock(return_value=False)
        
        # Mock the get methods
        data_manager.get_accounts = AsyncMock()
        data_manager.get_transactions = AsyncMock()
        data_manager.get_financial_summary = AsyncMock()
        
        # Mock cache cleanup
        data_manager.cache.cleanup_expired = MagicMock()
        
        # Run one iteration of periodic sync
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]  # Stop after first iteration
            
            with pytest.raises(asyncio.CancelledError):
                await data_manager.periodic_sync()
        
        # Verify get methods were not called
        data_manager.get_accounts.assert_not_called()
        data_manager.get_transactions.assert_not_called()
        data_manager.get_financial_summary.assert_not_called()
        
        # Cache cleanup should still be called
        data_manager.cache.cleanup_expired.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_periodic_sync_error_handling(self, data_manager):
        """Test error handling in periodic sync."""
        # Mock needs_update to return True
        data_manager.needs_update = MagicMock(return_value=True)
        
        # Mock get_accounts to raise an error
        data_manager.get_accounts = AsyncMock(side_effect=APIError("API Error"))
        
        # Mock cache cleanup
        data_manager.cache.cleanup_expired = MagicMock()
        
        # Run one iteration of periodic sync
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]  # Stop after first iteration
            
            with pytest.raises(asyncio.CancelledError):
                await data_manager.periodic_sync()
        
        # Should continue despite the error
        data_manager.cache.cleanup_expired.assert_called_once()


class TestCacheKeyGeneration:
    """Test suite for cache key generation methods."""
    
    def test_cache_key_methods(self, mock_cache_manager):
        """Test cache key generation methods."""
        # Test account key
        assert mock_cache_manager.account_key() == "accounts:all"
        assert mock_cache_manager.account_key("123") == "account:123"
        
        # Test transaction key
        assert mock_cache_manager.transaction_key() == "transactions"
        assert mock_cache_manager.transaction_key("123") == "transactions:account:123"
        assert mock_cache_manager.transaction_key(page=2) == "transactions:page:2"
        assert mock_cache_manager.transaction_key("123", 2) == "transactions:account:123:page:2"
        
        # Test summary key
        assert mock_cache_manager.summary_key() == "summary:current"
        assert mock_cache_manager.summary_key("monthly") == "summary:monthly"
        
        # Test cashflow key
        assert mock_cache_manager.cashflow_key(2023, 6) == "cashflow:2023-06"
        assert mock_cache_manager.cashflow_key(2023, 12) == "cashflow:2023-12"


class TestDataManagerIntegration:
    """Integration tests for DataManager with real-like scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_data_flow(self, mock_api_client, mock_cache_manager, mock_financial_calculator, sample_accounts, sample_transactions):
        """Test complete data flow from API to cache to calculation."""
        # Setup data manager
        data_manager = DataManager(
            api_client=mock_api_client,
            cache_manager=mock_cache_manager,
            calculator=mock_financial_calculator,
            update_interval=300
        )
        
        # Setup cache to be empty initially
        mock_cache_manager.get.return_value = None
        
        # Setup API responses
        mock_api_client.get_all_pages.side_effect = [
            [acc.model_dump() for acc in sample_accounts],  # get_accounts call
            [tx.model_dump() for tx in sample_transactions]  # get_transactions call
        ]
        
        # Setup calculator
        mock_summary = FinancialSummary(
            total_assets=Decimal("20000.00"),
            total_liabilities=Decimal("2500.00"),
            net_worth=Decimal("17500.00")
        )
        mock_financial_calculator.calculate_financial_summary.return_value = mock_summary
        
        # Get financial summary (should trigger full data flow)
        result = await data_manager.get_financial_summary()
        
        # Verify API calls
        assert mock_api_client.get_all_pages.call_count == 2
        
        # Verify cache updates
        assert mock_cache_manager.set.call_count >= 3  # accounts, transactions, summary
        
        # Verify calculation
        mock_financial_calculator.calculate_financial_summary.assert_called_once()
        
        # Verify result
        assert isinstance(result, FinancialSummary)
        assert result.net_worth == Decimal("17500.00")
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self, mock_api_client, mock_cache_manager, mock_financial_calculator, sample_accounts):
        """Test error recovery using cached data."""
        data_manager = DataManager(
            api_client=mock_api_client,
            cache_manager=mock_cache_manager,
            calculator=mock_financial_calculator,
            update_interval=300
        )
        
        # Setup cache to return None initially, then cached data on fallback
        cached_data = [acc.model_dump() for acc in sample_accounts]
        mock_cache_manager.get.side_effect = [None, cached_data]
        
        # Setup API to fail
        mock_api_client.get_all_pages.side_effect = APIError("Network error")
        
        # Should recover using cached data
        result = await data_manager.get_accounts()
        
        # Verify fallback to cache
        assert mock_cache_manager.get.call_count == 2
        assert len(result) == len(sample_accounts)
    
    @pytest.mark.asyncio
    async def test_concurrent_data_access(self, mock_api_client, mock_cache_manager, mock_financial_calculator, sample_accounts):
        """Test concurrent access to data manager methods."""
        data_manager = DataManager(
            api_client=mock_api_client,
            cache_manager=mock_cache_manager,
            calculator=mock_financial_calculator,
            update_interval=300
        )
        
        # Setup cache to be empty
        mock_cache_manager.get.return_value = None
        
        # Setup API response
        api_data = [acc.model_dump() for acc in sample_accounts]
        mock_api_client.get_all_pages.return_value = api_data
        
        # Make concurrent requests
        tasks = [
            data_manager.get_accounts(),
            data_manager.get_accounts(),
            data_manager.get_accounts()
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 3
        assert all(len(result) == len(sample_accounts) for result in results)
        
        # API might be called multiple times due to concurrency
        assert mock_api_client.get_all_pages.call_count >= 1
