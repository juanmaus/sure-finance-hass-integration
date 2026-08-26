# Changelog

## 2.0.0 - 2026-08-26

### Fixed
- **Transactions failed to parse, leaving the integration permanently unavailable.**
  The pydantic `Category` model required a `classification` field that the API does not
  return on the category embedded in a transaction, so every transaction with a category
  raised `1 validation error for Transaction`. `openapi.yaml` documents the field as
  required; the live API omits it. Modelling the API response at all is what made this
  fragile, so the models are gone (see below).
- `ConfigEntryNotReady` was raised from inside the forwarded `sensor` platform, which
  Home Assistant logs as an error. The first refresh now happens during config entry
  setup, before `async_forward_entry_setups`.
- Transactions dated the 1st of the month were excluded from the monthly cashflow figures.
  The month boundary carried the current time of day while transaction dates parse to
  midnight, so anything dated the 1st fell before the window start.
- The aiohttp `ClientSession` was leaked on every failed setup attempt; Home Assistant
  retries setup, so sessions accumulated for as long as the API was unreachable.
- `enable_cashflow_sensor`, `enable_outflow_sensor` and `enable_liability_sensor` are
  honoured again — those sensors were created regardless of the setting.

### Changed
- **Breaking:** removed the cache layer (`cache_manager.py`, `data_manager.py`) and the
  pydantic models (`models.py`). Data is read live from the API on each refresh and
  passed around as plain dicts, so an unexpected field can no longer break a refresh.
- **Breaking:** removed the `sure_finance.clear_cache` service. There is no cache to
  clear; delete any automation or script that calls it.
- **Breaking:** removed the "Cache duration" config option. Existing config entries keep
  the stored value; it is ignored.
- Integration no longer declares `pydantic`, `redis` or `python-dateutil` requirements,
  so Home Assistant installs nothing at startup.
- `refresh_data` now refreshes every configured entry rather than only the last one set up.

### Upgrade notes
After updating, delete `/config/custom_components/sure_finance/cache/` — the old pickle
cache directory is no longer read or cleaned up.

## 1.0.0 - 2026-03-26
- Initial HACS-compatible release of Sure Finance custom integration
- Config flow with API Key and API Host
- Sensors for net worth, cashflow, outflow, liabilities, savings rate, and per-account balances
- Caching and robust parsing of localized currency formats
