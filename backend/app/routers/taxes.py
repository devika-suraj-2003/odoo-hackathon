"""
Tax Management Router.

Mounted under /api/taxes.
Provides endpoints for creating, listing, retrieving, updating, deactivating
tax rules, and calculating exact taxes and Indian GST in integer paise.
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.tax import (
    TaxCreate,
    TaxUpdate,
    TaxResponse,
    TaxCalculateRequest,
    TaxCalculateResponse,
    GSTBreakdown,
)
from app.services import tax as tax_service

router = APIRouter()


@router.post(
    "",
    response_model=TaxResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tax rule",
)
@router.post(
    "/",
    response_model=TaxResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_tax(
    tax_in: TaxCreate,
    db: Session = Depends(get_db),
) -> TaxResponse:
    """
    Create a new tax rule.

    - **name**: Unique name for the tax (e.g. 'GST 18%').
    - **rate**: Percentage rate between 0.00 and 100.00 (e.g. 18.00).
    - **tax_type**: Tax type ('gst', 'vat', 'sales_tax', 'exempt', 'other').
    - **description**: Optional details on applicability.
    - **is_active**: True by default.
    """
    existing = tax_service.get_tax_by_name(db, tax_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A tax rule named '{tax_in.name}' already exists with ID {existing.id}.",
        )

    return tax_service.create_tax(db, tax_in)


@router.get(
    "",
    response_model=List[TaxResponse],
    summary="List all tax rules",
)
@router.get(
    "/",
    response_model=List[TaxResponse],
    include_in_schema=False,
)
def list_taxes(
    is_active: Annotated[
        Optional[bool],
        Query(
            description="Filter by active status (true: active only, false: deactivated only)"
        ),
    ] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=500, description="Max number of records to return")
    ] = 100,
    db: Session = Depends(get_db),
) -> List[TaxResponse]:
    """Retrieve all configured taxes with optional pagination and active-state filtering."""
    return tax_service.get_taxes(db, skip=skip, limit=limit, is_active=is_active)


@router.get(
    "/{tax_id}",
    response_model=TaxResponse,
    summary="Retrieve a tax rule by ID",
)
def get_tax(
    tax_id: int,
    db: Session = Depends(get_db),
) -> TaxResponse:
    """Retrieve details of a specific tax rule by its unique ID."""
    tax = tax_service.get_tax_by_id(db, tax_id)
    if not tax:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tax rule with ID {tax_id} was not found.",
        )
    return tax


@router.put(
    "/{tax_id}",
    response_model=TaxResponse,
    summary="Update an existing tax rule",
)
def update_tax(
    tax_id: int,
    tax_in: TaxUpdate,
    db: Session = Depends(get_db),
) -> TaxResponse:
    """Update fields of an existing tax rule."""
    tax = tax_service.get_tax_by_id(db, tax_id)
    if not tax:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tax rule with ID {tax_id} was not found.",
        )

    # If updating the name, ensure no other record uses the same name
    if tax_in.name and tax_in.name.strip().lower() != tax.name.lower():
        conflict = tax_service.get_tax_by_name(db, tax_in.name)
        if conflict and conflict.id != tax_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another tax rule named '{tax_in.name}' already exists with ID {conflict.id}.",
            )

    return tax_service.update_tax(db, tax, tax_in)


@router.delete(
    "/{tax_id}",
    response_model=TaxResponse,
    summary="Deactivate a tax rule (Soft Delete)",
)
def deactivate_tax(
    tax_id: int,
    db: Session = Depends(get_db),
) -> TaxResponse:
    """
    Deactivate a tax rule instead of permanently deleting it.
    Preserves audit trails and references for historical invoices.
    """
    tax = tax_service.get_tax_by_id(db, tax_id)
    if not tax:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tax rule with ID {tax_id} was not found.",
        )

    if not tax.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tax rule with ID {tax_id} is already deactivated.",
        )

    return tax_service.deactivate_tax(db, tax)


@router.post(
    "/calculate",
    response_model=TaxCalculateResponse,
    summary="Calculate tax amount in integer paise with Indian GST split",
)
def calculate_tax_endpoint(
    calc_in: TaxCalculateRequest,
    db: Session = Depends(get_db),
) -> TaxCalculateResponse:
    """
    Calculate exact tax for a transaction subtotal in paise.

    - **subtotal_paise**: Subtotal in integer paise (e.g. ₹100 = 10000 paise).
    - Provide either **tax_id** (to fetch registered rate) or **tax_rate** (direct custom rate).
    - **customer_state**: (Optional) Customer's state. When provided, calculates Indian GST
      intra-state split (CGST + SGST) or inter-state (IGST) against configured company state.
    """
    if calc_in.tax_id is not None:
        tax = tax_service.get_tax_by_id(db, calc_in.tax_id)
        if not tax:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tax rule with ID {calc_in.tax_id} was not found.",
            )
        rate = tax.rate
    elif calc_in.tax_rate is not None:
        rate = calc_in.tax_rate
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'tax_id' or 'tax_rate' must be specified in calculation request.",
        )

    try:
        if calc_in.customer_state and calc_in.customer_state.strip():
            gst_res = tax_service.calculate_gst(
                subtotal_paise=calc_in.subtotal_paise,
                tax_rate=rate,
                customer_state=calc_in.customer_state,
            )
            return TaxCalculateResponse(
                subtotal_paise=gst_res["subtotal_paise"],
                effective_tax_rate=gst_res["effective_tax_rate"],
                tax_amount_paise=gst_res["tax_amount_paise"],
                total_paise=gst_res["total_paise"],
                rounding_rule=gst_res["rounding_rule"],
                gst_breakdown=GSTBreakdown(**gst_res["gst_breakdown"]),
            )
        else:
            std_res = tax_service.calculate_tax(
                subtotal_paise=calc_in.subtotal_paise,
                tax_rate=rate,
            )
            return TaxCalculateResponse(
                subtotal_paise=std_res["subtotal_paise"],
                effective_tax_rate=std_res["tax_rate"],
                tax_amount_paise=std_res["tax_amount_paise"],
                total_paise=std_res["total_paise"],
                rounding_rule=std_res["rounding_rule"],
                gst_breakdown=None,
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
