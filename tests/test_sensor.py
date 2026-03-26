"""Tests for Sure Finance Sensor Platform."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CURRENCY_DOLLAR
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.sure_finance.models import (
    AccountBalance,
    AccountClassification,
    CashflowSummary,
    FinancialSummary,
)
from custom_components.sure_finance.sensor import (
    AccountBalanceSensor,
    CashflowSensor,
    LiabilitySensor,
    MonthlySavingsRateSensor,
    NetWorthSensor,
    OutflowSensor,
    SureFinanceBaseSensor,
    SureFinanceDataUpdateCoordinator,
    async_setup_entry,
)


class TestSureFinanceDataUpdateCoordinator:
    """Test suite for SureFinanceDataUpdateCoordinator."""
    
    @pytest.fixture
    def coordinator(self, mock_hass, mock_data_manager):
        """Create a test coordinator instance."""
        return SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
    
    def test_initialization(self, coordinator, mock_data_manager):
        """Test coordinator initialization."""
        assert coordinator.data_manager is mock_data_manager
        assert coordinator.name == "Sure Finance"
        assert coordinator.update_interval == timedelta(seconds=300)
    
    @pytest.mark.asyncio
    async def test_async_update_data_success(self, coordinator, mock_data_manager, sample_accounts):
        """Test successful data update."""
        # Setup mock data
        mock_summary = FinancialSummary(
            total_assets=Decimal("20000.00"),
            total_liabilities=Decimal("2500.00"),
            net_worth=Decimal("17500.00"),
            total_cashflow=Decimal("3000.00"),
            total_outflow=Decimal("500.00")
        )
        
        mock_balances = [
            AccountBalance(
                account_id=uuid4(),
                account_name="Test Account",
                balance=Decimal("5000.00"),
                currency="USD",
                classification=AccountClassification.ASSET,
                last_updated=datetime.utcnow()
            )
        ]
        
        mock_cashflow = CashflowSummary(
            period_start=datetime(2023, 6, 1),
            period_end=datetime(2023, 6, 30),
            total_income=Decimal("3000.00"),
            total_expenses=Decimal("500.00"),
            net_cashflow=Decimal("2500.00")
        )
        
        # Setup data manager mocks
        mock_data_manager.get_financial_summary.return_value = mock_summary
        mock_data_manager.get_accounts.return_value = sample_accounts
        mock_data_manager.calculator.get_account_balances.return_value = mock_balances
        mock_data_manager.get_monthly_cashflow.return_value = mock_cashflow
        
        result = await coordinator._async_update_data()
        
        # Verify data structure
        assert "summary" in result
        assert "balances" in result
        assert "monthly_cashflow" in result
        assert "last_update" in result
        
        assert result["summary"] == mock_summary
        assert result["balances"] == mock_balances
        assert result["monthly_cashflow"] == mock_cashflow
        assert isinstance(result["last_update"], datetime)
        
        # Verify method calls
        mock_data_manager.get_financial_summary.assert_called_once()
        mock_data_manager.get_accounts.assert_called_once()
        mock_data_manager.calculator.get_account_balances.assert_called_once_with(sample_accounts)
        mock_data_manager.get_monthly_cashflow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_update_data_error(self, coordinator, mock_data_manager):
        """Test data update with error."""
        # Setup data manager to raise error
        mock_data_manager.get_financial_summary.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            await coordinator._async_update_data()
        
        assert "API Error" in str(exc_info.value)


class TestSureFinanceBaseSensor:
    """Test suite for SureFinanceBaseSensor."""
    
    @pytest.fixture
    def base_sensor(self, mock_hass, mock_data_manager):
        """Create a test base sensor instance."""
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        return SureFinanceBaseSensor(
            coordinator=coordinator,
            sensor_type="test_sensor",
            name="Test Sensor",
            icon="mdi:test",
            currency="USD"
        )
    
    def test_initialization(self, base_sensor):
        """Test base sensor initialization."""
        assert base_sensor._sensor_type == "test_sensor"
        assert base_sensor._name == "Test Sensor"
        assert base_sensor._icon == "mdi:test"
        assert base_sensor._currency == "USD"
    
    def test_unique_id(self, base_sensor):
        """Test unique ID generation."""
        assert base_sensor.unique_id == "sure_finance_test_sensor"
    
    def test_name(self, base_sensor):
        """Test sensor name property."""
        assert base_sensor.name == "Sure Finance Test Sensor"
    
    def test_icon(self, base_sensor):
        """Test sensor icon property."""
        assert base_sensor.icon == "mdi:test"
    
    def test_device_info(self, base_sensor):
        """Test device info property."""
        device_info = base_sensor.device_info
        
        assert device_info["identifiers"] == {("sure_finance", "sure_finance")}
        assert device_info["name"] == "Sure Finance"
        assert device_info["manufacturer"] == "Sure Finance"
        assert device_info["model"] == "Financial Tracker"
        assert device_info["sw_version"] == "1.0.0"
    
    def test_device_class(self, base_sensor):
        """Test device class property."""
        assert base_sensor.device_class == SensorDeviceClass.MONETARY
    
    def test_state_class(self, base_sensor):
        """Test state class property."""
        assert base_sensor.state_class == SensorStateClass.TOTAL
    
    def test_native_unit_of_measurement(self, base_sensor):
        """Test unit of measurement property."""
        assert base_sensor.native_unit_of_measurement == "USD"
    
    def test_custom_currency(self, mock_hass, mock_data_manager):
        """Test base sensor with custom currency."""
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        sensor = SureFinanceBaseSensor(
            coordinator=coordinator,
            sensor_type="test_sensor",
            name="Test Sensor",
            currency="EUR"
        )
        
        assert sensor.native_unit_of_measurement == "EUR"
        assert sensor._currency == "EUR"


class TestCashflowSensor:
    """Test suite for CashflowSensor."""
    
    @pytest.fixture
    def cashflow_sensor(self, mock_hass, mock_data_manager):
        """Create a test cashflow sensor instance."""
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        return CashflowSensor(coordinator, "USD")
    
    def test_initialization(self, cashflow_sensor):
        """Test cashflow sensor initialization."""
        assert cashflow_sensor._sensor_type == "total_cashflow"
        assert cashflow_sensor._name == "Total Cashflow"
        assert cashflow_sensor._icon == "mdi:cash-plus"
        assert cashflow_sensor._currency == "USD"
    
    def test_native_value_with_data(self, cashflow_sensor):
        """Test native value with coordinator data."""
        # Setup coordinator data
        cashflow_sensor.coordinator.data = {
            "summary": FinancialSummary(
                total_cashflow=Decimal("3000.00")
            )
        }
        
        assert cashflow_sensor.native_value == 3000.0
    
    def test_native_value_no_data(self, cashflow_sensor):
        """Test native value with no coordinator data."""
        cashflow_sensor.coordinator.data = None
        assert cashflow_sensor.native_value == 0.0
        
        cashflow_sensor.coordinator.data = {}
        assert cashflow_sensor.native_value == 0.0
    
    def test_extra_state_attributes(self, cashflow_sensor):
        """Test extra state attributes."""
        # Setup coordinator data
        cashflow_sensor.coordinator.data = {
            "monthly_cashflow": CashflowSummary(
                period_start=datetime(2023, 6, 1),
                period_end=datetime(2023, 6, 30),
                total_income=Decimal("3500.00"),
                income_by_category={
                    "Salary": Decimal("3000.00"),
                    "Freelance": Decimal("500.00")
                }
            )
        }
        
        attributes = cashflow_sensor.extra_state_attributes
        
        assert attributes["monthly_income"] == 3500.0
        assert attributes["income_by_category"] == {
            "Salary": 3000.0,
            "Freelance": 500.0
        }
    
    def test_extra_state_attributes_no_data(self, cashflow_sensor):
        """Test extra state attributes with no data."""
        cashflow_sensor.coordinator.data = None
        attributes = cashflow_sensor.extra_state_attributes
        assert attributes == {}


class TestOutflowSensor:
    """Test suite for OutflowSensor."""
    
    @pytest.fixture
    def outflow_sensor(self, mock_hass, mock_data_manager):
        """Create a test outflow sensor instance."""
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        return OutflowSensor(coordinator, "USD")
    
    def test_initialization(self, outflow_sensor):
        """Test outflow sensor initialization."""
        assert outflow_sensor._sensor_type == "total_outflow"
        assert outflow_sensor._name == "Total Outflow"
        assert outflow_sensor._icon == "mdi:cash-minus"
    
    def test_native_value_with_data(self, outflow_sensor):
        """Test native value with coordinator data."""
        outflow_sensor.coordinator.data = {
            "summary": FinancialSummary(
                total_outflow=Decimal("1500.00")
            )
        }
        
        assert outflow_sensor.native_value == 1500.0
    
    def test_extra_state_attributes(self, outflow_sensor):
        """Test extra state attributes."""
        outflow_sensor.coordinator.data = {
            "monthly_cashflow": CashflowSummary(
                period_start=datetime(2023, 6, 1),
                period_end=datetime(2023, 6, 30),
                total_expenses=Decimal("1200.00"),
                expenses_by_category={
                    "Groceries": Decimal("400.00"),
                    "Utilities": Decimal("200.00"),
                    "Entertainment": Decimal("600.00")
                }
            )
        }
        
        attributes = outflow_sensor.extra_state_attributes
        
        assert attributes["monthly_expenses"] == 1200.0
        assert attributes["expenses_by_category"] == {
            "Groceries": 400.0,
            "Utilities": 200.0,
            "Entertainment": 600.0
        }


class TestLiabilitySensor:
    """Test suite for LiabilitySensor."""
    
    @pytest.fixture
    def liability_sensor(self, mock_hass, mock_data_manager):
        """Create a test liability sensor instance."""
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        return LiabilitySensor(coordinator, "USD")
    
    def test_initialization(self, liability_sensor):
        """Test liability sensor initialization."""
        assert liability_sensor._sensor_type == "total_liability"
        assert liability_sensor._name == "Total Liability"
        assert liability_sensor._icon == "mdi:bank-minus"
    
    def test_native_value_with_data(self, liability_sensor):
        """Test native value with coordinator data."""
        liability_sensor.coordinator.data = {
            "summary": FinancialSummary(
                total_liabilities=Decimal("5000.00")
            )
        }
        
        assert liability_sensor.native_value == 5000.0
    
    def test_extra_state_attributes(self, liability_sensor):
        """Test extra state attributes."""
        liability_sensor.coordinator.data = {
            "balances": [
                AccountBalance(
                    account_id=uuid4(),
                    account_name="Credit Card",
                    balance=Decimal("2500.00"),
                    currency="USD",
                    classification=AccountClassification.LIABILITY,
                    last_updated=datetime.utcnow()
                ),
                AccountBalance(
                    account_id=uuid4(),
                    account_name="Mortgage",
                    balance=Decimal("150000.00"),
                    currency="USD",
                    classification=AccountClassification.LIABILITY,
                    last_updated=datetime.utcnow()
                ),
                AccountBalance(
                    account_id=uuid4(),
                    account_name="Checking",
                    balance=Decimal("5000.00"),
                    currency="USD",
                    classification=AccountClassification.ASSET,
                    last_updated=datetime.utcnow()
                ),
            ]
        }
        
        attributes = liability_sensor.extra_state_attributes
        
        assert "liability_accounts" in attributes
        liability_accounts = attributes["liability_accounts"]
        
        # Should only include liability accounts
        assert len(liability_accounts) == 2
        
        # Verify account details
        account_names = [acc["name"] for acc in liability_accounts]
        assert "Credit Card" in account_names
        assert "Mortgage" in account_names
        assert "Checking" not in account_names


class TestNetWorthSensor:
    """Test suite for NetWorthSensor."""
    
    @pytest.fixture
    def net_worth_sensor(self, mock_hass, mock_data_manager):
        """Create a test net worth sensor instance."""
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        return NetWorthSensor(coordinator, "USD")
    
    def test_initialization(self, net_worth_sensor):
        """Test net worth sensor initialization."""
        assert net_worth_sensor._sensor_type == "net_worth"
        assert net_worth_sensor._name == "Net Worth"
        assert net_worth_sensor._icon == "mdi:bank"
    
    def test_native_value_with_data(self, net_worth_sensor):
        """Test native value with coordinator data."""
        net_worth_sensor.coordinator.data = {
            "summary": FinancialSummary(
                net_worth=Decimal("75000.00")
            )
        }
        
        assert net_worth_sensor.native_value == 75000.0
    
    def test_extra_state_attributes(self, net_worth_sensor):
        """Test extra state attributes."""
        last_updated = datetime.utcnow()
        net_worth_sensor.coordinator.data = {
            "summary": FinancialSummary(
                total_assets=Decimal("100000.00"),
                total_liabilities=Decimal("25000.00"),
                net_worth=Decimal("75000.00"),
                last_updated=last_updated
            )
        }
        
        attributes = net_worth_sensor.extra_state_attributes
        
        assert attributes["total_assets"] == 100000.0
        assert attributes["total_liabilities"] == 25000.0
        assert attributes["last_updated"] == last_updated.isoformat()


class TestAccountBalanceSensor:
    """Test suite for AccountBalanceSensor."""
    
    @pytest.fixture
    def account_balance_sensor(self, mock_hass, mock_data_manager):
        """Create a test account balance sensor instance."""
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        account = AccountBalance(
            account_id=uuid4(),
            account_name="Test Checking Account",
            balance=Decimal("5000.00"),
            currency="USD",
            classification=AccountClassification.ASSET,
            last_updated=datetime.utcnow()
        )
        
        return AccountBalanceSensor(coordinator, account)
    
    def test_initialization(self, account_balance_sensor):
        """Test account balance sensor initialization."""
        assert account_balance_sensor._account_name == "Test Checking Account"
        assert account_balance_sensor._name == "Account Test Checking Account"
        assert account_balance_sensor._icon == "mdi:bank-outline"
        assert account_balance_sensor._currency == "USD"
    
    def test_unique_id(self, account_balance_sensor):
        """Test unique ID includes account ID."""
        unique_id = account_balance_sensor.unique_id
        assert unique_id.startswith("sure_finance_account_")
        assert str(account_balance_sensor._account_id) in unique_id
    
    def test_native_value_with_data(self, account_balance_sensor):
        """Test native value with coordinator data."""
        account_balance_sensor.coordinator.data = {
            "balances": [
                AccountBalance(
                    account_id=account_balance_sensor._account_id,
                    account_name="Test Checking Account",
                    balance=Decimal("7500.00"),
                    currency="USD",
                    classification=AccountClassification.ASSET,
                    last_updated=datetime.utcnow()
                )
            ]
        }
        
        assert account_balance_sensor.native_value == 7500.0
    
    def test_native_value_account_not_found(self, account_balance_sensor):
        """Test native value when account is not found in data."""
        account_balance_sensor.coordinator.data = {
            "balances": [
                AccountBalance(
                    account_id=uuid4(),  # Different account ID
                    account_name="Other Account",
                    balance=Decimal("1000.00"),
                    currency="USD",
                    classification=AccountClassification.ASSET,
                    last_updated=datetime.utcnow()
                )
            ]
        }
        
        assert account_balance_sensor.native_value == 0.0
    
    def test_extra_state_attributes(self, account_balance_sensor):
        """Test extra state attributes."""
        last_updated = datetime.utcnow()
        account_balance_sensor.coordinator.data = {
            "balances": [
                AccountBalance(
                    account_id=account_balance_sensor._account_id,
                    account_name="Test Checking Account",
                    balance=Decimal("5000.00"),
                    currency="USD",
                    classification=AccountClassification.ASSET,
                    last_updated=last_updated
                )
            ]
        }
        
        attributes = account_balance_sensor.extra_state_attributes
        
        assert attributes["account_name"] == "Test Checking Account"
        assert attributes["classification"] == "asset"
        assert attributes["last_updated"] == last_updated.isoformat()


class TestMonthlySavingsRateSensor:
    """Test suite for MonthlySavingsRateSensor."""
    
    @pytest.fixture
    def savings_rate_sensor(self, mock_hass, mock_data_manager):
        """Create a test monthly savings rate sensor instance."""
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        return MonthlySavingsRateSensor(coordinator)
    
    def test_initialization(self, savings_rate_sensor):
        """Test savings rate sensor initialization."""
        assert savings_rate_sensor._sensor_type == "monthly_savings_rate"
        assert savings_rate_sensor._name == "Monthly Savings Rate"
        assert savings_rate_sensor._icon == "mdi:percent"
        assert savings_rate_sensor._currency == "%"
    
    def test_device_class_override(self, savings_rate_sensor):
        """Test that device class is overridden for percentage sensor."""
        assert savings_rate_sensor.device_class is None
    
    def test_state_class_override(self, savings_rate_sensor):
        """Test that state class is overridden for measurement."""
        assert savings_rate_sensor.state_class == SensorStateClass.MEASUREMENT
    
    def test_native_value_with_data(self, savings_rate_sensor):
        """Test native value calculation with coordinator data."""
        savings_rate_sensor.coordinator.data = {
            "monthly_cashflow": CashflowSummary(
                period_start=datetime(2023, 6, 1),
                period_end=datetime(2023, 6, 30),
                total_income=Decimal("5000.00"),
                total_expenses=Decimal("3000.00")
            )
        }
        
        # Savings rate = (5000 - 3000) / 5000 * 100 = 40%
        assert savings_rate_sensor.native_value == 40.0
    
    def test_native_value_zero_income(self, savings_rate_sensor):
        """Test native value with zero income."""
        savings_rate_sensor.coordinator.data = {
            "monthly_cashflow": CashflowSummary(
                period_start=datetime(2023, 6, 1),
                period_end=datetime(2023, 6, 30),
                total_income=Decimal("0.00"),
                total_expenses=Decimal("1000.00")
            )
        }
        
        assert savings_rate_sensor.native_value == 0.0
    
    def test_native_value_no_data(self, savings_rate_sensor):
        """Test native value with no coordinator data."""
        savings_rate_sensor.coordinator.data = None
        assert savings_rate_sensor.native_value == 0.0
    
    def test_extra_state_attributes(self, savings_rate_sensor):
        """Test extra state attributes."""
        savings_rate_sensor.coordinator.data = {
            "monthly_cashflow": CashflowSummary(
                period_start=datetime(2023, 6, 1),
                period_end=datetime(2023, 6, 30),
                total_income=Decimal("4000.00"),
                total_expenses=Decimal("2500.00"),
                net_cashflow=Decimal("1500.00")
            )
        }
        
        attributes = savings_rate_sensor.extra_state_attributes
        
        assert attributes["monthly_income"] == 4000.0
        assert attributes["monthly_expenses"] == 2500.0
        assert attributes["monthly_savings"] == 1500.0


class TestAsyncSetupEntry:
    """Test suite for async_setup_entry function."""
    
    @pytest.mark.asyncio
    async def test_setup_entry_all_sensors_enabled(self, mock_hass, mock_config_entry):
        """Test setup with all sensors enabled."""
        # Mock data manager and coordinator
        mock_data_manager = AsyncMock()
        mock_hass.data = {
            "sure_finance": {
                mock_config_entry.entry_id: {
                    "data_manager": mock_data_manager
                }
            }
        }
        
        # Mock coordinator data
        mock_coordinator_data = {
            "summary": FinancialSummary(),
            "balances": [
                AccountBalance(
                    account_id=uuid4(),
                    account_name="Test Account",
                    balance=Decimal("1000.00"),
                    currency="USD",
                    classification=AccountClassification.ASSET,
                    last_updated=datetime.utcnow()
                )
            ],
            "monthly_cashflow": CashflowSummary(
                period_start=datetime(2023, 6, 1),
                period_end=datetime(2023, 6, 30)
            ),
            "last_update": datetime.utcnow()
        }
        
        mock_async_add_entities = AsyncMock()
        
        with patch('custom_components.sure_finance.sensor.SureFinanceDataUpdateCoordinator') as mock_coordinator_class:
            mock_coordinator = AsyncMock()
            mock_coordinator.data = mock_coordinator_data
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Verify coordinator was created
            mock_coordinator_class.assert_called_once_with(
                mock_hass,
                mock_data_manager,
                300  # default update_interval
            )
            
            # Verify first refresh was called
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()
            
            # Verify sensors were added
            mock_async_add_entities.assert_called_once()
            added_sensors = mock_async_add_entities.call_args[0][0]
            
            # Should have all sensors enabled by default
            sensor_types = [sensor.__class__.__name__ for sensor in added_sensors]
            assert "CashflowSensor" in sensor_types
            assert "OutflowSensor" in sensor_types
            assert "LiabilitySensor" in sensor_types
            assert "NetWorthSensor" in sensor_types
            assert "MonthlySavingsRateSensor" in sensor_types
            assert "AccountBalanceSensor" in sensor_types
            
            # Verify coordinator was stored
            assert mock_hass.data["sure_finance"][mock_config_entry.entry_id]["coordinator"] == mock_coordinator
    
    @pytest.mark.asyncio
    async def test_setup_entry_sensors_disabled(self, mock_hass, mock_config_entry):
        """Test setup with some sensors disabled."""
        # Modify config to disable some sensors
        mock_config_entry.data.update({
            "enable_cashflow_sensor": False,
            "enable_outflow_sensor": False,
            "enable_liability_sensor": False,
            "enable_account_sensors": False,
        })
        
        mock_data_manager = AsyncMock()
        mock_hass.data = {
            "sure_finance": {
                mock_config_entry.entry_id: {
                    "data_manager": mock_data_manager
                }
            }
        }
        
        mock_coordinator_data = {
            "summary": FinancialSummary(),
            "balances": [],
            "monthly_cashflow": CashflowSummary(
                period_start=datetime(2023, 6, 1),
                period_end=datetime(2023, 6, 30)
            ),
            "last_update": datetime.utcnow()
        }
        
        mock_async_add_entities = AsyncMock()
        
        with patch('custom_components.sure_finance.sensor.SureFinanceDataUpdateCoordinator') as mock_coordinator_class:
            mock_coordinator = AsyncMock()
            mock_coordinator.data = mock_coordinator_data
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Verify sensors were added
            added_sensors = mock_async_add_entities.call_args[0][0]
            
            # Should only have enabled sensors
            sensor_types = [sensor.__class__.__name__ for sensor in added_sensors]
            assert "CashflowSensor" not in sensor_types
            assert "OutflowSensor" not in sensor_types
            assert "LiabilitySensor" not in sensor_types
            assert "NetWorthSensor" in sensor_types  # Always enabled
            assert "MonthlySavingsRateSensor" in sensor_types  # Always enabled
            assert "AccountBalanceSensor" not in sensor_types
    
    @pytest.mark.asyncio
    async def test_setup_entry_custom_currency(self, mock_hass, mock_config_entry):
        """Test setup with custom currency."""
        # Modify config to use EUR
        mock_config_entry.data.update({
            "currency": "EUR"
        })
        
        mock_data_manager = AsyncMock()
        mock_hass.data = {
            "sure_finance": {
                mock_config_entry.entry_id: {
                    "data_manager": mock_data_manager
                }
            }
        }
        
        mock_coordinator_data = {
            "summary": FinancialSummary(),
            "balances": [],
            "monthly_cashflow": CashflowSummary(
                period_start=datetime(2023, 6, 1),
                period_end=datetime(2023, 6, 30)
            ),
            "last_update": datetime.utcnow()
        }
        
        mock_async_add_entities = AsyncMock()
        
        with patch('custom_components.sure_finance.sensor.SureFinanceDataUpdateCoordinator') as mock_coordinator_class:
            mock_coordinator = AsyncMock()
            mock_coordinator.data = mock_coordinator_data
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Verify sensors were created with EUR currency
            added_sensors = mock_async_add_entities.call_args[0][0]
            
            # Find a monetary sensor to check currency
            net_worth_sensor = next(
                sensor for sensor in added_sensors 
                if isinstance(sensor, NetWorthSensor)
            )
            assert net_worth_sensor._currency == "EUR"
    
    @pytest.mark.asyncio
    async def test_setup_entry_custom_update_interval(self, mock_hass, mock_config_entry):
        """Test setup with custom update interval."""
        # Modify config to use custom update interval
        mock_config_entry.data.update({
            "update_interval": 600
        })
        
        mock_data_manager = AsyncMock()
        mock_hass.data = {
            "sure_finance": {
                mock_config_entry.entry_id: {
                    "data_manager": mock_data_manager
                }
            }
        }
        
        mock_async_add_entities = AsyncMock()
        
        with patch('custom_components.sure_finance.sensor.SureFinanceDataUpdateCoordinator') as mock_coordinator_class:
            mock_coordinator = AsyncMock()
            mock_coordinator.data = {}
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator_class.return_value = mock_coordinator
            
            await async_setup_entry(mock_hass, mock_config_entry, mock_async_add_entities)
            
            # Verify coordinator was created with custom update interval
            mock_coordinator_class.assert_called_once_with(
                mock_hass,
                mock_data_manager,
                600  # custom update_interval
            )


class TestSensorIntegration:
    """Integration tests for sensor platform."""
    
    @pytest.mark.asyncio
    async def test_complete_sensor_data_flow(self, mock_hass, mock_data_manager):
        """Test complete data flow from coordinator to sensors."""
        # Setup coordinator
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        # Setup mock data
        mock_summary = FinancialSummary(
            total_assets=Decimal("100000.00"),
            total_liabilities=Decimal("25000.00"),
            net_worth=Decimal("75000.00"),
            total_cashflow=Decimal("5000.00"),
            total_outflow=Decimal("3000.00")
        )
        
        mock_cashflow = CashflowSummary(
            period_start=datetime(2023, 6, 1),
            period_end=datetime(2023, 6, 30),
            total_income=Decimal("5000.00"),
            total_expenses=Decimal("3000.00"),
            net_cashflow=Decimal("2000.00")
        )
        
        # Setup coordinator data
        coordinator.data = {
            "summary": mock_summary,
            "monthly_cashflow": mock_cashflow,
            "balances": [],
            "last_update": datetime.utcnow()
        }
        
        # Create sensors
        sensors = [
            NetWorthSensor(coordinator, "USD"),
            CashflowSensor(coordinator, "USD"),
            OutflowSensor(coordinator, "USD"),
            MonthlySavingsRateSensor(coordinator)
        ]
        
        # Test sensor values
        assert sensors[0].native_value == 75000.0  # Net Worth
        assert sensors[1].native_value == 5000.0   # Cashflow
        assert sensors[2].native_value == 3000.0   # Outflow
        assert sensors[3].native_value == 40.0     # Savings Rate (2000/5000 * 100)
        
        # Test sensor attributes
        net_worth_attrs = sensors[0].extra_state_attributes
        assert net_worth_attrs["total_assets"] == 100000.0
        assert net_worth_attrs["total_liabilities"] == 25000.0
        
        savings_attrs = sensors[3].extra_state_attributes
        assert savings_attrs["monthly_income"] == 5000.0
        assert savings_attrs["monthly_expenses"] == 3000.0
        assert savings_attrs["monthly_savings"] == 2000.0
    
    @pytest.mark.asyncio
    async def test_sensor_error_handling(self, mock_hass, mock_data_manager):
        """Test sensor behavior when coordinator has errors."""
        coordinator = SureFinanceDataUpdateCoordinator(
            hass=mock_hass,
            data_manager=mock_data_manager,
            update_interval=300
        )
        
        # Setup coordinator with no data (simulating error state)
        coordinator.data = None
        
        # Create sensors
        sensors = [
            NetWorthSensor(coordinator, "USD"),
            CashflowSensor(coordinator, "USD"),
            MonthlySavingsRateSensor(coordinator)
        ]
        
        # All sensors should handle missing data gracefully
        assert sensors[0].native_value == 0.0
        assert sensors[1].native_value == 0.0
        assert sensors[2].native_value == 0.0
        
        # Attributes should be empty or safe defaults
        assert sensors[0].extra_state_attributes == {}
        assert sensors[1].extra_state_attributes == {}
        assert sensors[2].extra_state_attributes == {}
