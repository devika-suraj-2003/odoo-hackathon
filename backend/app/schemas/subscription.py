from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class SubscriptionLineCreate(BaseModel):
    product_id: int = Field(ge=1)
    variant_id: Optional[int] = Field(default=None, ge=1)
    tax_id: Optional[int] = Field(default=None, ge=1)
    quantity: int = Field(default=1, ge=1, strict=True)
    unit_price: int = Field(ge=0, strict=True, description="Unit price in paise")


class SubscriptionCreate(BaseModel):
    customer_id: int = Field(ge=1)
    plan_id: int = Field(ge=1)
    template_id: Optional[int] = Field(default=None, ge=1)
    start_date: date = Field(default_factory=date.today)
    payment_terms: str = Field(default="immediate", max_length=30)
    lines: list[SubscriptionLineCreate] = Field(min_length=1)
    discount_id: Optional[int] = Field(default=None, ge=1)


class SubscriptionResponse(BaseModel):
    id: int
    number: str
    customer: Optional[dict]
    plan: Optional[dict]
    status: str
    start_date: date
    expiry_date: Optional[date]
    next_billing_date: Optional[date]
    payment_terms: str
    lines: list[dict]
    subtotal: int
    discount_total: int
    total: int
    history: list[dict]
