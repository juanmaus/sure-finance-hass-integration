"""Minimal Sure Finance API Client (no cache).

Async client to interact with the Sure Finance API.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout


class APIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(APIError):
    pass


class RateLimitError(APIError):
    pass


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

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def connect(self):
        if self._session is None:
            headers = {
                "X-Api-Key": self.api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            self._session = aiohttp.ClientSession(headers=headers, timeout=self.timeout)

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    def _url(self, endpoint: str) -> str:
        return urljoin(self.base_url, endpoint)

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        if self._session is None:
            await self.connect()
        url = self._url(endpoint)
        try:
            async with self._session.request(method, url, **kwargs) as resp:
                data = await resp.json(content_type=None) if resp.content_length else {}
                if resp.status in (200, 201):
                    return data
                if resp.status == 401:
                    raise AuthenticationError("Authentication failed", status_code=401, details=data)
                if resp.status == 429:
                    raise RateLimitError("Rate limit exceeded", status_code=429, details=data)
                raise APIError(f"API error: {data.get('error') or resp.reason}", status_code=resp.status, details=data)
        except aiohttp.ClientError as e:
            raise APIError(f"Network error: {e}")

    # Endpoints
    async def get_accounts(self, page: Optional[int] = None, per_page: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page
        return await self._request("GET", "/api/v1/accounts", params=params)

    async def get_transactions(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_id: Optional[str] = None,
        transaction_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page
        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%d")
        if account_id:
            params["account_id"] = account_id
        if transaction_type:
            params["type"] = transaction_type
        if search:
            params["search"] = search
        return await self._request("GET", "/api/v1/transactions", params=params)

    async def get_all_pages(self, endpoint_func, per_page: int = 100, **kwargs) -> Any:
        page = 1
        items = []
        while True:
            result = await endpoint_func(page=page, per_page=per_page, **kwargs)
            if "accounts" in result:
                batch = result["accounts"]
            elif "transactions" in result:
                batch = result["transactions"]
            else:
                batch = result.get("data") or []
            items.extend(batch)

            meta = result.get("pagination") or result.get("meta")
            if not meta:
                break
            total_pages = meta.get("total_pages", 0)
            if page >= total_pages or total_pages == 0:
                break
            page += 1
        return items
