"""
Tax Management Service.

Provides financial calculations for taxes and Indian GST using exact Decimal
arithmetic and integer paise (1 Rupee = 100 Paise), along with CRUD operations,
seed data handling, and integration helpers for Invoices & Subscriptions.
"""

import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.tax import Tax
from app.schemas.tax import TaxCreate, TaxUpdate


ROUNDING_RULE_DESCRIPTION = "ROUND_HALF_UP to nearest 1 paise (0.50 paise rounds up)"


def get_company_state() -> str:
    """Retrieve company operating state for GST jurisdiction from environment."""
    return os.getenv("COMPANY_STATE", "Kerala").strip() or "Kerala"


# ==============================================================================
# FINANCIAL CALCULATION CORE
# ==============================================================================

def calculate_tax(
    subtotal_paise: int,
    tax_rate: Decimal,
) -> Dict[str, Any]:
    """
    Calculate tax for a given subtotal in paise and tax rate percentage.

    Rules:
    - Monetary amounts are strictly integer paise.
    - Tax rate is a Decimal percentage (e.g., Decimal("18.00") for 18%).
    - Calculations are executed using Python's Decimal arithmetic to eliminate
      binary floating-point precision errors.
    - Tax amount is rounded to the nearest integer paise using ROUND_HALF_UP.

    Args:
        subtotal_paise: Non-negative integer representing the amount in paise.
        tax_rate: Decimal percentage between 0 and 100.

    Returns:
        dict containing subtotal_paise, tax_rate, tax_amount_paise, total_paise.
    """
    if subtotal_paise < 0:
        raise ValueError("subtotal_paise cannot be negative.")
    if not tax_rate.is_finite():
        raise ValueError("tax_rate must be a finite number.")
    if not (Decimal("0.0") <= tax_rate <= Decimal("100.0")):
        raise ValueError("tax_rate must be between 0.00 and 100.00 percent.")

    # (subtotal * rate) / 100
    subtotal_dec = Decimal(subtotal_paise)
    tax_dec = (subtotal_dec * tax_rate) / Decimal("100")

    # Round to nearest integer paise using ROUND_HALF_UP
    tax_paise = int(tax_dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    total_paise = subtotal_paise + tax_paise

    return {
        "subtotal_paise": subtotal_paise,
        "tax_rate": tax_rate,
        "tax_amount_paise": tax_paise,
        "total_paise": total_paise,
        "rounding_rule": ROUNDING_RULE_DESCRIPTION,
    }


def calculate_gst(
    subtotal_paise: int,
    tax_rate: Decimal,
    customer_state: str,
    company_state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate Indian Goods and Services Tax (GST) with state-based breakdown.

    Rules:
    - Intra-State (Customer State == Company State):
        GST is equally divided into Central GST (CGST) and State GST (SGST).
        For an 18% rate, CGST is 9% and SGST is 9%.
    - Inter-State (Customer State != Company State):
        Integrated GST (IGST) applies at the full tax rate (18% IGST).
    - Company location is retrieved from environment variable COMPANY_STATE.

    Args:
        subtotal_paise: Subtotal amount in integer paise.
        tax_rate: GST rate percentage (e.g. Decimal("18.00")).
        customer_state: State where customer is registered.
        company_state: Optional company operating state override.

    Returns:
        dict containing full tax calculation plus GST breakdown.
    """
    if not customer_state or not customer_state.strip():
        raise ValueError("customer_state is required for GST calculation.")

    base_calculation = calculate_tax(subtotal_paise, tax_rate)
    effective_company_state = (company_state or get_company_state()).strip()
    cust_state_clean = customer_state.strip()

    is_intra_state = cust_state_clean.lower() == effective_company_state.lower()

    if is_intra_state:
        # Split into equal halves for CGST and SGST
        half_rate = tax_rate / Decimal("2")
        cgst_dec = (Decimal(subtotal_paise) * half_rate) / Decimal("100")
        cgst_paise = int(cgst_dec.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        sgst_paise = base_calculation["tax_amount_paise"] - cgst_paise
        igst_paise = 0
        igst_rate = Decimal("0.0")
        cgst_rate = half_rate
        sgst_rate = half_rate
        tax_amount_paise = base_calculation["tax_amount_paise"]
    else:
        # Full rate applies as IGST
        igst_rate = tax_rate
        igst_paise = base_calculation["tax_amount_paise"]
        cgst_paise = 0
        sgst_paise = 0
        cgst_rate = Decimal("0.0")
        sgst_rate = Decimal("0.0")
        tax_amount_paise = igst_paise

    total_paise = subtotal_paise + tax_amount_paise

    return {
        "subtotal_paise": subtotal_paise,
        "effective_tax_rate": tax_rate,
        "tax_amount_paise": tax_amount_paise,
        "total_paise": total_paise,
        "rounding_rule": ROUNDING_RULE_DESCRIPTION,
        "gst_breakdown": {
            "is_intra_state": is_intra_state,
            "company_state": effective_company_state,
            "customer_state": cust_state_clean,
            "cgst_rate": cgst_rate,
            "cgst_amount_paise": cgst_paise,
            "sgst_rate": sgst_rate,
            "sgst_amount_paise": sgst_paise,
            "igst_rate": igst_rate,
            "igst_amount_paise": igst_paise,
        },
    }


# ==============================================================================
# INTEGRATION HELPERS (FOR INVOICES & SUBSCRIPTIONS)
# ==============================================================================

def apply_tax_to_amount(
    subtotal_paise: int,
    tax: Tax,
    customer_state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reusable helper for teammates' Invoice and Subscription modules.
    Applies a Tax model record to an amount in integer paise.
    """
    if not tax.is_active:
        raise ValueError(f"Tax rule '{tax.name}' (ID: {tax.id}) is deactivated and cannot be applied.")

    rate = Decimal(str(tax.rate))
    if customer_state and tax.tax_type.lower() == "gst":
        return calculate_gst(
            subtotal_paise=subtotal_paise,
            tax_rate=rate,
            customer_state=customer_state,
        )
    return calculate_tax(subtotal_paise=subtotal_paise, tax_rate=rate)


# ==============================================================================
# DATABASE CRUD OPERATIONS
# ==============================================================================

def get_taxes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> List[Tax]:
    """Retrieve list of taxes with optional pagination and active-status filter."""
    query = db.query(Tax)
    if is_active is not None:
        query = query.filter(Tax.is_active == is_active)
    return query.order_by(Tax.id.asc()).offset(skip).limit(limit).all()


def get_tax_by_id(db: Session, tax_id: int) -> Optional[Tax]:
    """Retrieve a tax record by primary key."""
    return db.query(Tax).filter(Tax.id == tax_id).first()


def get_tax_by_name(db: Session, name: str) -> Optional[Tax]:
    """Retrieve a tax record by name, ignoring surrounding whitespace and case."""
    return db.query(Tax).filter(func.lower(Tax.name) == name.strip().lower()).first()


def create_tax(db: Session, tax_in: TaxCreate) -> Tax:
    """Create a new tax record in the database."""
    tax = Tax(
        name=tax_in.name.strip(),
        rate=tax_in.rate,
        tax_type=tax_in.tax_type.value if hasattr(tax_in.tax_type, "value") else str(tax_in.tax_type),
        description=tax_in.description.strip() if tax_in.description else None,
        is_active=tax_in.is_active,
    )
    db.add(tax)
    db.commit()
    db.refresh(tax)
    return tax


def update_tax(db: Session, tax: Tax, tax_in: TaxUpdate) -> Tax:
    """Update fields on an existing tax record."""
    update_data = tax_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "tax_type" and value is not None:
            setattr(tax, field, value.value if hasattr(value, "value") else str(value))
        elif field == "name" and value is not None:
            setattr(tax, field, value.strip())
        elif field == "description" and value is not None:
            setattr(tax, field, value.strip())
        else:
            setattr(tax, field, value)

    db.commit()
    db.refresh(tax)
    return tax


def deactivate_tax(db: Session, tax: Tax) -> Tax:
    """
    Soft-delete / deactivate a tax rule.
    Preserves audit trails and references for historical invoices and subscriptions.
    """
    tax.is_active = False
    db.commit()
    db.refresh(tax)
    return tax


# ==============================================================================
# SEED DATA LOGIC
# ==============================================================================

DEFAULT_TAX_SEEDS = [
    {
        "name": "GST 5%",
        "rate": Decimal("5.00"),
        "tax_type": "gst",
        "description": "Standard Indian GST rate of 5% (Intra-state: 2.5% CGST + 2.5% SGST, Inter-state: 5% IGST)",
        "is_active": True,
    },
    {
        "name": "GST 18%",
        "rate": Decimal("18.00"),
        "tax_type": "gst",
        "description": "Standard Indian GST rate of 18% (Intra-state: 9% CGST + 9% SGST, Inter-state: 18% IGST)",
        "is_active": True,
    },
]


def seed_default_taxes(db: Session) -> List[Tax]:
    """
    Seed initial standard GST tax rates (5% and 18%) if they do not already exist.
    Prevents duplicates on application reloads.
    """
    seeded: List[Tax] = []
    for item in DEFAULT_TAX_SEEDS:
        existing = get_tax_by_name(db, item["name"])
        if not existing:
            new_tax = Tax(
                name=item["name"],
                rate=item["rate"],
                tax_type=item["tax_type"],
                description=item["description"],
                is_active=item["is_active"],
            )
            db.add(new_tax)
            seeded.append(new_tax)

    if seeded:
        db.commit()
        for t in seeded:
            db.refresh(t)

    return seeded
