"""Tests for config entry setup and teardown."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryNotReady

import custom_components.sure_finance as init_module
from custom_components.sure_finance import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.sure_finance.api_client import AuthenticationError
from custom_components.sure_finance.const import DOMAIN, SERVICE_REFRESH_DATA


@pytest.fixture
def call_order():
    return []


@pytest.fixture
def hass(call_order):
    hass = MagicMock()
    hass.data = {}
    hass.services.has_service.return_value = False

    async def forward(entry, platforms):
        call_order.append("forward")

    hass.config_entries.async_forward_entry_setups = AsyncMock(side_effect=forward)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def entry():
    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.data = {"api_key": "secret", "host": "https://app.sure.am"}
    return entry


@pytest.fixture
def client(call_order):
    client = MagicMock()
    client.connect = AsyncMock(side_effect=lambda: call_order.append("connect"))
    client.close = AsyncMock()
    return client


@pytest.fixture
def coordinator(call_order):
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=lambda: call_order.append("refresh")
    )
    return coordinator


def patched(client, coordinator):
    return (
        patch.object(init_module, "SureFinanceClient", return_value=client),
        patch.object(init_module, "SureFinanceDataCoordinator", return_value=coordinator),
    )


class TestAsyncSetup:
    @pytest.mark.asyncio
    async def test_creates_namespace(self, hass):
        assert await async_setup(hass, {}) is True
        assert hass.data[DOMAIN] == {}


class TestSetupEntry:
    @pytest.mark.asyncio
    async def test_successful_setup(self, hass, entry, client, coordinator):
        p1, p2 = patched(client, coordinator)
        with p1, p2:
            assert await async_setup_entry(hass, entry) is True

        stored = hass.data[DOMAIN]["entry-1"]
        assert stored["api_client"] is client
        assert stored["coordinator"] is coordinator
        hass.services.async_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_first_refresh_happens_before_forwarding(
        self, hass, entry, client, coordinator, call_order
    ):
        """The regression this restructure fixes.

        Home Assistant logs an error if a forwarded platform raises
        ConfigEntryNotReady, so the first refresh must complete during entry
        setup rather than inside the sensor platform.
        """
        p1, p2 = patched(client, coordinator)
        with p1, p2:
            await async_setup_entry(hass, entry)

        assert call_order == ["connect", "refresh", "forward"]

    @pytest.mark.asyncio
    async def test_invalid_auth_returns_false(self, hass, entry, client, coordinator):
        coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=AuthenticationError("bad key", 401)
        )
        p1, p2 = patched(client, coordinator)
        with p1, p2:
            assert await async_setup_entry(hass, entry) is False

        client.close.assert_awaited_once()
        hass.config_entries.async_forward_entry_setups.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_ready_closes_session(self, hass, entry, client, coordinator):
        """HA retries setup; a leaked ClientSession per attempt would pile up."""
        coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=ConfigEntryNotReady("api down")
        )
        p1, p2 = patched(client, coordinator)
        with p1, p2, pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)

        client.close.assert_awaited_once()
        assert "entry-1" not in hass.data.get(DOMAIN, {})

    @pytest.mark.asyncio
    async def test_service_registered_only_once(self, hass, entry, client, coordinator):
        hass.services.has_service.return_value = True
        p1, p2 = patched(client, coordinator)
        with p1, p2:
            await async_setup_entry(hass, entry)

        hass.services.async_register.assert_not_called()


class TestRefreshService:
    @pytest.mark.asyncio
    async def test_service_refreshes_every_entry(self, hass, entry, client, coordinator):
        coordinator.async_request_refresh = AsyncMock()
        p1, p2 = patched(client, coordinator)
        with p1, p2:
            await async_setup_entry(hass, entry)

        handler = hass.services.async_register.call_args[0][2]
        await handler(MagicMock())

        coordinator.async_request_refresh.assert_awaited_once()


class TestUnloadEntry:
    @pytest.mark.asyncio
    async def test_closes_client_and_removes_service(self, hass, entry, client, coordinator):
        hass.data[DOMAIN] = {"entry-1": {"api_client": client, "coordinator": coordinator}}

        assert await async_unload_entry(hass, entry) is True

        client.close.assert_awaited_once()
        hass.services.async_remove.assert_called_once_with(DOMAIN, SERVICE_REFRESH_DATA)

    @pytest.mark.asyncio
    async def test_keeps_service_while_entries_remain(self, hass, entry, client, coordinator):
        hass.data[DOMAIN] = {
            "entry-1": {"api_client": client, "coordinator": coordinator},
            "entry-2": {"api_client": MagicMock(), "coordinator": MagicMock()},
        }

        await async_unload_entry(hass, entry)

        hass.services.async_remove.assert_not_called()

    @pytest.mark.asyncio
    async def test_failed_platform_unload_keeps_data(self, hass, entry, client, coordinator):
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
        hass.data[DOMAIN] = {"entry-1": {"api_client": client, "coordinator": coordinator}}

        assert await async_unload_entry(hass, entry) is False

        client.close.assert_not_awaited()
        assert "entry-1" in hass.data[DOMAIN]
