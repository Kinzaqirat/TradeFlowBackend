"""Pydantic v2 schemas for Trade endpoints."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional


class TradeCreate(BaseModel):
    symbol: str
    direction: str  # LONG | SHORT
    entry_datetime: datetime
    exit_datetime: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    fees: Decimal = Decimal("0")
    notes: Optional[str] = None
    tags: list[str] = []

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        v = v.upper()
        if v not in ("LONG", "SHORT"):
            raise ValueError("Direction must be LONG or SHORT")
        return v

    @field_validator("entry_price", "exit_price", "quantity")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Must be greater than 0")
        return v

    @model_validator(mode="after")
    def exit_after_entry(self) -> "TradeCreate":
        if self.exit_datetime <= self.entry_datetime:
            raise ValueError("exit_datetime must be after entry_datetime")
        return self


class TradeUpdate(BaseModel):
    symbol: Optional[str] = None
    direction: Optional[str] = None
    entry_datetime: Optional[datetime] = None
    exit_datetime: Optional[datetime] = None
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    fees: Optional[Decimal] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None


class TradeResponse(BaseModel):
    id: str
    symbol: str
    direction: str
    entry_datetime: datetime
    exit_datetime: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    fees: Decimal
    notes: Optional[str]
    tags: list[str]
    pnl: Decimal
    pnl_percent: Decimal
    result: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
