"""Tests for the API client."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from custom_components.sure_finance.api_client import (
    APIError,
    AuthenticationError,
    RateLimitError,
    SureFinanceClient,
)


@pytest.fixture
def client():
    return SureFinanceClient(api_key="secret", base_url="https://app.sure.am")


class TestRequestParams:
    @pytest.mark.asyncio
    async def test_transaction_date_range_formatting(self, client):
        client._request = AsyncMock(return_value={})

        await client.get_transactions(
            page=2,
            per_page=50,
            start_date=datetime(2026, 7, 26, 13, 4),
            end_date=datetime(2026, 8, 25, 23, 36),
        )

        params = client._request.await_args.kwargs["params"]
        assert params == {
            "page": 2,
            "per_page": 50,
            "start_date": "2026-07-26",
            "end_date": "2026-08-25",
        }

    @pytest.mark.asyncio
    async def test_omits_unset_filters(self, client):
        client._request = AsyncMock(return_value={})

        await client.get_transactions(per_page=100)

        assert client._request.await_args.kwargs["params"] == {"per_page": 100}

    def test_url_join(self, client):
        assert client._url("/api/v1/accounts") == "https://app.sure.am/api/v1/accounts"


class TestGetAllPages:
    @pytest.mark.asyncio
    async def test_walks_every_page(self, client):
        pages = [
            {"transactions": [{"id": "1"}, {"id": "2"}], "pagination": {"total_pages": 2}},
            {"transactions": [{"id": "3"}], "pagination": {"total_pages": 2}},
        ]
        endpoint = AsyncMock(side_effect=pages)

        items = await client.get_all_pages(endpoint, per_page=2)

        assert [i["id"] for i in items] == ["1", "2", "3"]
        assert endpoint.await_count == 2

    @pytest.mark.asyncio
    async def test_stops_without_pagination_block(self, client):
        endpoint = AsyncMock(return_value={"accounts": [{"id": "a"}]})

        items = await client.get_all_pages(endpoint)

        assert items == [{"id": "a"}]
        assert endpoint.await_count == 1

    @pytest.mark.asyncio
    async def test_zero_total_pages_terminates(self, client):
        """Guards against an infinite request loop on an empty result set."""
        endpoint = AsyncMock(return_value={"transactions": [], "pagination": {"total_pages": 0}})

        items = await client.get_all_pages(endpoint)

        assert items == []
        assert endpoint.await_count == 1


class TestErrorMapping:
    @pytest.mark.parametrize(
        "status,expected",
        [(401, AuthenticationError), (429, RateLimitError), (500, APIError)],
    )
    @pytest.mark.asyncio
    async def test_status_codes_map_to_exceptions(self, client, status, expected):
        class FakeResponse:
            def __init__(self):
                self.status = status
                self.reason = "err"
                self.content_length = 10

            async def json(self, content_type=None):
                return {"error": "nope"}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        class FakeSession:
            def request(self, *args, **kwargs):
                return FakeResponse()

        client._session = FakeSession()

        with pytest.raises(expected):
            await client._request("GET", "/api/v1/accounts")
