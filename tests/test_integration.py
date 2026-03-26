"""Integration tests for Sure Finance Home Assistant Integration."""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.sure_finance import (
    DOMAIN,
    PLATFORMS,
    async_remove_services,
    async_setup,
    async_setup_entry,
    async_setup_services,
    async_unload_entry,
)
from custom_components.sure_finance.api_client import AuthenticationError
from custom_components.sure_finance.models import (
    Account,
    AccountClassification,
    FinancialSummary,
)


class TestIntegrationSetup:
    """Test suite for integration setup and teardown."""
    
    @pytest.mark.asyncio
    async def test_async_setup(self, mock_hass):
        """Test basic integration setup."""
        config = {}
        
        result = await async_setup(mock_hass, config)
        
        assert result is True
        assert DOMAIN in mock_hass.data
        assert mock_hass.data[DOMAIN] == {}
    
    @pytest.mark.asyncio
    async def test_async_setup_entry_success(self, mock_hass, mock_config_entry):
        """Test successful config entry setup."""
        # Setup mocks
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        # Mock API client
        with patch('custom_components.sure_finance.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect.return_value = None
            mock_client.get_accounts.return_value = [
                {"id": str(uuid4()), "name": "Test Account", "balance": "1000.00"}
            ]
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client
            
            # Mock cache manager
            with patch('custom_components.sure_finance.CacheManager') as mock_cache_class:
                mock_cache = AsyncMock()
                mock_cache.connect_redis.return_value = None
                mock_cache_class.return_value = mock_cache
                
                # Mock financial calculator
                with patch('custom_components.sure_finance.FinancialCalculator') as mock_calc_class:
                    mock_calc = MagicMock()
                    mock_calc_class.return_value = mock_calc
                    
                    # Mock data manager
                    with patch('custom_components.sure_finance.DataManager') as mock_dm_class:
                        mock_dm = MagicMock()
                        mock_dm_class.return_value = mock_dm
                        
                        result = await async_setup_entry(mock_hass, mock_config_entry)
                        
                        assert result is True
                        
                        # Verify components were created
                        mock_client_class.assert_called_once()
                        mock_cache_class.assert_called_once()
                        mock_calc_class.assert_called_once()
                        mock_dm_class.assert_called_once()
                        
                        # Verify API connection was tested
                        mock_client.connect.assert_called_once()
                        mock_client.get_accounts.assert_called_once()
                        
                        # Verify cache connection
                        mock_cache.connect_redis.assert_called_once()
                        
                        # Verify data was stored
                        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
                        entry_data = mock_hass.data[DOMAIN][mock_config_entry.entry_id]
                        assert "api_client" in entry_data
                        assert "cache_manager" in entry_data
                        assert "data_manager" in entry_data
                        assert "calculator" in entry_data
                        
                        # Verify platform setup
                        mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
                            mock_config_entry, PLATFORMS
                        )
    
    @pytest.mark.asyncio
    async def test_async_setup_entry_auth_error(self, mock_hass, mock_config_entry):
        """Test setup with authentication error."""
        mock_hass.data = {DOMAIN: {}}
        
        with patch('custom_components.sure_finance.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect.return_value = None
            mock_client.get_accounts.side_effect = AuthenticationError("Invalid API key")
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client
            
            result = await async_setup_entry(mock_hass, mock_config_entry)
            
            assert result is False
            
            # Verify client was still closed
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_setup_entry_connection_error(self, mock_hass, mock_config_entry):
        """Test setup with connection error."""
        mock_hass.data = {DOMAIN: {}}
        
        with patch('custom_components.sure_finance.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect.side_effect = ConnectionError("Network error")
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client
            
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(mock_hass, mock_config_entry)
    
    @pytest.mark.asyncio
    async def test_async_setup_entry_with_custom_config(self, mock_hass):
        """Test setup with custom configuration values."""
        custom_config = ConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Sure Finance",
            data={
                CONF_API_KEY: "custom_api_key",
                "host": "https://custom.sure.am",
                "base_url": "https://api.custom.sure.am",  # Should take precedence over host
                "update_interval": 600,
                "currency": "EUR",
                "cache_duration": 7200,
            },
            source="user",
            entry_id="custom_entry_id",
        )
        
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        with patch('custom_components.sure_finance.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect.return_value = None
            mock_client.get_accounts.return_value = []
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client
            
            with patch('custom_components.sure_finance.CacheManager') as mock_cache_class:
                mock_cache = AsyncMock()
                mock_cache.connect_redis.return_value = None
                mock_cache_class.return_value = mock_cache
                
                with patch('custom_components.sure_finance.FinancialCalculator') as mock_calc_class:
                    mock_calc = MagicMock()
                    mock_calc_class.return_value = mock_calc
                    
                    with patch('custom_components.sure_finance.DataManager') as mock_dm_class:
                        mock_dm = MagicMock()
                        mock_dm_class.return_value = mock_dm
                        
                        result = await async_setup_entry(mock_hass, custom_config)
                        
                        assert result is True
                        
                        # Verify API client was created with custom values
                        mock_client_class.assert_called_once_with(
                            api_key="custom_api_key",
                            base_url="https://api.custom.sure.am",  # base_url takes precedence
                            timeout=30
                        )
                        
                        # Verify cache manager was created with custom cache duration
                        cache_call_args = mock_cache_class.call_args
                        assert cache_call_args.kwargs["default_ttl"] == 7200
                        
                        # Verify financial calculator was created with custom currency
                        mock_calc_class.assert_called_once_with(currency="EUR")
                        
                        # Verify data manager was created with custom update interval
                        dm_call_args = mock_dm_class.call_args
                        assert dm_call_args.kwargs["update_interval"] == 600
    
    @pytest.mark.asyncio
    async def test_async_unload_entry_success(self, mock_hass, mock_config_entry):
        """Test successful config entry unload."""
        # Setup entry data
        mock_api_client = AsyncMock()
        mock_cache_manager = AsyncMock()
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "api_client": mock_api_client,
                    "cache_manager": mock_cache_manager,
                    "data_manager": MagicMock(),
                    "calculator": MagicMock(),
                }
            }
        }
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        with patch('custom_components.sure_finance.async_remove_services') as mock_remove_services:
            result = await async_unload_entry(mock_hass, mock_config_entry)
            
            assert result is True
            
            # Verify platforms were unloaded
            mock_hass.config_entries.async_unload_platforms.assert_called_once_with(
                mock_config_entry, PLATFORMS
            )
            
            # Verify cleanup was performed
            mock_api_client.close.assert_called_once()
            mock_cache_manager.close.assert_called_once()
            
            # Verify entry data was removed
            assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]
            
            # Verify services were removed (no more entries)
            mock_remove_services.assert_called_once_with(mock_hass)
    
    @pytest.mark.asyncio
    async def test_async_unload_entry_failure(self, mock_hass, mock_config_entry):
        """Test config entry unload failure."""
        # Setup entry data
        mock_api_client = AsyncMock()
        mock_cache_manager = AsyncMock()
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "api_client": mock_api_client,
                    "cache_manager": mock_cache_manager,
                    "data_manager": MagicMock(),
                    "calculator": MagicMock(),
                }
            }
        }
        
        # Mock platform unload failure
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
        
        result = await async_unload_entry(mock_hass, mock_config_entry)
        
        assert result is False
        
        # Verify cleanup was not performed
        mock_api_client.close.assert_not_called()
        mock_cache_manager.close.assert_not_called()
        
        # Verify entry data was not removed
        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
    
    @pytest.mark.asyncio
    async def test_async_unload_entry_with_remaining_entries(self, mock_hass, mock_config_entry):
        """Test unload when other entries still exist."""
        # Setup multiple entries
        other_entry_id = "other_entry_id"
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "api_client": AsyncMock(),
                    "cache_manager": AsyncMock(),
                    "data_manager": MagicMock(),
                    "calculator": MagicMock(),
                },
                other_entry_id: {
                    "api_client": AsyncMock(),
                    "cache_manager": AsyncMock(),
                    "data_manager": MagicMock(),
                    "calculator": MagicMock(),
                }
            }
        }
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        with patch('custom_components.sure_finance.async_remove_services') as mock_remove_services:
            result = await async_unload_entry(mock_hass, mock_config_entry)
            
            assert result is True
            
            # Verify services were not removed (other entries still exist)
            mock_remove_services.assert_not_called()
            
            # Verify only the target entry was removed
            assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]
            assert other_entry_id in mock_hass.data[DOMAIN]


class TestIntegrationServices:
    """Test suite for integration services."""
    
    @pytest.mark.asyncio
    async def test_async_setup_services(self, mock_hass, mock_config_entry):
        """Test service registration."""
        # Setup entry data
        mock_data_manager = AsyncMock()
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "data_manager": mock_data_manager,
                    "cache_manager": AsyncMock(),
                }
            }
        }
        
        await async_setup_services(mock_hass, mock_config_entry)
        
        # Verify services were registered
        assert mock_hass.services.async_register.call_count == 2
        
        # Verify service calls
        service_calls = mock_hass.services.async_register.call_args_list
        
        # Check refresh_data service
        refresh_call = service_calls[0]
        assert refresh_call[0] == (DOMAIN, "refresh_data")
        
        # Check clear_cache service
        clear_call = service_calls[1]
        assert clear_call[0] == (DOMAIN, "clear_cache")
    
    @pytest.mark.asyncio
    async def test_refresh_data_service(self, mock_hass, mock_config_entry):
        """Test refresh_data service functionality."""
        # Setup entry data
        mock_data_manager = AsyncMock()
        mock_coordinator = AsyncMock()
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "data_manager": mock_data_manager,
                    "coordinator": mock_coordinator,
                    "cache_manager": AsyncMock(),
                }
            }
        }
        
        await async_setup_services(mock_hass, mock_config_entry)
        
        # Get the refresh_data service function
        refresh_service = mock_hass.services.async_register.call_args_list[0][0][2]
        
        # Call the service
        await refresh_service(None)
        
        # Verify data manager sync was called
        mock_data_manager.sync_all_data.assert_called_once()
        
        # Verify coordinator refresh was called
        mock_coordinator.async_request_refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refresh_data_service_no_coordinator(self, mock_hass, mock_config_entry):
        """Test refresh_data service without coordinator."""
        # Setup entry data without coordinator
        mock_data_manager = AsyncMock()
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "data_manager": mock_data_manager,
                    "cache_manager": AsyncMock(),
                }
            }
        }
        
        await async_setup_services(mock_hass, mock_config_entry)
        
        # Get the refresh_data service function
        refresh_service = mock_hass.services.async_register.call_args_list[0][0][2]
        
        # Call the service (should not raise error)
        await refresh_service(None)
        
        # Verify data manager sync was still called
        mock_data_manager.sync_all_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_cache_service(self, mock_hass, mock_config_entry):
        """Test clear_cache service functionality."""
        # Setup entry data
        mock_cache_manager = AsyncMock()
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "data_manager": AsyncMock(),
                    "cache_manager": mock_cache_manager,
                }
            }
        }
        
        await async_setup_services(mock_hass, mock_config_entry)
        
        # Get the clear_cache service function
        clear_service = mock_hass.services.async_register.call_args_list[1][0][2]
        
        # Call the service
        await clear_service(None)
        
        # Verify cache namespaces were cleared
        expected_calls = [
            mock_cache_manager.clear_namespace("accounts"),
            mock_cache_manager.clear_namespace("transactions"),
            mock_cache_manager.clear_namespace("summaries"),
            mock_cache_manager.clear_namespace("cashflow"),
        ]
        
        assert mock_cache_manager.clear_namespace.call_count == 4
    
    @pytest.mark.asyncio
    async def test_async_remove_services(self, mock_hass):
        """Test service removal."""
        await async_remove_services(mock_hass)
        
        # Verify services were removed
        assert mock_hass.services.async_remove.call_count == 2
        
        removal_calls = mock_hass.services.async_remove.call_args_list
        
        # Check refresh_data service removal
        refresh_removal = removal_calls[0]
        assert refresh_removal[0] == (DOMAIN, "refresh_data")
        
        # Check clear_cache service removal
        clear_removal = removal_calls[1]
        assert clear_removal[0] == (DOMAIN, "clear_cache")


class TestIntegrationErrorHandling:
    """Test suite for integration error handling."""
    
    @pytest.mark.asyncio
    async def test_setup_entry_api_client_creation_error(self, mock_hass, mock_config_entry):
        """Test setup with API client creation error."""
        mock_hass.data = {DOMAIN: {}}
        
        with patch('custom_components.sure_finance.SureFinanceClient') as mock_client_class:
            mock_client_class.side_effect = Exception("Client creation failed")
            
            with pytest.raises(Exception) as exc_info:
                await async_setup_entry(mock_hass, mock_config_entry)
            
            assert "Client creation failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_setup_entry_cache_manager_error(self, mock_hass, mock_config_entry):
        """Test setup with cache manager error."""
        mock_hass.data = {DOMAIN: {}}
        
        with patch('custom_components.sure_finance.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect.return_value = None
            mock_client.get_accounts.return_value = []
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client
            
            with patch('custom_components.sure_finance.CacheManager') as mock_cache_class:
                mock_cache_class.side_effect = Exception("Cache creation failed")
                
                with pytest.raises(Exception) as exc_info:
                    await async_setup_entry(mock_hass, mock_config_entry)
                
                assert "Cache creation failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_setup_entry_redis_connection_error(self, mock_hass, mock_config_entry):
        """Test setup with Redis connection error (should not fail setup)."""
        mock_hass.data = {DOMAIN: {}}
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        with patch('custom_components.sure_finance.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect.return_value = None
            mock_client.get_accounts.return_value = []
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client
            
            with patch('custom_components.sure_finance.CacheManager') as mock_cache_class:
                mock_cache = AsyncMock()
                mock_cache.connect_redis.side_effect = Exception("Redis connection failed")
                mock_cache_class.return_value = mock_cache
                
                with patch('custom_components.sure_finance.FinancialCalculator') as mock_calc_class:
                    mock_calc = MagicMock()
                    mock_calc_class.return_value = mock_calc
                    
                    with patch('custom_components.sure_finance.DataManager') as mock_dm_class:
                        mock_dm = MagicMock()
                        mock_dm_class.return_value = mock_dm
                        
                        # Should succeed despite Redis error
                        result = await async_setup_entry(mock_hass, mock_config_entry)
                        assert result is True
    
    @pytest.mark.asyncio
    async def test_unload_entry_cleanup_errors(self, mock_hass, mock_config_entry):
        """Test unload entry with cleanup errors."""
        # Setup entry data with mocks that raise errors
        mock_api_client = AsyncMock()
        mock_api_client.close.side_effect = Exception("API client close error")
        
        mock_cache_manager = AsyncMock()
        mock_cache_manager.close.side_effect = Exception("Cache manager close error")
        
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "api_client": mock_api_client,
                    "cache_manager": mock_cache_manager,
                    "data_manager": MagicMock(),
                    "calculator": MagicMock(),
                }
            }
        }
        
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        # Should succeed despite cleanup errors
        result = await async_unload_entry(mock_hass, mock_config_entry)
        assert result is True
        
        # Verify cleanup was attempted
        mock_api_client.close.assert_called_once()
        mock_cache_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_service_errors(self, mock_hass, mock_config_entry):
        """Test service error handling."""
        # Setup entry data with failing data manager
        mock_data_manager = AsyncMock()
        mock_data_manager.sync_all_data.side_effect = Exception("Sync failed")
        
        mock_cache_manager = AsyncMock()
        mock_cache_manager.clear_namespace.side_effect = Exception("Clear failed")
        
        mock_hass.data = {
            DOMAIN: {
                mock_config_entry.entry_id: {
                    "data_manager": mock_data_manager,
                    "cache_manager": mock_cache_manager,
                }
            }
        }
        
        await async_setup_services(mock_hass, mock_config_entry)
        
        # Get service functions
        refresh_service = mock_hass.services.async_register.call_args_list[0][0][2]
        clear_service = mock_hass.services.async_register.call_args_list[1][0][2]
        
        # Services should handle errors gracefully
        with pytest.raises(Exception):
            await refresh_service(None)
        
        with pytest.raises(Exception):
            await clear_service(None)


class TestIntegrationConstants:
    """Test suite for integration constants and configuration."""
    
    def test_domain_constant(self):
        """Test domain constant value."""
        assert DOMAIN == "sure_finance"
    
    def test_platforms_constant(self):
        """Test platforms constant value."""
        from homeassistant.const import Platform
        assert PLATFORMS == [Platform.SENSOR]
    
    def test_config_entry_structure(self, mock_config_entry):
        """Test expected config entry structure."""
        assert mock_config_entry.domain == DOMAIN
        assert CONF_API_KEY in mock_config_entry.data
        assert "host" in mock_config_entry.data
        assert "update_interval" in mock_config_entry.data
        assert "currency" in mock_config_entry.data


class TestIntegrationLifecycle:
    """Test suite for complete integration lifecycle."""
    
    @pytest.mark.asyncio
    async def test_complete_lifecycle(self, mock_hass, mock_config_entry):
        """Test complete integration lifecycle from setup to teardown."""
        # Step 1: Basic setup
        result = await async_setup(mock_hass, {})
        assert result is True
        assert DOMAIN in mock_hass.data
        
        # Step 2: Entry setup
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        with patch('custom_components.sure_finance.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect.return_value = None
            mock_client.get_accounts.return_value = []
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client
            
            with patch('custom_components.sure_finance.CacheManager') as mock_cache_class:
                mock_cache = AsyncMock()
                mock_cache.connect_redis.return_value = None
                mock_cache.close.return_value = None
                mock_cache_class.return_value = mock_cache
                
                with patch('custom_components.sure_finance.FinancialCalculator') as mock_calc_class:
                    mock_calc = MagicMock()
                    mock_calc_class.return_value = mock_calc
                    
                    with patch('custom_components.sure_finance.DataManager') as mock_dm_class:
                        mock_dm = MagicMock()
                        mock_dm_class.return_value = mock_dm
                        
                        # Setup entry
                        result = await async_setup_entry(mock_hass, mock_config_entry)
                        assert result is True
                        
                        # Verify entry data exists
                        assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
                        
                        # Step 3: Service setup
                        await async_setup_services(mock_hass, mock_config_entry)
                        
                        # Verify services are registered
                        assert mock_hass.services.async_register.call_count == 2
                        
                        # Step 4: Entry teardown
                        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
                        
                        result = await async_unload_entry(mock_hass, mock_config_entry)
                        assert result is True
                        
                        # Verify cleanup
                        mock_client.close.assert_called_once()
                        mock_cache.close.assert_called_once()
                        
                        # Verify entry data was removed
                        assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]
    
    @pytest.mark.asyncio
    async def test_multiple_entries_lifecycle(self, mock_hass):
        """Test lifecycle with multiple config entries."""
        # Create multiple config entries
        entry1 = ConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Sure Finance 1",
            data={CONF_API_KEY: "key1", "host": "https://app1.sure.am"},
            source="user",
            entry_id="entry1",
        )
        
        entry2 = ConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Sure Finance 2",
            data={CONF_API_KEY: "key2", "host": "https://app2.sure.am"},
            source="user",
            entry_id="entry2",
        )
        
        # Setup
        await async_setup(mock_hass, {})
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        with patch('custom_components.sure_finance.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect.return_value = None
            mock_client.get_accounts.return_value = []
            mock_client.close.return_value = None
            mock_client_class.return_value = mock_client
            
            with patch('custom_components.sure_finance.CacheManager') as mock_cache_class:
                mock_cache = AsyncMock()
                mock_cache.connect_redis.return_value = None
                mock_cache.close.return_value = None
                mock_cache_class.return_value = mock_cache
                
                with patch('custom_components.sure_finance.FinancialCalculator') as mock_calc_class:
                    mock_calc = MagicMock()
                    mock_calc_class.return_value = mock_calc
                    
                    with patch('custom_components.sure_finance.DataManager') as mock_dm_class:
                        mock_dm = MagicMock()
                        mock_dm_class.return_value = mock_dm
                        
                        # Setup both entries
                        result1 = await async_setup_entry(mock_hass, entry1)
                        result2 = await async_setup_entry(mock_hass, entry2)
                        
                        assert result1 is True
                        assert result2 is True
                        
                        # Verify both entries exist
                        assert "entry1" in mock_hass.data[DOMAIN]
                        assert "entry2" in mock_hass.data[DOMAIN]
                        
                        # Unload first entry
                        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
                        
                        with patch('custom_components.sure_finance.async_remove_services') as mock_remove_services:
                            result = await async_unload_entry(mock_hass, entry1)
                            assert result is True
                            
                            # Services should not be removed (entry2 still exists)
                            mock_remove_services.assert_not_called()
                            
                            # Only entry1 should be removed
                            assert "entry1" not in mock_hass.data[DOMAIN]
                            assert "entry2" in mock_hass.data[DOMAIN]
                            
                            # Unload second entry
                            result = await async_unload_entry(mock_hass, entry2)
                            assert result is True
                            
                            # Now services should be removed
                            mock_remove_services.assert_called_once_with(mock_hass)
                            
                            # All entries should be removed
                            assert "entry1" not in mock_hass.data[DOMAIN]
                            assert "entry2" not in mock_hass.data[DOMAIN]
