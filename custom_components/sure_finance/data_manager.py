"""Data management and synchronization (integration copy)."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .api_client import SureFinanceClient, PaginationParams, DateRangeParams
from .cache_manager import CacheManager
from .financial_calculator import FinancialCalculator
from .models import (
    Account,
    Transaction,
    Category,
    Merchant,
    Tag,
    FinancialSummary,
    CashflowSummary
)

logger = logging.getLogger(__name__)


class DataManager:
    def __init__(
        self,
        api_client: SureFinanceClient,
        cache_manager: CacheManager,
        calculator: FinancialCalculator,
        update_interval: int = 300
    ):
        self.api_client = api_client
        self.cache = cache_manager
        self.calculator = calculator
        self.update_interval = update_interval
        self._last_updates: Dict[str, datetime] = {}

    async def get_accounts(self, force_refresh: bool = False) -> List[Account]:
        cache_key = self.cache.account_key()
        if not force_refresh:
            cached = await self.cache.get(cache_key, namespace="accounts")
            if cached:
                return [Account(**acc) for acc in cached]
        try:
            logger.info("Fetching accounts from API")
            all_accounts = await self.api_client.get_all_pages(
                self.api_client.get_accounts,
                per_page=100
            )
            await self.cache.set(cache_key, [acc for acc in all_accounts], ttl=self.update_interval, namespace="accounts")
            self._last_updates["accounts"] = datetime.utcnow()
            return [Account(**acc) for acc in all_accounts]
        except Exception as e:
            logger.error(f"Failed to fetch accounts: {e}")
            cached = await self.cache.get(cache_key, namespace="accounts")
            if cached:
                return [Account(**acc) for acc in cached]
            raise

    async def get_transactions(self, days: int = 30, account_id: Optional[str] = None, force_refresh: bool = False) -> List[Transaction]:
        cache_key = self.cache.transaction_key(account_id)
        if not force_refresh:
            cached = await self.cache.get(cache_key, namespace="transactions")
            if cached:
                return [Transaction(**tx) for tx in cached]
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        date_range = DateRangeParams(start_date=start_date, end_date=end_date)
        try:
            logger.info(f"Fetching transactions from API (last {days} days)")
            all_transactions = await self.api_client.get_all_pages(
                self.api_client.get_transactions,
                per_page=100,
                date_range=date_range,
                account_id=account_id
            )
            await self.cache.set(cache_key, [tx for tx in all_transactions], ttl=self.update_interval, namespace="transactions")
            self._last_updates["transactions"] = datetime.utcnow()
            return [Transaction(**tx) for tx in all_transactions]
        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            cached = await self.cache.get(cache_key, namespace="transactions")
            if cached:
                return [Transaction(**tx) for tx in cached]
            raise

    async def get_categories(self, force_refresh: bool = False) -> List[Category]:
        cache_key = "categories:all"
        if not force_refresh:
            cached = await self.cache.get(cache_key, namespace="metadata")
            if cached:
                return [Category(**cat) for cat in cached]
        try:
            logger.info("Fetching categories from API")
            all_categories = await self.api_client.get_all_pages(self.api_client.get_categories, per_page=100)
            await self.cache.set(cache_key, [cat for cat in all_categories], ttl=86400, namespace="metadata")
            return [Category(**cat) for cat in all_categories]
        except Exception as e:
            logger.error(f"Failed to fetch categories: {e}")
            cached = await self.cache.get(cache_key, namespace="metadata")
            if cached:
                return [Category(**cat) for cat in cached]
            raise

    async def get_merchants(self, force_refresh: bool = False) -> List[Merchant]:
        cache_key = "merchants:all"
        if not force_refresh:
            cached = await self.cache.get(cache_key, namespace="metadata")
            if cached:
                return [Merchant(**m) for m in cached]
        try:
            logger.info("Fetching merchants from API")
            merchants = await self.api_client.get_merchants()
            await self.cache.set(cache_key, merchants, ttl=86400, namespace="metadata")
            return [Merchant(**m) for m in merchants]
        except Exception as e:
            logger.error(f"Failed to fetch merchants: {e}")
            cached = await self.cache.get(cache_key, namespace="metadata")
            if cached:
                return [Merchant(**m) for m in cached]
            raise

    async def get_tags(self, force_refresh: bool = False) -> List[Tag]:
        cache_key = "tags:all"
        if not force_refresh:
            cached = await self.cache.get(cache_key, namespace="metadata")
            if cached:
                return [Tag(**t) for t in cached]
        try:
            logger.info("Fetching tags from API")
            tags = await self.api_client.get_tags()
            await self.cache.set(cache_key, tags, ttl=86400, namespace="metadata")
            return [Tag(**t) for t in tags]
        except Exception as e:
            logger.error(f"Failed to fetch tags: {e}")
            cached = await self.cache.get(cache_key, namespace="metadata")
            if cached:
                return [Tag(**t) for t in cached]
            raise

    async def get_financial_summary(self, force_refresh: bool = False) -> FinancialSummary:
        cache_key = self.cache.summary_key()
        if not force_refresh:
            cached = await self.cache.get(cache_key, namespace="summaries")
            if cached:
                return FinancialSummary(**cached)
        accounts = await self.get_accounts(force_refresh)
        transactions = await self.get_transactions(days=30, force_refresh=force_refresh)
        summary = self.calculator.calculate_financial_summary(accounts, transactions)
        await self.cache.set(cache_key, summary.model_dump(), ttl=self.update_interval, namespace="summaries")
        return summary

    async def get_monthly_cashflow(self, year: int, month: int, force_refresh: bool = False) -> CashflowSummary:
        cache_key = self.cache.cashflow_key(year, month)
        if not force_refresh:
            cached = await self.cache.get(cache_key, namespace="cashflow")
            if cached:
                return CashflowSummary(**cached)
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        date_range = DateRangeParams(start_date=start_date, end_date=end_date)
        transactions = await self.api_client.get_all_pages(self.api_client.get_transactions, per_page=100, date_range=date_range)
        transaction_models = [Transaction(**tx) for tx in transactions]
        summary = self.calculator.calculate_cashflow_summary(transaction_models, start_date, end_date)
        await self.cache.set(cache_key, summary.model_dump(), ttl=86400, namespace="cashflow")
        return summary

    async def sync_all_data(self):
        logger.info("Starting full data sync")
        try:
            await asyncio.gather(
                self.get_accounts(force_refresh=True),
                self.get_categories(force_refresh=True),
                self.get_merchants(force_refresh=True),
                self.get_tags(force_refresh=True)
            )
            await self.get_transactions(days=90, force_refresh=True)
            await self.get_financial_summary(force_refresh=True)
            logger.info("Full data sync completed")
        except Exception as e:
            logger.error(f"Error during data sync: {e}")
            raise

    def needs_update(self, data_type: str) -> bool:
        last_update = self._last_updates.get(data_type)
        if not last_update:
            return True
        elapsed = (datetime.utcnow() - last_update).total_seconds()
        return elapsed >= self.update_interval

    async def periodic_sync(self):
        while True:
            try:
                tasks = []
                if self.needs_update("accounts"):
                    tasks.append(self.get_accounts(force_refresh=True))
                if self.needs_update("transactions"):
                    tasks.append(self.get_transactions(days=30, force_refresh=True))
                if tasks:
                    await asyncio.gather(*tasks)
                    await self.get_financial_summary(force_refresh=True)
                self.cache.cleanup_expired()
            except Exception as e:
                logger.error(f"Error in periodic sync: {e}")
            await asyncio.sleep(self.update_interval)
