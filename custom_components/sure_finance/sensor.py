"""Home Assistant sensor integration for Sure Finance."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_DOLLAR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .data_manager import DataManager
from .models import AccountBalance

logger = logging.getLogger(__name__)

DOMAIN = "sure_finance"


class SureFinanceDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Sure Finance data."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        data_manager: DataManager,
        update_interval: int
    ):
        """Initialize the data update coordinator."""
        self.data_manager = data_manager
        
        super().__init__(
            hass,
            logger,
            name="Sure Finance",
            update_interval=timedelta(seconds=update_interval),
        )
        
    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API."""
        try:
            # Get financial summary
            summary = await self.data_manager.get_financial_summary()
            
            # Get account balances
            accounts = await self.data_manager.get_accounts()
            balances = self.data_manager.calculator.get_account_balances(accounts)
            
            # Get monthly cashflow for current month
            now = datetime.utcnow()
            monthly_cashflow = await self.data_manager.get_monthly_cashflow(
                now.year,
                now.month
            )
            
            return {
                "summary": summary,
                "balances": balances,
                "monthly_cashflow": monthly_cashflow,
                "last_update": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error fetching Sure Finance data: {e}")
            raise


class SureFinanceBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Sure Finance."""
    
    def __init__(
        self,
        coordinator: SureFinanceDataUpdateCoordinator,
        sensor_type: str,
        name: str,
        icon: str = "mdi:cash",
        currency: str = CURRENCY_DOLLAR
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._name = name
        self._icon = icon
        self._currency = currency
        
    @property
    def unique_id(self) -> str:
        """Return unique ID."""
        return f"sure_finance_{self._sensor_type}"
        
    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Sure Finance {self._name}"
        
    @property
    def icon(self) -> str:
        """Return the icon."""
        return self._icon
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, "sure_finance")},
            name="Sure Finance",
            manufacturer="Sure Finance",
            model="Financial Tracker",
            sw_version="1.0.0",
        )
        
    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the device class."""
        return SensorDeviceClass.MONETARY
        
    @property
    def state_class(self) -> SensorStateClass:
        """Return the state class."""
        return SensorStateClass.TOTAL
        
    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self._currency


class CashflowSensor(SureFinanceBaseSensor):
    """Sensor for total cashflow (income)."""
    
    def __init__(self, coordinator: SureFinanceDataUpdateCoordinator, currency: str):
        super().__init__(
            coordinator,
            "total_cashflow",
            "Total Cashflow",
            "mdi:cash-plus",
            currency
        )
        
    @property
    def native_value(self) -> float:
        if self.coordinator.data and "summary" in self.coordinator.data:
            return float(self.coordinator.data["summary"].total_cashflow)
        return 0.0
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs = {}
        if self.coordinator.data and "monthly_cashflow" in self.coordinator.data:
            monthly = self.coordinator.data["monthly_cashflow"]
            attrs["monthly_income"] = float(monthly.total_income)
            attrs["income_by_category"] = {
                k: float(v) for k, v in monthly.income_by_category.items()
            }
        return attrs


class OutflowSensor(SureFinanceBaseSensor):
    """Sensor for total outflow (expenses)."""
    
    def __init__(self, coordinator: SureFinanceDataUpdateCoordinator, currency: str):
        super().__init__(
            coordinator,
            "total_outflow",
            "Total Outflow",
            "mdi:cash-minus",
            currency
        )
        
    @property
    def native_value(self) -> float:
        if self.coordinator.data and "summary" in self.coordinator.data:
            return float(self.coordinator.data["summary"].total_outflow)
        return 0.0
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs = {}
        if self.coordinator.data and "monthly_cashflow" in self.coordinator.data:
            monthly = self.coordinator.data["monthly_cashflow"]
            attrs["monthly_expenses"] = float(monthly.total_expenses)
            attrs["expenses_by_category"] = {
                k: float(v) for k, v in monthly.expenses_by_category.items()
            }
        return attrs


class LiabilitySensor(SureFinanceBaseSensor):
    """Sensor for total liabilities."""
    
    def __init__(self, coordinator: SureFinanceDataUpdateCoordinator, currency: str):
        super().__init__(
            coordinator,
            "total_liability",
            "Total Liability",
            "mdi:bank-minus",
            currency
        )
        
    @property
    def native_value(self) -> float:
        if self.coordinator.data and "summary" in self.coordinator.data:
            return float(self.coordinator.data["summary"].total_liabilities)
        return 0.0
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs = {}
        if self.coordinator.data and "balances" in self.coordinator.data:
            liability_accounts = [
                {
                    "name": b.account_name,
                    "balance": float(b.balance)
                }
                for b in self.coordinator.data["balances"]
                if b.classification.value == "liability"
            ]
            attrs["liability_accounts"] = liability_accounts
        return attrs


class NetWorthSensor(SureFinanceBaseSensor):
    """Sensor for net worth."""
    
    def __init__(self, coordinator: SureFinanceDataUpdateCoordinator, currency: str):
        super().__init__(
            coordinator,
            "net_worth",
            "Net Worth",
            "mdi:bank",
            currency
        )
        
    @property
    def native_value(self) -> float:
        if self.coordinator.data and "summary" in self.coordinator.data:
            return float(self.coordinator.data["summary"].net_worth)
        return 0.0
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs = {}
        if self.coordinator.data and "summary" in self.coordinator.data:
            summary = self.coordinator.data["summary"]
            attrs["total_assets"] = float(summary.total_assets)
            attrs["total_liabilities"] = float(summary.total_liabilities)
            attrs["last_updated"] = summary.last_updated.isoformat()
        return attrs


class AccountBalanceSensor(SureFinanceBaseSensor):
    """Sensor for individual account balance."""
    
    def __init__(
        self,
        coordinator: SureFinanceDataUpdateCoordinator,
        account: AccountBalance
    ):
        super().__init__(
            coordinator,
            f"account_{account.account_id}",
            f"Account {account.account_name}",
            "mdi:bank-outline",
            account.currency
        )
        self._account_id = account.account_id
        self._account_name = account.account_name
        
    @property
    def native_value(self) -> float:
        if self.coordinator.data and "balances" in self.coordinator.data:
            for balance in self.coordinator.data["balances"]:
                if balance.account_id == self._account_id:
                    return float(balance.balance)
        return 0.0
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs = {"account_name": self._account_name}
        if self.coordinator.data and "balances" in self.coordinator.data:
            for balance in self.coordinator.data["balances"]:
                if balance.account_id == self._account_id:
                    attrs["classification"] = balance.classification.value
                    attrs["last_updated"] = balance.last_updated.isoformat()
                    break
        return attrs


class MonthlySavingsRateSensor(SureFinanceBaseSensor):
    """Sensor for monthly savings rate."""
    
    def __init__(self, coordinator: SureFinanceDataUpdateCoordinator):
        super().__init__(
            coordinator,
            "monthly_savings_rate",
            "Monthly Savings Rate",
            "mdi:percent",
            "%"
        )
        
    @property
    def device_class(self) -> None:
        return None  # Percentage, not monetary
        
    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT
        
    @property
    def native_value(self) -> float:
        if self.coordinator.data and "monthly_cashflow" in self.coordinator.data:
            monthly = self.coordinator.data["monthly_cashflow"]
            if monthly.total_income > 0:
                savings = monthly.total_income - monthly.total_expenses
                rate = (savings / monthly.total_income) * 100
                return round(float(rate), 1)
        return 0.0
        
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs = {}
        if self.coordinator.data and "monthly_cashflow" in self.coordinator.data:
            monthly = self.coordinator.data["monthly_cashflow"]
            attrs["monthly_income"] = float(monthly.total_income)
            attrs["monthly_expenses"] = float(monthly.total_expenses)
            attrs["monthly_savings"] = float(monthly.net_cashflow)
        return attrs


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Sure Finance sensors."""
    data_manager = hass.data[DOMAIN][config_entry.entry_id]["data_manager"]
    config = config_entry.data
    
    coordinator = SureFinanceDataUpdateCoordinator(
        hass,
        data_manager,
        config.get("update_interval", 300)
    )
    
    await coordinator.async_config_entry_first_refresh()
    
    sensors = []
    currency = config.get("currency", CURRENCY_DOLLAR)
    
    if config.get("enable_cashflow_sensor", True):
        sensors.append(CashflowSensor(coordinator, currency))
        
    if config.get("enable_outflow_sensor", True):
        sensors.append(OutflowSensor(coordinator, currency))
        
    if config.get("enable_liability_sensor", True):
        sensors.append(LiabilitySensor(coordinator, currency))
        
    sensors.append(NetWorthSensor(coordinator, currency))
    sensors.append(MonthlySavingsRateSensor(coordinator))
    
    if config.get("enable_account_sensors", True) and "balances" in coordinator.data:
        for balance in coordinator.data["balances"]:
            sensors.append(AccountBalanceSensor(coordinator, balance))
    
    async_add_entities(sensors)
    
    hass.data[DOMAIN][config_entry.entry_id]["coordinator"] = coordinator
