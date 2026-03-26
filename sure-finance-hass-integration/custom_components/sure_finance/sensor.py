"""Home Assistant sensors for Sure Finance (no cache).

Coordinator fetches data directly from the API on each update.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_DOLLAR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from . import DOMAIN
from .api_client import SureFinanceClient
from .financial_calculator import (
    calculate_financial_summary,
    get_account_balances,
    calculate_monthly_cashflow,
    calculate_monthly_trends,
)

_LOGGER = logging.getLogger(__name__)


class SureFinanceDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: SureFinanceClient, currency: str, update_interval_s: int):
        self.client = client
        self.currency = currency
        super().__init__(
            hass,
            _LOGGER,
            name="Sure Finance",
            update_interval=timedelta(seconds=update_interval_s),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        # Fetch accounts and recent transactions directly from API
        accounts = await self.client.get_all_pages(self.client.get_accounts, per_page=100)

        # Last 30 days transactions
        now = datetime.utcnow()
        start = now - timedelta(days=30)
        all_txs = await self.client.get_all_pages(
            self.client.get_transactions,
            per_page=100,
            start_date=start,
            end_date=now,
        )

        summary = calculate_financial_summary(accounts, all_txs, self.currency)
        balances = get_account_balances(accounts, self.currency)
        monthly = calculate_monthly_cashflow(all_txs, now.replace(day=1), now, self.currency)
        trends = calculate_monthly_trends(all_txs, months=12, currency=self.currency)

        return {
            "summary": summary,
            "balances": balances,
            "monthly_cashflow": monthly,
            "trends": trends,
            "last_update": datetime.utcnow().isoformat(),
        }


class _BaseSensor(CoordinatorEntity[SureFinanceDataCoordinator], SensorEntity):
    def __init__(self, coordinator: SureFinanceDataCoordinator, sensor_type: str, name: str, icon: str = "mdi:cash", unit: str = CURRENCY_DOLLAR):
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
            sw_version="1.0.0",
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


class NetWorthSensor(_BaseSensor):
    @property
    def native_value(self) -> float:
        data = self.coordinator.data or {}
        return float((data.get("summary") or {}).get("net_worth") or 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        s = (self.coordinator.data or {}).get("summary") or {}
        return {
            "total_assets": s.get("total_assets", 0.0),
            "total_liabilities": s.get("total_liabilities", 0.0),
            "last_updated": s.get("last_updated"),
        }


class CashflowSensor(_BaseSensor):
    @property
    def native_value(self) -> float:
        data = self.coordinator.data or {}
        return float((data.get("summary") or {}).get("total_cashflow") or 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        m = (self.coordinator.data or {}).get("monthly_cashflow") or {}
        return {
            "monthly_income": m.get("total_income", 0.0),
            "income_by_category": m.get("income_by_category", {}),
        }


class OutflowSensor(_BaseSensor):
    @property
    def native_value(self) -> float:
        data = self.coordinator.data or {}
        return float((data.get("summary") or {}).get("total_outflow") or 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        m = (self.coordinator.data or {}).get("monthly_cashflow") or {}
        return {
            "monthly_expenses": m.get("total_expenses", 0.0),
            "expenses_by_category": m.get("expenses_by_category", {}),
        }


class LiabilitySensor(_BaseSensor):
    @property
    def native_value(self) -> float:
        data = self.coordinator.data or {}
        return float((data.get("summary") or {}).get("total_liabilities") or 0)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        balances: List[Dict[str, Any]] = (self.coordinator.data or {}).get("balances") or []
        liab = [
            {"name": b.get("account_name"), "balance": b.get("balance")}
            for b in balances
            if (b.get("classification") or "").lower() == "liability"
        ]
        return {"liability_accounts": liab}


class AccountBalanceSensor(_BaseSensor):
    def __init__(self, coordinator: SureFinanceDataCoordinator, account: Dict[str, Any]):
        super().__init__(
            coordinator,
            f"account_{account.get('account_id')}",
            f"Account {account.get('account_name')}",
            "mdi:bank-outline",
            account.get("currency") or CURRENCY_DOLLAR,
        )
        self._account_id = account.get("account_id")
        self._account_name = account.get("account_name")

    @property
    def native_value(self) -> float:
        balances: List[Dict[str, Any]] = (self.coordinator.data or {}).get("balances") or []
        for b in balances:
            if b.get("account_id") == self._account_id:
                return float(b.get("balance") or 0)
        return 0.0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        balances: List[Dict[str, Any]] = (self.coordinator.data or {}).get("balances") or []
        attrs = {"account_name": self._account_name}
        for b in balances:
            if b.get("account_id") == self._account_id:
                attrs["classification"] = b.get("classification")
                attrs["last_updated"] = b.get("last_updated")
                break
        return attrs


class MonthlySavingsRateSensor(_BaseSensor):
    def __init__(self, coordinator: SureFinanceDataCoordinator):
        super().__init__(coordinator, "monthly_savings_rate", "Monthly Savings Rate", "mdi:percent", "%")

    @property
    def device_class(self) -> None:
        return None

    @property
    def state_class(self) -> SensorStateClass:
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float:
        m = (self.coordinator.data or {}).get("monthly_cashflow") or {}
        inc = float(m.get("total_income") or 0)
        exp = float(m.get("total_expenses") or 0)
        if inc > 0:
            return round(((inc - exp) / inc) * 100, 1)
        return 0.0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        m = (self.coordinator.data or {}).get("monthly_cashflow") or {}
        return {
            "monthly_income": m.get("total_income", 0.0),
            "monthly_expenses": m.get("total_expenses", 0.0),
            "monthly_savings": m.get("net_cashflow", 0.0),
        }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    client: SureFinanceClient = data["api_client"]
    currency: str = entry.data.get("currency", CURRENCY_DOLLAR)

    coordinator = SureFinanceDataCoordinator(
        hass,
        client,
        currency,
        update_interval_s=entry.data.get("update_interval", 300),
    )

    await coordinator.async_config_entry_first_refresh()

    sensors: List[SensorEntity] = []
    # Always include these
    sensors.append(NetWorthSensor(coordinator, "net_worth", "Net Worth", "mdi:bank", currency))
    sensors.append(CashflowSensor(coordinator, "total_cashflow", "Total Cashflow", "mdi:cash-plus", currency))
    sensors.append(OutflowSensor(coordinator, "total_outflow", "Total Outflow", "mdi:cash-minus", currency))
    sensors.append(LiabilitySensor(coordinator, "total_liability", "Total Liability", "mdi:bank-minus", currency))
    sensors.append(MonthlySavingsRateSensor(coordinator))

    # Per-account sensors if enabled
    if entry.data.get("enable_account_sensors", True):
        for b in (coordinator.data or {}).get("balances", []):
            sensors.append(AccountBalanceSensor(coordinator, b))

    async_add_entities(sensors)

    # Store coordinator for service
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator
