"""Shared fixtures.

The payloads here mirror the *real* shapes returned by app.sure.am, recorded from
a live account. The important detail is that objects embedded inside a
transaction are slim projections, not full entities:

  * embedded ``account``  -> {id, name, account_type}      (no balance/classification)
  * embedded ``category`` -> {id, name, color, icon}       (**no classification**)

``openapi.yaml`` in the sibling add-on repo claims ``Category.classification`` is
required. It is not returned by the API, and assuming it was is what broke
transaction parsing in v1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ACCOUNT_CREDIT_CARD = {
    "id": "9e18efc6-c159-4f56-8e99-8cfd00856c61",
    "name": "Bac VISA Pricesmart",
    "balance": "-₡678.855,10",
    "balance_cents": -67885510,
    "currency": "CRC",
    "classification": "liability",
    "account_type": "credit_card",
    "subtype": None,
    "status": "active",
    "institution_name": "Bac San Jose",
    "created_at": "2026-03-18T07:46:08Z",
    "updated_at": "2026-08-26T05:28:17Z",
}

ACCOUNT_CHECKING = {
    "id": "b2f5427e-f73c-4ee2-8fba-5dcdd25835b7",
    "name": "Bac Colones",
    "balance": "$150.00",
    "balance_cents": 15000,
    "currency": "USD",
    "classification": "asset",
    "account_type": "depository",
    "created_at": "2026-03-18T07:46:08Z",
    "updated_at": "2026-08-26T05:28:17Z",
}


def make_transaction(
    *,
    tx_id: str = "1de52fb9-e7f0-4e27-80f5-850bf72611a1",
    date: str = "2026-08-15",
    amount: str = "-₡71.265,92",
    classification: str = "expense",
    category: dict | None = None,
    currency: str = "CRC",
) -> dict:
    """Build a transaction in the exact shape the API returns."""
    return {
        "id": tx_id,
        "date": date,
        "amount": amount,
        "amount_cents": 7126592,
        "signed_amount_cents": 7126592,
        "currency": currency,
        "name": "PAGO DE TARJETA",
        "notes": None,
        "classification": classification,
        # Slim projection: no balance, currency or classification.
        "account": {
            "id": ACCOUNT_CREDIT_CARD["id"],
            "name": ACCOUNT_CREDIT_CARD["name"],
            "account_type": "credit_card",
        },
        "category": category,
        "merchant": None,
        "tags": [{"id": "f002f4f8-dd2e-4e57-a59e-c6d73cc88d62", "name": "Juan", "color": "#61c9ea"}],
        "transfer": None,
        "created_at": "2026-08-26T05:30:33Z",
        "updated_at": "2026-08-26T05:30:33Z",
    }


#: Category exactly as embedded in a transaction — note the absent "classification".
SLIM_CATEGORY = {
    "id": "6973d924-1b92-44a6-9008-cc87c36e40ec",
    "name": "Income",
    "color": "#22c55e",
    "icon": "circle-dollar-sign",
}


@pytest.fixture
def accounts() -> list[dict]:
    return [dict(ACCOUNT_CREDIT_CARD), dict(ACCOUNT_CHECKING)]


@pytest.fixture
def transactions() -> list[dict]:
    return [
        make_transaction(
            tx_id="11111111-1111-1111-1111-111111111111",
            date="2026-08-01",
            amount="₡100.000,00",
            classification="income",
            category=SLIM_CATEGORY,
        ),
        make_transaction(
            tx_id="22222222-2222-2222-2222-222222222222",
            date="2026-08-15",
            amount="-₡25.000,50",
            classification="expense",
            category={"id": "abc", "name": "Groceries", "color": "#f00", "icon": "cart"},
        ),
        make_transaction(
            tx_id="33333333-3333-3333-3333-333333333333",
            date="2026-08-20",
            amount="-₡5.000,00",
            classification="expense",
            category=None,
        ),
    ]
