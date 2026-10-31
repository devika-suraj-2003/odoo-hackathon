from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PaymentMethod(str, Enum):
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    CASH = "cash"
    RAZORPAY = "razorpay"


class PaymentCreate(BaseModel):
    invoice_id: int = Field(ge=1)
    amount: int = Field(gt=0, strict=True, description="Payment amount in paise")
    method: PaymentMethod
    payment_date: date = Field(default_factory=date.today)
    note: Optional[str] = Field(default=None, max_length=500)


class PaymentResponse(BaseModel):
    id: int
    invoice_id: int
    method: str
    amount: int
    payment_date: date
    note: Optional[str]


class RazorpayOrderRequest(BaseModel):
    invoice_id: int = Field(ge=1)


class RazorpayOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str


class RazorpayVerifyRequest(BaseModel):
    invoice_id: int = Field(ge=1)
    razorpay_order_id: str = Field(min_length=1, max_length=100)
    razorpay_payment_id: str = Field(min_length=1, max_length=100)
    razorpay_signature: str = Field(min_length=1, max_length=256)
