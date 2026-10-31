from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.discount import (
    DiscountCreate,
    DiscountResponse,
    DiscountUpdate,
    DiscountValidateRequest,
    DiscountValidateResponse,
)
from app.services import discount as discount_service

router = APIRouter(tags=["Discounts"])


@router.post("", response_model=DiscountResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DiscountResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_discount(discount_in: DiscountCreate, db: Session = Depends(get_db)):
    if discount_service.get_discount_by_name(db, discount_in.name):
        raise HTTPException(status_code=400, detail="A discount with this name already exists.")
    try:
        return discount_service.create_discount(db, discount_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[DiscountResponse])
@router.get("/", response_model=list[DiscountResponse], include_in_schema=False)
def list_discounts(
    is_active: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
):
    return discount_service.get_discounts(db, is_active=is_active)


@router.post("/validate", response_model=DiscountValidateResponse)
def validate_discount(
    request: DiscountValidateRequest,
    db: Session = Depends(get_db),
):
    discount = discount_service.get_discount_by_id(db, request.discount_id)
    if discount is None:
        raise HTTPException(status_code=404, detail="Discount not found.")
    try:
        amount = discount_service.calculate_discount(
            discount=discount,
            subtotal=request.subtotal,
            quantity=request.quantity,
            applies_to=request.applies_to.value,
            product_ids=request.product_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DiscountValidateResponse(
        discount_id=discount.id,
        subtotal=request.subtotal,
        discount_amount=amount,
        total=request.subtotal - amount,
    )


@router.get("/{discount_id}", response_model=DiscountResponse)
def get_discount(discount_id: int, db: Session = Depends(get_db)):
    discount = discount_service.get_discount_by_id(db, discount_id)
    if discount is None:
        raise HTTPException(status_code=404, detail="Discount not found.")
    return discount


@router.put("/{discount_id}", response_model=DiscountResponse)
def update_discount(
    discount_id: int,
    discount_in: DiscountUpdate,
    db: Session = Depends(get_db),
):
    discount = discount_service.get_discount_by_id(db, discount_id)
    if discount is None:
        raise HTTPException(status_code=404, detail="Discount not found.")
    if discount_in.name and discount_in.name.lower() != discount.name.lower():
        existing = discount_service.get_discount_by_name(db, discount_in.name)
        if existing and existing.id != discount_id:
            raise HTTPException(status_code=400, detail="A discount with this name already exists.")
    try:
        return discount_service.update_discount(db, discount, discount_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{discount_id}", response_model=DiscountResponse)
def deactivate_discount(discount_id: int, db: Session = Depends(get_db)):
    discount = discount_service.get_discount_by_id(db, discount_id)
    if discount is None:
        raise HTTPException(status_code=404, detail="Discount not found.")
    if not discount.is_active:
        raise HTTPException(status_code=400, detail="Discount is already inactive.")
    return discount_service.deactivate_discount(db, discount)
