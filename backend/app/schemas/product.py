"""
product.py — Pydantic schemas for Product and ProductVariant management.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# ProductVariant Schemas
# ==============================================================================

class ProductVariantCreate(BaseModel):
    """
    Schema for creating or supplying a product variant.
    Includes optional id to support updating existing variants during product updates.
    """
    id: Optional[int] = Field(None, description="Optional variant ID when updating an existing variant")
    attribute: str = Field(..., min_length=1, max_length=100, description="Attribute name, e.g. Brand, Size, Color")
    value: str = Field(..., min_length=1, max_length=100, description="Attribute value, e.g. Odoo, XL, Blue")
    extra_price: int = Field(default=0, ge=0, description="Additional price in paise (e.g. ₹560 = 56000)")


class ProductVariantResponse(BaseModel):
    """
    Response schema for product variants.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    attribute: str
    value: str
    extra_price: int


# ==============================================================================
# Product Schemas
# ==============================================================================

class ProductCreate(BaseModel):
    """
    Schema for creating a new product with optional nested variants.
    Prices are represented as integers in paise (e.g. ₹499 = 49900).
    """
    name: str = Field(..., min_length=1, max_length=150, description="Product name")
    type: str = Field(..., min_length=1, max_length=100, description="Product type or category")
    sales_price: int = Field(..., ge=0, description="Sales price in paise")
    cost_price: int = Field(..., ge=0, description="Cost price in paise")
    notes: Optional[str] = Field(None, description="Optional description or internal notes")
    variants: List[ProductVariantCreate] = Field(default_factory=list, description="List of nested product variants")


class ProductUpdate(BaseModel):
    """
    Schema for updating an existing product and synchronizing its nested variants.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=150, description="Updated product name")
    type: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated product type")
    sales_price: Optional[int] = Field(None, ge=0, description="Updated sales price in paise")
    cost_price: Optional[int] = Field(None, ge=0, description="Updated cost price in paise")
    notes: Optional[str] = Field(None, description="Updated notes")
    variants: Optional[List[ProductVariantCreate]] = Field(
        None,
        description="Updated list of variants. When provided, replaces the product's variants list.",
    )


class ProductResponse(BaseModel):
    """
    Public response schema for products including nested variants.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    sales_price: int
    cost_price: int
    notes: Optional[str] = None
    variants: List[ProductVariantResponse] = Field(default_factory=list)

