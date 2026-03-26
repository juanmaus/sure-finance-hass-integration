"""Financial calculation utilities (no cache, dict-based).

Works directly with API response dicts.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple


def _parse_decimal(value: Any) -> Decimal:
    """Parse numeric values that may include currency symbols and locale separators.
    Returns Decimal(0) if parsing fails.
    """
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        s = value.strip()
        negative = False
        if s.startswith("(") and s.endswith(")"):
            negative = True
            s = s[1:-1]
        import re
        s = re.sub(r"[^0-9,\.-]", "", s)
        if s.count("-") > 1:
            s = s.replace("-", "")
        s = s if not s.endswith("-") else ("-" + s[:-1])
        last_dot = s.rfind('.')
        last_comma = s.rfind(',')
        if last_dot == -1 and last_comma == -1:
            normalized = s
        else:
            if last_dot > last_comma:
                decimal_sep = '.'
                thousand_sep = ','
            else:
                decimal_sep = ','
                thousand_sep = '.'
            s_wo_thousands = s.replace(thousand_sep, '')
            if decimal_sep != '.':
                s_wo_thousands = s_wo_thousands.replace(decimal_sep, '.')
            normalized = s_wo_thousands
        try:
            d = Decimal(normalized)
            if negative:
                d = -d
            return d
        except (InvalidOperation, ValueError):
            return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def calculate_financial_summary(accounts: List[Dict[str, Any]], transactions: Optional[List[Dict[str, Any]]], currency: str) -> Dict[str, Any]:
    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    total_cashflow = Decimal("0")
    total_outflow = Decimal("0")

    for acc in accounts:
        bal = _parse_decimal(acc.get("balance"))
        cls = (acc.get("classification") or "").lower()
        if cls == "asset":
            total_assets += bal
        elif cls == "liability":
            total_liabilities += abs(bal)

    if transactions:
        for tx in transactions:
            amt = _parse_decimal(tx.get("amount"))
            nature = (tx.get("classification") or tx.get("nature") or "").lower()
            if nature == "income":
                total_cashflow += amt
            elif nature == "expense":
                total_outflow += abs(amt)

    net_worth = total_assets - total_liabilities

    return {
        "total_cashflow": float(total_cashflow),
        "total_outflow": float(total_outflow),
        "total_assets": float(total_assets),
        "total_liabilities": float(total_liabilities),
        "net_worth": float(net_worth),
        "currency": currency,
        "last_updated": datetime.utcnow().isoformat(),
    }


def get_account_balances(accounts: List[Dict[str, Any]], default_currency: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    now = datetime.utcnow().isoformat()
    for acc in accounts:
        out.append(
            {
                "account_id": acc.get("id"),
                "account_name": acc.get("name"),
                "balance": float(_parse_decimal(acc.get("balance"))),
                "currency": acc.get("currency") or default_currency,
                "classification": (acc.get("classification") or "asset").lower(),
                "last_updated": acc.get("updated_at") or now,
            }
        )
    return out


def calculate_monthly_cashflow(transactions: List[Dict[str, Any]], start: datetime, end: datetime, currency: str) -> Dict[str, Any]:
    inc = Decimal("0")
    exp = Decimal("0")
    inc_by_cat: Dict[str, Decimal] = defaultdict(Decimal)
    exp_by_cat: Dict[str, Decimal] = defaultdict(Decimal)

    for tx in transactions:
        # Filter by date
        try:
            # tx['date'] can be YYYY-MM-DD or ISO; handle both
            tx_date_str = tx.get("date")
            if not tx_date_str:
                continue
            if len(tx_date_str) == 10:
                tx_date = datetime.strptime(tx_date_str, "%Y-%m-%d")
            else:
                tx_date = datetime.fromisoformat(tx_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            continue
        if not (start <= tx_date <= end):
            continue

        amt = _parse_decimal(tx.get("amount"))
        nature = (tx.get("classification") or tx.get("nature") or "").lower()
        cat = (tx.get("category", {}) or {}).get("name") or "Uncategorized"

        if nature == "income":
            inc += amt
            inc_by_cat[cat] += amt
        elif nature == "expense":
            a = abs(amt)
            exp += a
            exp_by_cat[cat] += a

    net = inc - exp

    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "total_income": float(inc),
        "total_expenses": float(exp),
        "net_cashflow": float(net),
        "income_by_category": {k: float(v) for k, v in inc_by_cat.items()},
        "expenses_by_category": {k: float(v) for k, v in exp_by_cat.items()},
        "currency": currency,
    }


def calculate_monthly_trends(transactions: List[Dict[str, Any]], months: int, currency: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    end_date = datetime.utcnow()
    txs = list(transactions)

    for _ in range(months):
        month_end = end_date.replace(day=1) - timedelta(days=1)
        month_start = month_end.replace(day=1)
        key = month_start.strftime("%Y-%m")
        out[key] = calculate_monthly_cashflow(txs, month_start, month_end, currency)
        end_date = month_start - timedelta(days=1)

    return out
