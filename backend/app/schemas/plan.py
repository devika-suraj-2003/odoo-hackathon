"""
plan.py — Pydantic v2 schemas for Subscription Plan management.
"""

from datetime import date
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SUPPORTED_BILLING_PERIODS = ("daily", "weekly", "monthly", "yearly")
BillingPeriodType = Literal["daily", "weekly", "monthly", "yearly"]


# ==============================================================================
# Plan Create Schema
# ==============================================================================

class PlanCreate(BaseModel):
    """
    Schema for creating a new subscription plan.
    Monetary values (price) are stored in paise (e.g. ₹999 = 99900).
    """
    name: str = Field(..., min_length=1, max_length=150, description="Plan name")
    price: int = Field(..., ge=0, description="Price in paise (must not be negative, e.g. ₹999 = 99900)")
    billing_period: BillingPeriodType = Field(
        ...,
        description="Billing cycle: 'daily', 'weekly', 'monthly', or 'yearly'",
    )
    min_qty: int = Field(
        default=1,
        ge=1,
        description="Minimum subscription quantity (must be at least 1)",
    )
    start_date: date = Field(..., description="Date when plan becomes available")
    end_date: Optional[date] = Field(
        default=None,
        description="Optional date when plan expires (must be on or after start_date)",
    )
    auto_close: bool = Field(
        default=False,
        description="Automatically close expired subscription",
    )
    closable: bool = Field(
        default=True,
        description="Allow user or admin to close the subscription",
    )
    pausable: bool = Field(
        default=True,
        description="Allow user or admin to pause the subscription",
    )
    renewable: bool = Field(
        default=True,
        description="Allow subscription to renew upon expiration",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this plan is currently active for subscriptions",
    )

    @field_validator("billing_period", mode="before")
    @classmethod
    def validate_billing_period(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_norm = v.strip().lower()
            if v_norm not in SUPPORTED_BILLING_PERIODS:
                raise ValueError(
                    f"Invalid billing_period '{v}'. Must be one of: {', '.join(SUPPORTED_BILLING_PERIODS)}"
                )
            return v_norm
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "PlanCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date")
        return self


# ==============================================================================
# Plan Update Schema
# ==============================================================================

class PlanUpdate(BaseModel):
    """
    Schema for updating an existing subscription plan.
    All fields are optional.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=150, description="Updated plan name")
    price: Optional[int] = Field(None, ge=0, description="Updated price in paise (must not be negative)")
    billing_period: Optional[BillingPeriodType] = Field(
        None,
        description="Updated billing cycle: 'daily', 'weekly', 'monthly', or 'yearly'",
    )
    min_qty: Optional[int] = Field(
        None,
        ge=1,
        description="Updated minimum subscription quantity (must be at least 1)",
    )
    start_date: Optional[date] = Field(None, description="Updated start date")
    end_date: Optional[date] = Field(None, description="Updated end date")
    auto_close: Optional[bool] = Field(None, description="Updated auto_close flag")
    closable: Optional[bool] = Field(None, description="Updated closable flag")
    pausable: Optional[bool] = Field(None, description="Updated pausable flag")
    renewable: Optional[bool] = Field(None, description="Updated renewable flag")
    is_active: Optional[bool] = Field(None, description="Updated is_active flag")

    @field_validator("billing_period", mode="before")
    @classmethod
    def validate_billing_period(cls, v: Any) -> Any:
        if v is not None and isinstance(v, str):
            v_norm = v.strip().lower()
            if v_norm not in SUPPORTED_BILLING_PERIODS:
                raise ValueError(
                    f"Invalid billing_period '{v}'. Must be one of: {', '.join(SUPPORTED_BILLING_PERIODS)}"
                )
            return v_norm
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "PlanUpdate":
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date cannot be earlier than start_date")
        return self


# ==============================================================================
# Plan Response Schema
# ==============================================================================

class PlanResponse(BaseModel):
    """
    Public response schema for subscription plans.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: int
    billing_period: str
    min_qty: int
    start_date: date
    end_date: Optional[date] = None
    auto_close: bool
    closable: bool
    pausable: bool
    renewable: bool
    is_active: bool

