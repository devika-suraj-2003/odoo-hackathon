from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DiscountType(str, Enum):
    PERCENT = "percent"
    FIXED = "fixed"


class DiscountApplicability(str, Enum):
    SUBSCRIPTION = "subscription"
    PRODUCTS = "products"


class DiscountFields(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    discount_type: DiscountType
    value: Decimal = Field(gt=0)
    min_purchase: Optional[int] = Field(default=None, ge=0, strict=True)
    min_qty: Optional[int] = Field(default=None, ge=1, strict=True)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    usage_limit: Optional[int] = Field(default=None, ge=1, strict=True)
    applies_to: DiscountApplicability
    product_ids: list[int] = Field(default_factory=list)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Discount name cannot be blank.")
        return value

    @field_validator("value")
    @classmethod
    def validate_value_precision(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value != value.quantize(Decimal("0.01")):
            raise ValueError("Discount value must be finite and have at most two decimal places.")
        return value

    @model_validator(mode="after")
    def validate_rules(self):
        if self.discount_type == DiscountType.PERCENT and self.value > 100:
            raise ValueError("Percentage discounts cannot exceed 100%.")
        if self.discount_type == DiscountType.FIXED and self.value != self.value.to_integral_value():
            raise ValueError("Fixed discounts must be supplied as an integer amount in paise.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date.")
        if self.applies_to == DiscountApplicability.PRODUCTS and not self.product_ids:
            raise ValueError("Select at least one product for a product-specific discount.")
        if self.applies_to == DiscountApplicability.SUBSCRIPTION and self.product_ids:
            raise ValueError("Product IDs are only valid for product-specific discounts.")
        if any(product_id < 1 for product_id in self.product_ids):
            raise ValueError("Product IDs must be positive integers.")
        if len(set(self.product_ids)) != len(self.product_ids):
            raise ValueError("Product IDs must not contain duplicates.")
        return self


class DiscountCreate(DiscountFields):
    pass


class DiscountUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    discount_type: Optional[DiscountType] = None
    value: Optional[Decimal] = Field(default=None, gt=0)
    min_purchase: Optional[int] = Field(default=None, ge=0, strict=True)
    min_qty: Optional[int] = Field(default=None, ge=1, strict=True)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    usage_limit: Optional[int] = Field(default=None, ge=1, strict=True)
    applies_to: Optional[DiscountApplicability] = None
    product_ids: Optional[list[int]] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Discount name cannot be blank.")
        return value

    @field_validator("value")
    @classmethod
    def validate_value_precision(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is not None and (
            not value.is_finite() or value != value.quantize(Decimal("0.01"))
        ):
            raise ValueError("Discount value must be finite and have at most two decimal places.")
        return value

    @model_validator(mode="after")
    def validate_combined_rules(self):
        if self.discount_type == DiscountType.PERCENT and self.value is not None and self.value > 100:
            raise ValueError("Percentage discounts cannot exceed 100%.")
        if (
            self.discount_type == DiscountType.FIXED
            and self.value is not None
            and self.value != self.value.to_integral_value()
        ):
            raise ValueError("Fixed discounts must be supplied as an integer amount in paise.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date.")
        if self.applies_to == DiscountApplicability.PRODUCTS and self.product_ids == []:
            raise ValueError("Select at least one product for a product-specific discount.")
        if self.applies_to == DiscountApplicability.SUBSCRIPTION and self.product_ids:
            raise ValueError("Product IDs are only valid for product-specific discounts.")
        if self.product_ids is not None:
            if any(product_id < 1 for product_id in self.product_ids):
                raise ValueError("Product IDs must be positive integers.")
            if len(set(self.product_ids)) != len(self.product_ids):
                raise ValueError("Product IDs must not contain duplicates.")
        return self


class DiscountResponse(DiscountFields):
    id: int
    used_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscountValidateRequest(BaseModel):
    discount_id: int = Field(ge=1)
    subtotal: int = Field(ge=0, strict=True, description="Subtotal in paise")
    quantity: int = Field(default=1, ge=1, strict=True)
    applies_to: DiscountApplicability
    product_ids: list[int] = Field(default_factory=list)


class DiscountValidateResponse(BaseModel):
    discount_id: int
    subtotal: int
    discount_amount: int
    total: int
