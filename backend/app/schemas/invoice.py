from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class InvoiceLineCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    quantity: int = Field(ge=1, strict=True)
    unit_price: int = Field(ge=0, strict=True, description="Unit price in paise")
    product_id: Optional[int] = Field(default=None, ge=1)
    tax_id: Optional[int] = Field(default=None, ge=1)


class InvoiceCreate(BaseModel):
    customer_id: int = Field(ge=1)
    subscription_id: Optional[int] = Field(default=None, ge=1)
    due_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    lines: list[InvoiceLineCreate] = Field(min_length=1)
    discount_id: Optional[int] = Field(default=None, ge=1)
    customer_state: Optional[str] = Field(default=None, min_length=1, max_length=100)


class InvoiceResponse(BaseModel):
    id: int
    number: str
    subscription_id: Optional[int]
    customer: Optional[dict]
    status: str
    invoice_date: date
    due_date: Optional[date]
    period_start: Optional[date]
    period_end: Optional[date]
    lines: list[dict]
    subtotal: int
    discount_total: int
    tax_total: int
    total: int
    amount_paid: int
    amount_due: int

    model_config = ConfigDict(from_attributes=True)
