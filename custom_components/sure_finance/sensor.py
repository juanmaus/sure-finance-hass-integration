"""Home Assistant sensors for Sure Finance.

All values come from the coordinator payload, which is built from raw API dicts
(see coordinator.py); nothing here parses the API response itself.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_DOLLAR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_CURRENCY, DOMAIN
from .coordinator import SureFinanceDataCoordinator

_LOGGER = logging.getLogger(__name__)


class _BaseSensor(CoordinatorEntity[SureFinanceDataCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: SureFinanceDataCoordinator,
        sensor_type: str,
        name: str,
        icon: str = "mdi:cash",
        unit: str = CURRENCY_DOLLAR,
    ) -> None:
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._name = name
        self._icon = icon
        self._unit = unit

    @property
    def unique_id(self) -> str:
        return f"sure_finance_{self._sensor_type}"

    @property
    def name(self) -> str:
        return f"Sure Finance {self._name}"

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "sure_finance")},
            name="Sure Finance",
            manufacturer="Sure Finance",
            model="Financial Tracker",
        )

    @property
    def device_class(self) -> SensorDeviceClass:
        return SensorDeviceClass.MONETARY

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.TOTAL

    @property
    def native_unit_of_measurement(self) -> str:
        return self._unit

    @property
    def _summary(self) -> Dict[str, Any]:
        return (self.coordinator.data or {}).get("summary") or {}

    @property
    def _monthly(self) -> Dict[str, Any]:
        return (self.coordinator.data or {}).get("monthly_cashflow") or {}

    @property
    def _balances(self) -> List[Dict[str, Any]]:
        return (self.coordinator.data or {}).get("balances") or []


class NetWorthSensor(_BaseSensor):
    @property
    def native_value(self) -> float:
        return float(self._summary.get("net_worth") or 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "total_assets": self._summary.get("total_assets", 0.0),
            "total_liabilities": self._summary.get("total_liabilities", 0.0),
            "last_updated": self._summary.get("last_updated"),
        }


class CashflowSensor(_BaseSensor):
    @property
    def native_value(self) -> float:
        return float(self._summary.get("total_cashflow") or 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "monthly_income": self._monthly.get("total_income", 0.0),
            "income_by_category": self._monthly.get("income_by_category", {}),
        }


class OutflowSensor(_BaseSensor):
    @property
    def native_value(self) -> float:
        return float(self._summary.get("total_outflow") or 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "monthly_expenses": self._monthly.get("total_expenses", 0.0),
            "expenses_by_category": self._monthly.get("expenses_by_category", {}),
        }


class LiabilitySensor(_BaseSensor):
    @property
    def native_value(self) -> float:
        return float(self._summary.get("total_liabilities") or 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "liability_accounts": [
                {"name": b.get("account_name"), "balance": b.get("balance")}
                for b in self._balances
                if (b.get("classification") or "").lower() == "liability"
            ]
        }


class AccountBalanceSensor(_BaseSensor):
    def __init__(self, coordinator: SureFinanceDataCoordinator, account: Dict[str, Any]) -> None:
        super().__init__(
            coordinator,
            f"account_{account.get('account_id')}",
            f"Account {account.get('account_name')}",
            "mdi:bank-outline",
            account.get("currency") or CURRENCY_DOLLAR,
        )
        self._account_id = account.get("account_id")
        self._account_name = account.get("account_name")

    def _balance(self) -> Optional[Dict[str, Any]]:
        for b in self._balances:
            if b.get("account_id") == self._account_id:
                return b
        return None

    @property
    def native_value(self) -> float:
        return float((self._balance() or {}).get("balance") or 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {"account_name": self._account_name}
        balance = self._balance()
        if balance:
            attrs["classification"] = balance.get("classification")
            attrs["last_updated"] = balance.get("last_updated")
        return attrs


class MonthlySavingsRateSensor(_BaseSensor):
    def __init__(self, coordinator: SureFinanceDataCoordinator) -> None:
        super().__init__(
            coordinator, "monthly_savings_rate", "Monthly Savings Rate", "mdi:percent", "%"
        )

    @property
    def device_class(self) -> None:
        return None

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float:
        income = float(self._monthly.get("total_income") or 0)
        expenses = float(self._monthly.get("total_expenses") or 0)
        if income > 0:
            return round(((income - expenses) / income) * 100, 1)
        return 0.0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "monthly_income": self._monthly.get("total_income", 0.0),
            "monthly_expenses": self._monthly.get("total_expenses", 0.0),
            "monthly_savings": self._monthly.get("net_cashflow", 0.0),
        }


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Sure Finance sensors from a config entry."""
    coordinator: SureFinanceDataCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    currency: str = entry.data.get("currency", DEFAULT_CURRENCY)

    sensors: List[SensorEntity] = [
        NetWorthSensor(coordinator, "net_worth", "Net Worth", "mdi:bank", currency),
        MonthlySavingsRateSensor(coordinator),
    ]

    if entry.data.get("enable_cashflow_sensor", True):
        sensors.append(
            CashflowSensor(
                coordinator, "total_cashflow", "Total Cashflow", "mdi:cash-plus", currency
            )
        )
    if entry.data.get("enable_outflow_sensor", True):
        sensors.append(
            OutflowSensor(
                coordinator, "total_outflow", "Total Outflow", "mdi:cash-minus", currency
            )
        )
    if entry.data.get("enable_liability_sensor", True):
        sensors.append(
            LiabilitySensor(
                coordinator, "total_liability", "Total Liability", "mdi:bank-minus", currency
            )
        )

    if entry.data.get("enable_account_sensors", True):
        for balance in (coordinator.data or {}).get("balances", []):
            sensors.append(AccountBalanceSensor(coordinator, balance))

    async_add_entities(sensors)
