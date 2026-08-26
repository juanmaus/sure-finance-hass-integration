# CLAUDE.md

Home Assistant custom integration (HACS) for the **Sure Finance** API (`https://app.sure.am`).
Exposes net worth, cashflow, outflow, liabilities, savings rate and per-account balance sensors.

## Design rule: don't model the API

There is **no schema layer**. `api_client.py` returns raw response dicts, and everything downstream
reads them with `.get()`. This is deliberate: v1 used pydantic models, and the integration went
permanently unavailable because `Category` required a `classification` field that the API doesn't
return on the category embedded in a transaction. One unexpected field killed every refresh.

If you reintroduce typed models, you take on that failure mode again. Prefer tolerant `.get()`
access and let `_parse_decimal` absorb bad values.

## Module map

`custom_components/sure_finance/`

- `const.py` — `DOMAIN`, `PLATFORMS`, defaults, `TRANSACTION_WINDOW_DAYS`. Import constants from
  here, not from `__init__.py` (that used to cause an import cycle with `sensor.py`).
- `__init__.py` — `async_setup_entry` builds the client and coordinator, **runs the first refresh
  itself**, then forwards to platforms. Registers the `sure_finance.refresh_data` service once.
- `coordinator.py` — `SureFinanceDataCoordinator`. Fetches accounts + the last 30 days of
  transactions, returns `{summary, balances, monthly_cashflow, last_update}`. Wraps `APIError` in
  `UpdateFailed`.
- `api_client.py` — aiohttp client, `X-Api-Key` header. `get_all_pages()` walks
  `pagination.total_pages` and unwraps `accounts`/`transactions`/`data`.
- `financial_calculator.py` — module-level functions over dicts. `_parse_decimal()` handles
  localised money strings (`"$418.40"`, `"-₡71.265,92"`, `"(1,234.56)"`) by inferring the decimal
  separator from whichever of `.`/`,` appears last, and returns `Decimal("0")` rather than raising.
- `sensor.py` — entities only. Reads the coordinator from `hass.data`; never fetches.
- `config_flow.py` — UI config: `api_key`, `host`, `update_interval`, `currency`, sensor toggles.

## Two structural rules

1. **The first refresh belongs in `__init__.py`, not the sensor platform.** Raising
   `ConfigEntryNotReady` from inside `async_forward_entry_setups` makes HA log
   `"raises exception ConfigEntryNotReady in forwarded platform sensor"`. `test_init.py`
   asserts the `connect → refresh → forward` ordering.
2. **Close the aiohttp session on every setup failure.** HA retries entry setup on
   `ConfigEntryNotReady`, so an early `return`/`raise` that skips `client.close()` leaks one
   `ClientSession` per attempt.

## API shape gotchas

`../sure-finance-hass-addons/openapi.yaml` is the spec, but **it is wrong in at least one place**:
it marks `Category.classification` required while the live API never returns it. Prefer the real
recorded payloads in `../sure-finance-hass-addons/sure-finance/cache/*.cache` (pickled
`{"value": [...], "expires_at": ...}`) over the spec when deciding what a field looks like.

Objects embedded in a transaction are **slim projections**, not full entities:

- embedded `account` → `{id, name, account_type}` (no balance/currency/classification/timestamps)
- embedded `category` → `{id, name, color, icon}` (**no `classification`**)
- top-level `/api/v1/accounts` → full objects, `balance` as a formatted string, plus `classification`
- money is a **formatted string** (`"$0.00"`, `"-₡71.265,92"`); `*_cents` integers exist but are unused
- transaction `date` is `YYYY-MM-DD`, so it parses to midnight — any window boundary compared
  against it must also be midnight, or transactions on the first day get dropped

## Sibling repos

`../sure-finance-hass-addons/sure-finance/` is a **separate HA add-on** hitting the same API. It
still carries the old pydantic `src/models.py`, `data_manager.py` and `cache_manager.py` that this
integration was originally copy-pasted from. It is *not* kept in sync any more — don't mirror
changes there without checking, and don't treat its models as a reference for API shape.

## Testing

```bash
python -m pytest        # pytest.ini enforces --cov-fail-under=85
```

`requirements-test.txt` has the deps. The repo's own `.venv/` is empty; a working interpreter with
Home Assistant + pytest lives at `../sure-finance-hass-addons/sure-finance/venv/bin/python`.

`tests/conftest.py` fixtures mirror real recorded payloads, including the slim category with no
`classification` — that's the v1 regression, keep it that way.

## Deployment

HACS keys off `manifest.json` → `version`. It sat at `1.0.0` from the initial commit through several
bug-fix commits, so **fixes never reached the installed instance**. Always bump the version and add
a `CHANGELOG.md` entry when shipping a fix.

Deployed location on the HA box is `/config/custom_components/sure_finance/`. v1 left a pickle cache
in `/config/custom_components/sure_finance/cache/`; that directory is now unused and should be
deleted by hand.

## Conventions

- Log with lazy `%s` formatting, not f-strings.
- `_LOGGER`, not `logger`.
