# Sure Finance Home Assistant Integration

Display your Sure Finance data as native Home Assistant entities (net worth, income, expenses, liabilities, per-account balances, savings rate).

This is a custom integration for Home Assistant (HACS compatible).

## Features
- Sensors: Net Worth, Total Cashflow (income), Total Outflow (expenses), Total Liability, Monthly Savings Rate
- Optional per-account balance sensors
- Config flow (UI) with API Key, API Host, update interval, toggles
- Caching and retry logic

## Installation (HACS)
1. In HACS → Integrations → three-dots menu → Custom repositories
2. Add this repository URL and select category "Integration"
3. Find "Sure Finance" in HACS, install
4. Restart Home Assistant
5. Go to Settings → Devices & Services → Add Integration → search "Sure Finance"
6. Enter:
   - API Key (from your Sure instance)
   - API Host (base URL, e.g. https://app.sure.am or http://your-local-sure:3000)

## Manual install (without HACS)
1. Copy `custom_components/sure_finance` to `<config>/custom_components/sure_finance` on your HA instance
2. Restart Home Assistant
3. Add the integration from Settings → Devices & Services

## Configuration Options
- API Key (required)
- API Host (Base URL) (defaults to https://app.sure.am)
- Update interval (seconds)
- Currency code
- Enable/disable specific sensors (cashflow, outflow, liability, account sensors)
- Cache duration (seconds)

## Entities
- sensor.sure_finance_net_worth
- sensor.sure_finance_total_cashflow
- sensor.sure_finance_total_outflow
- sensor.sure_finance_total_liability
- sensor.sure_finance_monthly_savings_rate
- sensor.sure_finance_account_<name> (if enabled)

## Services
- sure_finance.refresh_data
- sure_finance.clear_cache

## Troubleshooting
- Enable debug logging:
  ```yaml
  logger:
    default: info
    logs:
      custom_components.sure_finance: debug
  ```
- If API returns localized currency strings (e.g., $1,234.56 or 1.234,56), the integration parses them automatically.
- For self-hosted instances with self-signed TLS, use http:// or install a valid certificate.

## License
MIT
