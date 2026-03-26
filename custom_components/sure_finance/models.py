"""Pydantic models (integration copy)."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    INFLOW = "inflow"
    OUTFLOW = "outflow"


class AccountClassification(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    INCOME = "income"
    EXPENSE = "expense"


class CategoryClassification(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class ImportStatus(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    IMPORTING = "importing"
    REVERTING = "reverting"
    REVERT_FAILED = "revert_failed"
    FAILED = "failed"


class TradeType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class BaseEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def _parse_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
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
            return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


class Account(BaseEntity):
    name: str
    account_type: str
    balance: Optional[Decimal] = None
    currency: Optional[str] = None
    classification: Optional[AccountClassification] = None

    @field_validator('balance', mode='before')
    @classmethod
    def _balance_parse(cls, v):
        parsed = _parse_decimal(v)
        return parsed if parsed is not None else v


class Category(BaseEntity):
    name: str
    classification: CategoryClassification
    color: str
    icon: str
    parent_id: Optional[UUID] = None
    parent: Optional['Category'] = None
    subcategories_count: int = 0


class Merchant(BaseEntity):
    name: str
    type: Optional[str] = Field(default=None, description="FamilyMerchant or ProviderMerchant")


class Tag(BaseEntity):
    name: str
    color: str


class Transfer(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    other_account: Optional[Account] = None


class Transaction(BaseEntity):
    date: datetime
    amount: Decimal
    currency: str
    name: str
    notes: Optional[str] = None
    classification: str
    account: Account
    category: Optional[Category] = None
    merchant: Optional[Merchant] = None
    tags: List[Tag] = Field(default_factory=list)
    transfer: Optional[Transfer] = None

    @field_validator('amount', mode='before')
    @classmethod
    def _amount_parse(cls, v):
        parsed = _parse_decimal(v)
        return parsed if parsed is not None else v


class Trade(BaseEntity):
    date: datetime
    amount: Decimal
    currency: str
    name: str
    notes: Optional[str] = None
    qty: Decimal
    price: Decimal
    investment_activity_label: Optional[str] = None
    account: Account
    security: Optional[Dict[str, Any]] = None
    category: Optional[Dict[str, Any]] = None

    @field_validator('amount', 'qty', 'price', mode='before')
    @classmethod
    def _trade_numbers_parse(cls, v):
        parsed = _parse_decimal(v)
        return parsed if parsed is not None else v


class Holding(BaseEntity):
    date: datetime
    qty: Decimal = Field(description="Quantity of shares held")
    price: Decimal = Field(description="Price per share")
    amount: Decimal
    currency: str
    cost_basis_source: Optional[str] = None
    account: Account
    security: Dict[str, Any]
    avg_cost: Optional[Decimal] = None

    @field_validator('qty', 'price', 'amount', 'avg_cost', mode='before')
    @classmethod
    def _holding_numbers_parse(cls, v):
        parsed = _parse_decimal(v)
        return parsed if parsed is not None else v


class Valuation(BaseEntity):
    date: datetime
    amount: Decimal
    currency: str
    notes: Optional[str] = None
    kind: str
    account: Account

    @field_validator('amount', mode='before')
    @classmethod
    def _valuation_amount_parse(cls, v):
        parsed = _parse_decimal(v)
        return parsed if parsed is not None else v


class ImportConfiguration(BaseModel):
    date_col_label: Optional[str] = None
    amount_col_label: Optional[str] = None
    name_col_label: Optional[str] = None
    category_col_label: Optional[str] = None
    tags_col_label: Optional[str] = None
    notes_col_label: Optional[str] = None
    account_col_label: Optional[str] = None
    date_format: Optional[str] = None
    number_format: Optional[str] = None
    signage_convention: Optional[str] = None


class ImportStats(BaseModel):
    rows_count: int = 0
    valid_rows_count: Optional[int] = None


class Import(BaseEntity):
    type: str
    status: ImportStatus
    account_id: Optional[UUID] = None
    rows_count: Optional[int] = None
    error: Optional[str] = None
    configuration: Optional[ImportConfiguration] = None
    stats: Optional[ImportStats] = None


class PaginationInfo(BaseModel):
    page: int = Field(ge=1)
    per_page: int = Field(ge=1)
    total_count: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class PaginatedResponse(BaseModel):
    pagination: PaginationInfo


class TransactionCollection(PaginatedResponse):
    transactions: List[Transaction]


class AccountCollection(PaginatedResponse):
    accounts: List[Account]


class CategoryCollection(PaginatedResponse):
    categories: List[Category]


class TradeCollection(PaginatedResponse):
    trades: List[Trade]


class HoldingCollection(PaginatedResponse):
    holdings: List[Holding]


class FinancialSummary(BaseModel):
    total_cashflow: Decimal = Field(default=Decimal("0"))
    total_outflow: Decimal = Field(default=Decimal("0"))
    total_assets: Decimal = Field(default=Decimal("0"))
    total_liabilities: Decimal = Field(default=Decimal("0"))
    net_worth: Decimal = Field(default=Decimal("0"))
    currency: str = "USD"
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('total_cashflow', 'total_outflow', 'total_assets', 'total_liabilities', 'net_worth', mode='before')
    @classmethod
    def _summary_numbers_parse(cls, v):
        parsed = _parse_decimal(v)
        return parsed if parsed is not None else v


class AccountBalance(BaseModel):
    account_id: UUID
    account_name: str
    balance: Decimal
    currency: str
    classification: AccountClassification
    last_updated: datetime

    @field_validator('balance', mode='before')
    @classmethod
    def _balance_parse_ab(cls, v):
        parsed = _parse_decimal(v)
        return parsed if parsed is not None else v


class CashflowItem(BaseModel):
    date: datetime
    amount: Decimal
    currency: str
    category: Optional[str] = None
    merchant: Optional[str] = None
    description: str
    transaction_id: UUID

    @field_validator('amount', mode='before')
    @classmethod
    def _cashflow_item_amount(cls, v):
        parsed = _parse_decimal(v)
        return parsed if parsed is not None else v


class CashflowSummary(BaseModel):
    period_start: datetime
    period_end: datetime
    total_income: Decimal = Field(default=Decimal("0"))
    total_expenses: Decimal = Field(default=Decimal("0"))
    net_cashflow: Decimal = Field(default=Decimal("0"))
    income_by_category: Dict[str, Decimal] = Field(default_factory=dict)
    expenses_by_category: Dict[str, Decimal] = Field(default_factory=dict)
    currency: str = "USD"

    @field_validator('total_income', 'total_expenses', 'net_cashflow', mode='before')
    @classmethod
    def _cashflow_summary_numbers(cls, v):
        parsed = _parse_decimal(v)
        return parsed if parsed is not None else v


Category.model_rebuild()
