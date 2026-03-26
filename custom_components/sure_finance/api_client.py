"""Sure Finance API Client (integration copy)."""

# The content below is copied from sure-finance/src/api_client.py

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(APIError):
    pass


class RateLimitError(APIError):
    pass


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=25, ge=1, le=100)


class DateRangeParams(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SureFinanceClient:
    BASE_URL = "https://app.sure.am"
    DEFAULT_TIMEOUT = 30

    def __init__(self, api_key: str, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = ClientTimeout(total=timeout or self.DEFAULT_TIMEOUT)
        self._session: Optional[ClientSession] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        if not self._session:
            headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            self._session = ClientSession(headers=headers, timeout=self.timeout)

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    def _build_url(self, endpoint: str) -> str:
        return urljoin(self.base_url, endpoint)

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        if not self._session:
            await self.connect()
        url = self._build_url(endpoint)
        try:
            async with self._session.request(method, url, **kwargs) as response:
                data = await response.json() if response.content_length else {}
                if response.status in (200, 201):
                    return data
                if response.status == 401:
                    raise AuthenticationError("Authentication failed", status_code=401, details=data)
                if response.status == 429:
                    raise RateLimitError("Rate limit exceeded", status_code=429, details=data)
                error_msg = data.get("error", "Unknown error")
                raise APIError(f"API error: {error_msg}", status_code=response.status, details=data)
        except aiohttp.ClientError as e:
            raise APIError(f"Network error: {str(e)}")

    async def get_accounts(self, pagination: Optional[PaginationParams] = None) -> Dict[str, Any]:
        params = {}
        if pagination:
            params.update(pagination.model_dump(exclude_none=True))
        return await self._request("GET", "/api/v1/accounts", params=params)

    async def get_transactions(
        self,
        pagination: Optional[PaginationParams] = None,
        date_range: Optional[DateRangeParams] = None,
        account_id: Optional[str] = None,
        category_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        transaction_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        params = {}
        if pagination:
            params.update(pagination.model_dump(exclude_none=True))
        if date_range:
            if date_range.start_date:
                params["start_date"] = date_range.start_date.strftime("%Y-%m-%d")
            if date_range.end_date:
                params["end_date"] = date_range.end_date.strftime("%Y-%m-%d")
        if account_id:
            params["account_id"] = account_id
        if category_id:
            params["category_id"] = category_id
        if merchant_id:
            params["merchant_id"] = merchant_id
        if transaction_type:
            params["type"] = transaction_type
        if search:
            params["search"] = search
        return await self._request("GET", "/api/v1/transactions", params=params)

    async def get_category(self, category_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/api/v1/categories/{category_id}")

    async def get_categories(self, pagination: Optional[PaginationParams] = None, classification: Optional[str] = None, roots_only: bool = False, parent_id: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if pagination:
            params.update(pagination.model_dump(exclude_none=True))
        if classification:
            params["classification"] = classification
        if roots_only:
            params["roots_only"] = "true"
        if parent_id:
            params["parent_id"] = parent_id
        return await self._request("GET", "/api/v1/categories", params=params)

    async def get_merchants(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "/api/v1/merchants")

    async def get_tags(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "/api/v1/tags")

    async def get_all_pages(self, endpoint_func, per_page: int = 100, **kwargs) -> List[Dict[str, Any]]:
        all_items: List[Dict[str, Any]] = []
        page = 1
        while True:
            pagination = PaginationParams(page=page, per_page=per_page)
            result = await endpoint_func(pagination=pagination, **kwargs)
            if "transactions" in result:
                items = result["transactions"]
            elif "accounts" in result:
                items = result["accounts"]
            elif "categories" in result:
                items = result["categories"]
            elif "trades" in result:
                items = result["trades"]
            elif "holdings" in result:
                items = result["holdings"]
            elif "data" in result:
                items = result["data"]
            else:
                break
            all_items.extend(items)
            pagination_info = result.get("pagination") or result.get("meta")
            if not pagination_info:
                break
            total_pages = pagination_info.get("total_pages", 0)
            if page >= total_pages:
                break
            page += 1
        return all_items

