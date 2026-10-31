"""
Pydantic Schemas for Tax Management and Calculations.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaxType(str, Enum):
    GST = "gst"
    VAT = "vat"
    SALES_TAX = "sales_tax"
    EXEMPT = "exempt"
    OTHER = "other"


class TaxBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the tax rule (e.g. 'GST 18%')",
        examples=["GST 18%"],
    )
    rate: Decimal = Field(
        ...,
        ge=Decimal("0.0"),
        le=Decimal("100.0"),
        description="Tax rate percentage between 0.00 and 100.00",
        examples=[Decimal("18.00")],
    )
    tax_type: TaxType = Field(
        default=TaxType.GST,
        description="Tax classification ('gst', 'vat', 'sales_tax', 'exempt', 'other')",
        examples=[TaxType.GST],
    )
    description: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional human-readable description of this tax rule",
        examples=["Standard GST rate for SaaS and cloud software subscriptions"],
    )
    is_active: bool = Field(
        default=True,
        description="Whether this tax rule is active and available for billing",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Tax name cannot be blank or whitespace-only.")
        return stripped

    @field_validator("rate")
    @classmethod
    def validate_rate_precision(cls, v: Decimal) -> Decimal:
        if v != v.quantize(Decimal("0.01")):
            raise ValueError("Tax rate can have at most two decimal places.")
        return v


class TaxCreate(TaxBase):
    """Schema for creating a new Tax rule."""
    pass


class TaxUpdate(BaseModel):
    """Schema for updating an existing Tax rule."""
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated tax name",
    )
    rate: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.0"),
        le=Decimal("100.0"),
        description="Updated tax rate percentage (0.00 to 100.00)",
    )
    tax_type: Optional[TaxType] = Field(
        default=None,
        description="Updated tax classification",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated description",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Enable or deactivate this tax rule",
    )

    @field_validator("name")
    @classmethod
    def validate_name_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Tax name cannot be blank or whitespace-only.")
            return stripped
        return v

    @field_validator("rate")
    @classmethod
    def validate_rate_precision(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v != v.quantize(Decimal("0.01")):
            raise ValueError("Tax rate can have at most two decimal places.")
        return v


class TaxResponse(TaxBase):
    """Response schema returning stored tax details."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GSTBreakdown(BaseModel):
    """Detailed breakdown for Indian GST calculations."""
    is_intra_state: bool = Field(
        description="True if customer is in the company state (CGST + SGST apply)"
    )
    company_state: str = Field(description="Configured operating state of the business")
    customer_state: str = Field(description="Billing state of the customer")
    cgst_rate: Decimal = Field(description="Central GST percentage rate")
    cgst_amount_paise: int = Field(description="Central GST amount in integer paise")
    sgst_rate: Decimal = Field(description="State GST percentage rate")
    sgst_amount_paise: int = Field(description="State GST amount in integer paise")
    igst_rate: Decimal = Field(description="Integrated GST percentage rate")
    igst_amount_paise: int = Field(description="Integrated GST amount in integer paise")


class TaxCalculateRequest(BaseModel):
    """Request payload to calculate tax for a subtotal in paise."""
    subtotal_paise: int = Field(
        ...,
        strict=True,
        ge=0,
        description="Transaction subtotal in integer paise (₹100 = 10000 paise)",
        examples=[10000],
    )
    tax_id: Optional[int] = Field(
        default=None,
        strict=True,
        ge=1,
        description="ID of an existing registered Tax rule",
    )
    tax_rate: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.0"),
        le=Decimal("100.0"),
        description="Direct custom tax percentage if tax_id is not specified",
    )
    customer_state: Optional[str] = Field(
        default=None,
        description="Billing state of the customer for Indian GST intra/inter-state split",
        examples=["Kerala", "Maharashtra"],
    )

    @field_validator("customer_state")
    @classmethod
    def validate_customer_state(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Customer state cannot be blank or whitespace-only.")
            return stripped
        return v

    @field_validator("tax_rate")
    @classmethod
    def validate_tax_rate_precision(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v != v.quantize(Decimal("0.01")):
            raise ValueError("Tax rate can have at most two decimal places.")
        return v


class TaxCalculateResponse(BaseModel):
    """Response payload containing exact tax calculation in paise."""
    subtotal_paise: int = Field(description="Original subtotal in integer paise")
    effective_tax_rate: Decimal = Field(description="Applied percentage tax rate")
    tax_amount_paise: int = Field(description="Calculated tax amount in integer paise")
    total_paise: int = Field(description="Final total (subtotal + tax) in integer paise")
    rounding_rule: str = Field(
        default="ROUND_HALF_UP to nearest 1 paise (0.50 paise rounds up)",
        description="Documented commercial rounding rule",
    )
    gst_breakdown: Optional[GSTBreakdown] = Field(
        default=None,
        description="Detailed CGST/SGST/IGST breakdown when customer_state is provided",
    )
