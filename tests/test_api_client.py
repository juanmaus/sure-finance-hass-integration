"""Tests for Sure Finance API Client."""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from aiohttp import ClientError, ClientSession, ClientTimeout

from custom_components.sure_finance.api_client import (
    APIError,
    AuthenticationError,
    DateRangeParams,
    PaginationParams,
    RateLimitError,
    SureFinanceClient,
)
from conftest import MockResponse, create_mock_response


class TestSureFinanceClient:
    """Test suite for SureFinanceClient."""
    
    @pytest.fixture
    def client(self):
        """Create a test client instance."""
        return SureFinanceClient(
            api_key="test_api_key",
            base_url="https://test.sure.am",
            timeout=30
        )
    
    def test_client_initialization(self):
        """Test client initialization with various parameters."""
        # Test with default values
        client = SureFinanceClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.base_url == "https://app.sure.am"
        assert client.timeout.total == 30
        
        # Test with custom values
        client = SureFinanceClient(
            api_key="custom_key",
            base_url="https://custom.sure.am",
            timeout=60
        )
        assert client.api_key == "custom_key"
        assert client.base_url == "https://custom.sure.am"
        assert client.timeout.total == 60
    
    def test_build_url(self, client):
        """Test URL building functionality."""
        # Test basic endpoint
        url = client._build_url("/api/v1/accounts")
        assert url == "https://test.sure.am/api/v1/accounts"
        
        # Test endpoint without leading slash
        url = client._build_url("api/v1/transactions")
        assert url == "https://test.sure.am/api/v1/transactions"
        
        # Test empty endpoint
        url = client._build_url("")
        assert url == "https://test.sure.am"
    
    @pytest.mark.asyncio
    async def test_connect_and_close(self, client):
        """Test connection establishment and cleanup."""
        # Initially no session
        assert client._session is None
        
        # Connect creates session
        await client.connect()
        assert client._session is not None
        assert isinstance(client._session, ClientSession)
        
        # Close cleans up session
        await client.close()
        assert client._session is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with SureFinanceClient(api_key="test") as client:
            assert client._session is not None
        # Session should be closed after exiting context
        assert client._session is None
    
    @pytest.mark.asyncio
    async def test_successful_request(self, client, mock_aiohttp_session):
        """Test successful API request handling."""
        # Setup mock response
        test_data = {"accounts": [{"id": str(uuid4()), "name": "Test Account"}]}
        mock_response = create_mock_response(200, test_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        # Make request
        result = await client._request("GET", "/api/v1/accounts")
        
        # Verify result
        assert result == test_data
        mock_aiohttp_session.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authentication_error(self, client, mock_aiohttp_session):
        """Test authentication error handling."""
        # Setup mock 401 response
        error_data = {"error": "Invalid API key"}
        mock_response = create_mock_response(401, error_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        # Test authentication error
        with pytest.raises(AuthenticationError) as exc_info:
            await client._request("GET", "/api/v1/accounts")
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.details == error_data
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client, mock_aiohttp_session):
        """Test rate limit error handling."""
        # Setup mock 429 response
        error_data = {"error": "Rate limit exceeded", "retry_after": 60}
        mock_response = create_mock_response(429, error_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        # Test rate limit error
        with pytest.raises(RateLimitError) as exc_info:
            await client._request("GET", "/api/v1/accounts")
        
        assert exc_info.value.status_code == 429
        assert exc_info.value.details == error_data
    
    @pytest.mark.asyncio
    async def test_generic_api_error(self, client, mock_aiohttp_session):
        """Test generic API error handling."""
        # Setup mock 500 response
        error_data = {"error": "Internal server error"}
        mock_response = create_mock_response(500, error_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        # Test generic API error
        with pytest.raises(APIError) as exc_info:
            await client._request("GET", "/api/v1/accounts")
        
        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_network_error(self, client):
        """Test network error handling."""
        # Mock ClientError
        with patch.object(client, '_session') as mock_session:
            mock_session.request.side_effect = ClientError("Network error")
            
            with pytest.raises(APIError) as exc_info:
                await client._request("GET", "/api/v1/accounts")
            
            assert "Network error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_empty_response(self, client, mock_aiohttp_session):
        """Test handling of empty response body."""
        # Setup mock response with no content
        mock_response = create_mock_response(200, {})
        mock_response.content_length = 0
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        # Make request
        result = await client._request("GET", "/api/v1/accounts")
        
        # Should return empty dict for empty response
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_accounts(self, client, mock_aiohttp_session):
        """Test get_accounts method."""
        test_data = {
            "accounts": [{"id": str(uuid4()), "name": "Test Account"}],
            "pagination": {"page": 1, "per_page": 25, "total_count": 1}
        }
        mock_response = create_mock_response(200, test_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        # Test without pagination
        result = await client.get_accounts()
        assert result == test_data
        
        # Test with pagination
        pagination = PaginationParams(page=2, per_page=50)
        result = await client.get_accounts(pagination=pagination)
        assert result == test_data
        
        # Verify pagination parameters were passed
        call_args = mock_aiohttp_session.request.call_args
        assert "params" in call_args.kwargs
        params = call_args.kwargs["params"]
        assert params["page"] == 2
        assert params["per_page"] == 50
    
    @pytest.mark.asyncio
    async def test_get_transactions(self, client, mock_aiohttp_session):
        """Test get_transactions method with various parameters."""
        test_data = {
            "transactions": [{"id": str(uuid4()), "name": "Test Transaction"}],
            "pagination": {"page": 1, "per_page": 25, "total_count": 1}
        }
        mock_response = create_mock_response(200, test_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        # Test with date range
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        date_range = DateRangeParams(start_date=start_date, end_date=end_date)
        
        result = await client.get_transactions(
            date_range=date_range,
            account_id="test_account_id",
            category_id="test_category_id",
            merchant_id="test_merchant_id",
            transaction_type="expense",
            search="test search"
        )
        
        assert result == test_data
        
        # Verify parameters were passed correctly
        call_args = mock_aiohttp_session.request.call_args
        params = call_args.kwargs["params"]
        assert params["start_date"] == "2023-01-01"
        assert params["end_date"] == "2023-12-31"
        assert params["account_id"] == "test_account_id"
        assert params["category_id"] == "test_category_id"
        assert params["merchant_id"] == "test_merchant_id"
        assert params["type"] == "expense"
        assert params["search"] == "test search"
    
    @pytest.mark.asyncio
    async def test_get_categories(self, client, mock_aiohttp_session):
        """Test get_categories method."""
        test_data = {
            "categories": [{"id": str(uuid4()), "name": "Test Category"}],
            "pagination": {"page": 1, "per_page": 25, "total_count": 1}
        }
        mock_response = create_mock_response(200, test_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        # Test with all parameters
        pagination = PaginationParams(page=1, per_page=50)
        result = await client.get_categories(
            pagination=pagination,
            classification="expense",
            roots_only=True,
            parent_id="parent_123"
        )
        
        assert result == test_data
        
        # Verify parameters
        call_args = mock_aiohttp_session.request.call_args
        params = call_args.kwargs["params"]
        assert params["page"] == 1
        assert params["per_page"] == 50
        assert params["classification"] == "expense"
        assert params["roots_only"] == "true"
        assert params["parent_id"] == "parent_123"
    
    @pytest.mark.asyncio
    async def test_get_category(self, client, mock_aiohttp_session):
        """Test get_category method for single category."""
        category_id = str(uuid4())
        test_data = {"id": category_id, "name": "Test Category"}
        mock_response = create_mock_response(200, test_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        result = await client.get_category(category_id)
        assert result == test_data
        
        # Verify correct endpoint was called
        call_args = mock_aiohttp_session.request.call_args
        assert f"/api/v1/categories/{category_id}" in call_args[1]  # URL argument
    
    @pytest.mark.asyncio
    async def test_get_merchants(self, client, mock_aiohttp_session):
        """Test get_merchants method."""
        test_data = [{"id": str(uuid4()), "name": "Test Merchant"}]
        mock_response = create_mock_response(200, test_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        result = await client.get_merchants()
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_get_tags(self, client, mock_aiohttp_session):
        """Test get_tags method."""
        test_data = [{"id": str(uuid4()), "name": "Test Tag"}]
        mock_response = create_mock_response(200, test_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        result = await client.get_tags()
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_get_all_pages_accounts(self, client):
        """Test get_all_pages method with accounts endpoint."""
        # Mock multiple pages of data
        page1_data = {
            "accounts": [
                {"id": str(uuid4()), "name": "Account 1"},
                {"id": str(uuid4()), "name": "Account 2"}
            ],
            "pagination": {"page": 1, "per_page": 2, "total_count": 3, "total_pages": 2}
        }
        page2_data = {
            "accounts": [
                {"id": str(uuid4()), "name": "Account 3"}
            ],
            "pagination": {"page": 2, "per_page": 2, "total_count": 3, "total_pages": 2}
        }
        
        # Mock the get_accounts method to return different pages
        client.get_accounts = AsyncMock(side_effect=[page1_data, page2_data])
        
        # Test get_all_pages
        result = await client.get_all_pages(client.get_accounts, per_page=2)
        
        # Should return all accounts from both pages
        assert len(result) == 3
        assert result[0]["name"] == "Account 1"
        assert result[1]["name"] == "Account 2"
        assert result[2]["name"] == "Account 3"
        
        # Verify get_accounts was called twice with correct pagination
        assert client.get_accounts.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_all_pages_transactions(self, client):
        """Test get_all_pages method with transactions endpoint."""
        # Mock single page of transactions
        page_data = {
            "transactions": [
                {"id": str(uuid4()), "name": "Transaction 1"}
            ],
            "pagination": {"page": 1, "per_page": 1, "total_count": 1, "total_pages": 1}
        }
        
        client.get_transactions = AsyncMock(return_value=page_data)
        
        result = await client.get_all_pages(client.get_transactions, per_page=100)
        
        assert len(result) == 1
        assert result[0]["name"] == "Transaction 1"
    
    @pytest.mark.asyncio
    async def test_get_all_pages_no_pagination(self, client):
        """Test get_all_pages method with response that has no pagination info."""
        # Mock response without pagination
        response_data = {"some_data": "value"}
        
        mock_endpoint = AsyncMock(return_value=response_data)
        
        result = await client.get_all_pages(mock_endpoint)
        
        # Should return empty list when no recognizable data structure
        assert result == []
    
    @pytest.mark.asyncio
    async def test_auto_connect_on_request(self, client, mock_aiohttp_session):
        """Test that _request automatically connects if no session exists."""
        test_data = {"test": "data"}
        mock_response = create_mock_response(200, test_data)
        
        # Mock the connect method and session creation
        with patch.object(client, 'connect') as mock_connect:
            mock_connect.return_value = None
            client._session = mock_aiohttp_session
            mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
            
            # Initially no session
            client._session = None
            
            result = await client._request("GET", "/test")
            
            # Should have called connect
            mock_connect.assert_called_once()
            assert result == test_data


class TestPaginationParams:
    """Test suite for PaginationParams model."""
    
    def test_default_values(self):
        """Test default pagination parameter values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.per_page == 25
    
    def test_custom_values(self):
        """Test custom pagination parameter values."""
        params = PaginationParams(page=5, per_page=50)
        assert params.page == 5
        assert params.per_page == 50
    
    def test_validation(self):
        """Test pagination parameter validation."""
        # Test minimum values
        with pytest.raises(ValueError):
            PaginationParams(page=0)  # page must be >= 1
        
        with pytest.raises(ValueError):
            PaginationParams(per_page=0)  # per_page must be >= 1
        
        with pytest.raises(ValueError):
            PaginationParams(per_page=101)  # per_page must be <= 100
    
    def test_model_dump(self):
        """Test model serialization."""
        params = PaginationParams(page=2, per_page=50)
        dumped = params.model_dump(exclude_none=True)
        assert dumped == {"page": 2, "per_page": 50}


class TestDateRangeParams:
    """Test suite for DateRangeParams model."""
    
    def test_default_values(self):
        """Test default date range parameter values."""
        params = DateRangeParams()
        assert params.start_date is None
        assert params.end_date is None
    
    def test_custom_values(self):
        """Test custom date range parameter values."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        params = DateRangeParams(start_date=start_date, end_date=end_date)
        assert params.start_date == start_date
        assert params.end_date == end_date
    
    def test_model_dump_exclude_none(self):
        """Test model serialization excluding None values."""
        start_date = datetime(2023, 1, 1)
        params = DateRangeParams(start_date=start_date)
        dumped = params.model_dump(exclude_none=True)
        assert dumped == {"start_date": start_date}
        assert "end_date" not in dumped


class TestAPIErrors:
    """Test suite for API error classes."""
    
    def test_api_error_basic(self):
        """Test basic APIError functionality."""
        error = APIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.details == {}
    
    def test_api_error_with_details(self):
        """Test APIError with status code and details."""
        details = {"field": "error message"}
        error = APIError("Test error", status_code=400, details=details)
        assert str(error) == "Test error"
        assert error.status_code == 400
        assert error.details == details
    
    def test_authentication_error(self):
        """Test AuthenticationError inheritance."""
        error = AuthenticationError("Auth failed", status_code=401)
        assert isinstance(error, APIError)
        assert str(error) == "Auth failed"
        assert error.status_code == 401
    
    def test_rate_limit_error(self):
        """Test RateLimitError inheritance."""
        error = RateLimitError("Rate limited", status_code=429)
        assert isinstance(error, APIError)
        assert str(error) == "Rate limited"
        assert error.status_code == 429


class TestRetryLogic:
    """Test suite for retry logic and error handling."""
    
    @pytest.mark.asyncio
    async def test_retry_on_network_error(self, client):
        """Test that network errors are properly handled without retry in base client."""
        # Note: Base client doesn't implement retry logic
        # This test ensures network errors are properly raised
        with patch.object(client, '_session') as mock_session:
            mock_session.request.side_effect = ClientError("Connection failed")
            
            with pytest.raises(APIError) as exc_info:
                await client._request("GET", "/test")
            
            assert "Connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout configuration and handling."""
        client = SureFinanceClient(api_key="test", timeout=5)
        assert client.timeout.total == 5
        
        # Test that timeout is passed to session
        await client.connect()
        assert client._session.timeout.total == 5
        await client.close()


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_malformed_json_response(self, client, mock_aiohttp_session):
        """Test handling of malformed JSON responses."""
        # Mock response that raises exception on json()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content_length = 100
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        client._session = mock_aiohttp_session
        
        # Should raise an exception when JSON parsing fails
        with pytest.raises(Exception):
            await client._request("GET", "/test")
    
    @pytest.mark.asyncio
    async def test_very_large_response(self, client, mock_aiohttp_session):
        """Test handling of very large API responses."""
        # Create a large response
        large_data = {"items": [f"item_{i}" for i in range(10000)]}
        mock_response = create_mock_response(200, large_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        result = await client._request("GET", "/test")
        assert len(result["items"]) == 10000
    
    def test_invalid_base_url(self):
        """Test client behavior with invalid base URL."""
        # Client should accept any string as base URL
        client = SureFinanceClient(api_key="test", base_url="not-a-url")
        assert client.base_url == "not-a-url"
        
        # URL building should still work
        url = client._build_url("/test")
        assert url == "not-a-url/test"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client, mock_aiohttp_session):
        """Test handling of concurrent requests."""
        import asyncio
        
        test_data = {"test": "data"}
        mock_response = create_mock_response(200, test_data)
        mock_aiohttp_session.request.return_value.__aenter__.return_value = mock_response
        
        client._session = mock_aiohttp_session
        
        # Make multiple concurrent requests
        tasks = [
            client._request("GET", f"/test/{i}")
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert len(results) == 5
        assert all(result == test_data for result in results)
        assert mock_aiohttp_session.request.call_count == 5
