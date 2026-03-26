"""Tests for Sure Finance Config Flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult

from custom_components.sure_finance.api_client import AuthenticationError
from custom_components.sure_finance.config_flow import (
    DOMAIN,
    SCHEMA_USER,
    SureFinanceConfigFlow,
    validate_input,
)


class TestSureFinanceConfigFlow:
    """Test suite for SureFinanceConfigFlow."""
    
    @pytest.fixture
    def flow(self, mock_hass):
        """Create a test config flow instance."""
        flow = SureFinanceConfigFlow()
        flow.hass = mock_hass
        return flow
    
    def test_schema_validation(self):
        """Test the user input schema validation."""
        # Test valid input
        valid_input = {
            CONF_API_KEY: "test_api_key_123",
            "host": "https://app.sure.am",
            "update_interval": 300,
            "currency": "USD",
            "enable_cashflow_sensor": True,
            "enable_outflow_sensor": True,
            "enable_liability_sensor": True,
            "enable_account_sensors": True,
            "enable_transaction_sensors": True,
            "cache_duration": 3600,
        }
        
        # Should not raise an exception
        validated = SCHEMA_USER(valid_input)
        assert validated[CONF_API_KEY] == "test_api_key_123"
        assert validated["host"] == "https://app.sure.am"
        assert validated["update_interval"] == 300
        assert validated["currency"] == "USD"
        assert validated["cache_duration"] == 3600
    
    def test_schema_defaults(self):
        """Test schema default values."""
        # Test with minimal input
        minimal_input = {CONF_API_KEY: "test_key"}
        
        validated = SCHEMA_USER(minimal_input)
        
        # Verify defaults
        assert validated["host"] == "https://app.sure.am"
        assert validated["update_interval"] == 300
        assert validated["currency"] == "USD"
        assert validated["enable_cashflow_sensor"] is True
        assert validated["enable_outflow_sensor"] is True
        assert validated["enable_liability_sensor"] is True
        assert validated["enable_account_sensors"] is True
        assert validated["enable_transaction_sensors"] is True
        assert validated["cache_duration"] == 3600
    
    def test_schema_validation_errors(self):
        """Test schema validation with invalid input."""
        # Test missing required field
        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_USER({})
        
        # Test invalid update_interval (too low)
        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_USER({
                CONF_API_KEY: "test_key",
                "update_interval": 30  # Below minimum of 60
            })
        
        # Test invalid update_interval (too high)
        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_USER({
                CONF_API_KEY: "test_key",
                "update_interval": 4000  # Above maximum of 3600
            })
        
        # Test invalid cache_duration (too low)
        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_USER({
                CONF_API_KEY: "test_key",
                "cache_duration": 200  # Below minimum of 300
            })
        
        # Test invalid cache_duration (too high)
        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_USER({
                CONF_API_KEY: "test_key",
                "cache_duration": 100000  # Above maximum of 86400
            })
    
    @pytest.mark.asyncio
    async def test_validate_input_success(self, mock_hass):
        """Test successful input validation."""
        test_data = {
            CONF_API_KEY: "valid_api_key",
            "host": "https://test.sure.am"
        }
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_accounts.return_value = [{"id": "123", "name": "Test Account"}]
            mock_client.close.return_value = None
            
            result = await validate_input(mock_hass, test_data)
            
            assert result == {"title": "Sure Finance"}
            
            # Verify client was created with correct parameters
            mock_client_class.assert_called_once_with(
                api_key="valid_api_key",
                base_url="https://test.sure.am"
            )
            
            # Verify client methods were called
            mock_client.connect.assert_called_once()
            mock_client.get_accounts.assert_called_once()
            mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_input_auth_error(self, mock_hass):
        """Test input validation with authentication error."""
        test_data = {
            CONF_API_KEY: "invalid_api_key",
            "host": "https://test.sure.am"
        }
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_accounts.side_effect = AuthenticationError("Invalid API key")
            mock_client.close.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await validate_input(mock_hass, test_data)
            
            assert str(exc_info.value) == "invalid_auth"
    
    @pytest.mark.asyncio
    async def test_validate_input_connection_error(self, mock_hass):
        """Test input validation with connection error."""
        test_data = {
            CONF_API_KEY: "test_api_key",
            "host": "https://invalid.sure.am"
        }
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.side_effect = ConnectionError("Cannot connect")
            mock_client.close.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await validate_input(mock_hass, test_data)
            
            assert str(exc_info.value) == "cannot_connect"
    
    @pytest.mark.asyncio
    async def test_validate_input_with_base_url_fallback(self, mock_hass):
        """Test input validation with base_url field instead of host."""
        test_data = {
            CONF_API_KEY: "test_api_key",
            "base_url": "https://custom.sure.am"  # Using base_url instead of host
        }
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_accounts.return_value = []
            mock_client.close.return_value = None
            
            result = await validate_input(mock_hass, test_data)
            
            assert result == {"title": "Sure Finance"}
            
            # Verify client was created with base_url
            mock_client_class.assert_called_once_with(
                api_key="test_api_key",
                base_url="https://custom.sure.am"
            )
    
    @pytest.mark.asyncio
    async def test_async_step_user_no_input(self, flow):
        """Test user step with no input (initial form display)."""
        result = await flow.async_step_user()
        
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["data_schema"] == SCHEMA_USER
        assert result["errors"] == {}
        assert "api_key_url" in result["description_placeholders"]
    
    @pytest.mark.asyncio
    async def test_async_step_user_valid_input(self, flow):
        """Test user step with valid input."""
        user_input = {
            CONF_API_KEY: "valid_api_key",
            "host": "https://app.sure.am",
            "update_interval": 300,
            "currency": "USD"
        }
        
        with patch('custom_components.sure_finance.config_flow.validate_input') as mock_validate:
            mock_validate.return_value = {"title": "Sure Finance"}
            
            # Mock unique ID methods
            flow.async_set_unique_id = MagicMock()
            flow._abort_if_unique_id_configured = MagicMock()
            flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
            
            result = await flow.async_step_user(user_input)
            
            # Verify validation was called
            mock_validate.assert_called_once_with(flow.hass, user_input)
            
            # Verify unique ID was set
            expected_unique_id = f"sure_finance_{hash(user_input[CONF_API_KEY])}"
            flow.async_set_unique_id.assert_called_once_with(expected_unique_id)
            
            # Verify entry creation
            flow.async_create_entry.assert_called_once_with(
                title="Sure Finance",
                data=user_input
            )
    
    @pytest.mark.asyncio
    async def test_async_step_user_auth_error(self, flow):
        """Test user step with authentication error."""
        user_input = {
            CONF_API_KEY: "invalid_api_key",
            "host": "https://app.sure.am"
        }
        
        with patch('custom_components.sure_finance.config_flow.validate_input') as mock_validate:
            mock_validate.side_effect = ValueError("invalid_auth")
            
            result = await flow.async_step_user(user_input)
            
            assert result["type"] == "form"
            assert result["step_id"] == "user"
            assert result["errors"] == {"base": "invalid_auth"}
    
    @pytest.mark.asyncio
    async def test_async_step_user_connection_error(self, flow):
        """Test user step with connection error."""
        user_input = {
            CONF_API_KEY: "test_api_key",
            "host": "https://invalid.sure.am"
        }
        
        with patch('custom_components.sure_finance.config_flow.validate_input') as mock_validate:
            mock_validate.side_effect = ValueError("cannot_connect")
            
            result = await flow.async_step_user(user_input)
            
            assert result["type"] == "form"
            assert result["step_id"] == "user"
            assert result["errors"] == {"base": "cannot_connect"}
    
    @pytest.mark.asyncio
    async def test_async_step_user_unknown_error(self, flow):
        """Test user step with unknown error."""
        user_input = {
            CONF_API_KEY: "test_api_key",
            "host": "https://app.sure.am"
        }
        
        with patch('custom_components.sure_finance.config_flow.validate_input') as mock_validate:
            mock_validate.side_effect = Exception("Unexpected error")
            
            result = await flow.async_step_user(user_input)
            
            assert result["type"] == "form"
            assert result["step_id"] == "user"
            assert result["errors"] == {"base": "unknown"}
    
    @pytest.mark.asyncio
    async def test_async_step_user_duplicate_entry(self, flow):
        """Test user step with duplicate entry (same API key)."""
        user_input = {
            CONF_API_KEY: "existing_api_key",
            "host": "https://app.sure.am"
        }
        
        with patch('custom_components.sure_finance.config_flow.validate_input') as mock_validate:
            mock_validate.return_value = {"title": "Sure Finance"}
            
            # Mock unique ID methods to simulate existing entry
            flow.async_set_unique_id = MagicMock()
            flow._abort_if_unique_id_configured = MagicMock(
                side_effect=config_entries.AbortFlow("already_configured")
            )
            
            with pytest.raises(config_entries.AbortFlow) as exc_info:
                await flow.async_step_user(user_input)
            
            assert exc_info.value.reason == "already_configured"
    
    @pytest.mark.asyncio
    async def test_async_step_import(self, flow):
        """Test import step (YAML configuration import)."""
        import_data = {
            CONF_API_KEY: "imported_api_key",
            "host": "https://imported.sure.am",
            "update_interval": 600
        }
        
        with patch.object(flow, 'async_step_user') as mock_step_user:
            mock_step_user.return_value = {"type": "create_entry"}
            
            result = await flow.async_step_import(import_data)
            
            # Should delegate to user step
            mock_step_user.assert_called_once_with(import_data)
            assert result == {"type": "create_entry"}
    
    def test_flow_version(self, flow):
        """Test that flow has correct version."""
        assert flow.VERSION == 1
    
    def test_flow_domain(self, flow):
        """Test that flow has correct domain."""
        assert flow.domain == DOMAIN
        assert DOMAIN == "sure_finance"


class TestConfigFlowValidation:
    """Test suite for config flow validation scenarios."""
    
    @pytest.mark.asyncio
    async def test_api_key_variations(self, mock_hass):
        """Test validation with different API key formats."""
        test_cases = [
            "simple_key",
            "key-with-dashes",
            "key_with_underscores",
            "KeyWithMixedCase123",
            "very-long-api-key-with-many-characters-and-numbers-123456789",
            "key.with.dots",
            "key+with+plus",
        ]
        
        for api_key in test_cases:
            test_data = {CONF_API_KEY: api_key}
            
            with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = None
                mock_client.get_accounts.return_value = []
                mock_client.close.return_value = None
                
                result = await validate_input(mock_hass, test_data)
                assert result == {"title": "Sure Finance"}
    
    @pytest.mark.asyncio
    async def test_host_url_variations(self, mock_hass):
        """Test validation with different host URL formats."""
        test_cases = [
            "https://app.sure.am",
            "https://custom.sure.am",
            "https://api.sure.am:8080",
            "http://localhost:3000",
            "https://sure.am/api/v1",
        ]
        
        for host in test_cases:
            test_data = {
                CONF_API_KEY: "test_key",
                "host": host
            }
            
            with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                mock_client.connect.return_value = None
                mock_client.get_accounts.return_value = []
                mock_client.close.return_value = None
                
                result = await validate_input(mock_hass, test_data)
                assert result == {"title": "Sure Finance"}
                
                # Verify correct host was passed
                mock_client_class.assert_called_with(
                    api_key="test_key",
                    base_url=host
                )
    
    @pytest.mark.asyncio
    async def test_boundary_values(self, mock_hass):
        """Test validation with boundary values for numeric fields."""
        # Test minimum values
        min_values = {
            CONF_API_KEY: "test_key",
            "update_interval": 60,  # Minimum
            "cache_duration": 300,  # Minimum
        }
        
        validated = SCHEMA_USER(min_values)
        assert validated["update_interval"] == 60
        assert validated["cache_duration"] == 300
        
        # Test maximum values
        max_values = {
            CONF_API_KEY: "test_key",
            "update_interval": 3600,  # Maximum
            "cache_duration": 86400,  # Maximum
        }
        
        validated = SCHEMA_USER(max_values)
        assert validated["update_interval"] == 3600
        assert validated["cache_duration"] == 86400
    
    @pytest.mark.asyncio
    async def test_boolean_sensor_toggles(self, mock_hass):
        """Test validation with different sensor toggle combinations."""
        test_cases = [
            # All enabled
            {
                "enable_cashflow_sensor": True,
                "enable_outflow_sensor": True,
                "enable_liability_sensor": True,
                "enable_account_sensors": True,
                "enable_transaction_sensors": True,
            },
            # All disabled
            {
                "enable_cashflow_sensor": False,
                "enable_outflow_sensor": False,
                "enable_liability_sensor": False,
                "enable_account_sensors": False,
                "enable_transaction_sensors": False,
            },
            # Mixed
            {
                "enable_cashflow_sensor": True,
                "enable_outflow_sensor": False,
                "enable_liability_sensor": True,
                "enable_account_sensors": False,
                "enable_transaction_sensors": True,
            },
        ]
        
        for sensor_config in test_cases:
            test_data = {CONF_API_KEY: "test_key", **sensor_config}
            
            validated = SCHEMA_USER(test_data)
            
            for key, expected_value in sensor_config.items():
                assert validated[key] == expected_value
    
    @pytest.mark.asyncio
    async def test_currency_codes(self, mock_hass):
        """Test validation with different currency codes."""
        currency_codes = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"]
        
        for currency in currency_codes:
            test_data = {
                CONF_API_KEY: "test_key",
                "currency": currency
            }
            
            validated = SCHEMA_USER(test_data)
            assert validated["currency"] == currency


class TestConfigFlowErrorHandling:
    """Test suite for config flow error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_network_timeout_error(self, mock_hass):
        """Test handling of network timeout during validation."""
        test_data = {CONF_API_KEY: "test_key"}
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.side_effect = TimeoutError("Connection timeout")
            mock_client.close.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await validate_input(mock_hass, test_data)
            
            assert str(exc_info.value) == "cannot_connect"
    
    @pytest.mark.asyncio
    async def test_api_server_error(self, mock_hass):
        """Test handling of API server errors during validation."""
        test_data = {CONF_API_KEY: "test_key"}
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_accounts.side_effect = Exception("Internal server error")
            mock_client.close.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await validate_input(mock_hass, test_data)
            
            assert str(exc_info.value) == "cannot_connect"
    
    @pytest.mark.asyncio
    async def test_malformed_response_error(self, mock_hass):
        """Test handling of malformed API responses during validation."""
        test_data = {CONF_API_KEY: "test_key"}
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_accounts.side_effect = ValueError("Invalid JSON response")
            mock_client.close.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await validate_input(mock_hass, test_data)
            
            assert str(exc_info.value) == "cannot_connect"
    
    @pytest.mark.asyncio
    async def test_client_cleanup_on_error(self, mock_hass):
        """Test that client is properly cleaned up even when errors occur."""
        test_data = {CONF_API_KEY: "test_key"}
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_accounts.side_effect = AuthenticationError("Invalid key")
            mock_client.close.return_value = None
            
            with pytest.raises(ValueError):
                await validate_input(mock_hass, test_data)
            
            # Verify client.close() was called even after error
            mock_client.close.assert_called_once()


class TestConfigFlowIntegration:
    """Integration tests for config flow."""
    
    @pytest.mark.asyncio
    async def test_complete_flow_success(self, mock_hass):
        """Test complete successful configuration flow."""
        flow = SureFinanceConfigFlow()
        flow.hass = mock_hass
        
        # Mock Home Assistant methods
        flow.async_set_unique_id = MagicMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={
            "type": "create_entry",
            "title": "Sure Finance",
            "data": {}
        })
        
        user_input = {
            CONF_API_KEY: "valid_api_key_123",
            "host": "https://app.sure.am",
            "update_interval": 300,
            "currency": "USD",
            "enable_cashflow_sensor": True,
            "enable_outflow_sensor": True,
            "enable_liability_sensor": True,
            "enable_account_sensors": True,
            "cache_duration": 3600,
        }
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.connect.return_value = None
            mock_client.get_accounts.return_value = [
                {"id": "123", "name": "Test Account", "balance": "1000.00"}
            ]
            mock_client.close.return_value = None
            
            # Step 1: Show initial form
            result1 = await flow.async_step_user()
            assert result1["type"] == "form"
            assert result1["step_id"] == "user"
            
            # Step 2: Submit valid data
            result2 = await flow.async_step_user(user_input)
            
            # Verify successful completion
            flow.async_create_entry.assert_called_once_with(
                title="Sure Finance",
                data=user_input
            )
    
    @pytest.mark.asyncio
    async def test_complete_flow_with_retry(self, mock_hass):
        """Test configuration flow with error and retry."""
        flow = SureFinanceConfigFlow()
        flow.hass = mock_hass
        
        # Mock Home Assistant methods
        flow.async_set_unique_id = MagicMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={
            "type": "create_entry",
            "title": "Sure Finance",
            "data": {}
        })
        
        invalid_input = {
            CONF_API_KEY: "invalid_api_key",
            "host": "https://app.sure.am"
        }
        
        valid_input = {
            CONF_API_KEY: "valid_api_key",
            "host": "https://app.sure.am"
        }
        
        with patch('custom_components.sure_finance.config_flow.SureFinanceClient') as mock_client_class:
            # First attempt - authentication error
            mock_client_invalid = AsyncMock()
            mock_client_invalid.connect.return_value = None
            mock_client_invalid.get_accounts.side_effect = AuthenticationError("Invalid key")
            mock_client_invalid.close.return_value = None
            
            # Second attempt - success
            mock_client_valid = AsyncMock()
            mock_client_valid.connect.return_value = None
            mock_client_valid.get_accounts.return_value = []
            mock_client_valid.close.return_value = None
            
            mock_client_class.side_effect = [mock_client_invalid, mock_client_valid]
            
            # Step 1: Submit invalid data
            result1 = await flow.async_step_user(invalid_input)
            assert result1["type"] == "form"
            assert result1["errors"] == {"base": "invalid_auth"}
            
            # Step 2: Submit valid data
            result2 = await flow.async_step_user(valid_input)
            
            # Verify successful completion
            flow.async_create_entry.assert_called_once_with(
                title="Sure Finance",
                data=valid_input
            )
