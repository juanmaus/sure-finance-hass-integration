"""Constants for the Sure Finance integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "sure_finance"
PLATFORMS = [Platform.SENSOR]

DEFAULT_HOST = "https://app.sure.am"
DEFAULT_UPDATE_INTERVAL = 300
DEFAULT_CURRENCY = "USD"

# Number of days of transaction history pulled on every refresh.
TRANSACTION_WINDOW_DAYS = 30

SERVICE_REFRESH_DATA = "refresh_data"
