"""
plans.py — Subscription Plan management endpoints for Brightloop Subscription Management System.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.plan import Plan
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse
from app.core.dependencies import get_current_user, require_admin

router = APIRouter(tags=["Plans"])


@router.get(
    "",
    response_model=List[PlanResponse],
    summary="List all subscription plans",
)
def list_plans(
    skip: int = Query(0, ge=0, description="Number of plans to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of plans to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve all subscription plans:
    - Accessible to all authenticated users (admin, staff, customer).
    - Supports pagination via skip and limit query parameters.
    - Path: GET /api/plans (collection endpoint without trailing slash).
    """
    stmt = select(Plan).offset(skip).limit(limit)
    plans = db.scalars(stmt).all()
    return plans


@router.get(
    "/{plan_id}",
    response_model=PlanResponse,
    summary="Get subscription plan by ID",
)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a single subscription plan by ID:
    - Accessible to all authenticated users (admin, staff, customer).
    - Returns HTTP 404 if the plan does not exist.
    """
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan with ID {plan_id} not found",
        )
    return plan


@router.post(
    "",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subscription plan",
)
def create_plan(
    plan_in: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new subscription plan:
    - Only administrators can create plans.
    - Validates billing cycle, non-negative price, min_qty >= 1, and date range.
    - Path: POST /api/plans (collection endpoint without trailing slash).
    - Returns HTTP 201 Created with the persisted plan.
    """
    try:
        plan = Plan(
            name=plan_in.name,
            price=plan_in.price,
            billing_period=plan_in.billing_period,
            min_qty=plan_in.min_qty,
            start_date=plan_in.start_date,
            end_date=plan_in.end_date,
            auto_close=plan_in.auto_close,
            closable=plan_in.closable,
            pausable=plan_in.pausable,
            renewable=plan_in.renewable,
            is_active=plan_in.is_active,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create plan: {str(e)}",
        )


@router.put(
    "/{plan_id}",
    response_model=PlanResponse,
    summary="Update a subscription plan",
)
def update_plan(
    plan_id: int,
    plan_in: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update an existing subscription plan:
    - Only administrators can update plans.
    - Validates effective date range when start_date or end_date is updated.
    - Returns HTTP 404 if plan does not exist.
    - Returns updated plan.
    """
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan with ID {plan_id} not found",
        )

    # Check effective start_date and end_date consistency
    effective_start = plan_in.start_date if plan_in.start_date is not None else plan.start_date
    effective_end = plan_in.end_date if plan_in.end_date is not None else plan.end_date
    if effective_start is not None and effective_end is not None and effective_end < effective_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot be earlier than start_date",
        )

    try:
        update_data = plan_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)

        db.commit()
        db.refresh(plan)
        return plan
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update plan: {str(e)}",
        )


@router.delete(
    "/{plan_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a subscription plan",
)
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Safely delete a subscription plan:
    - Only administrators can delete plans.
    - Returns HTTP 404 if plan not found.
    """
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan with ID {plan_id} not found",
        )

    try:
        db.delete(plan)
        db.commit()
        return {
            "status": "ok",
            "message": f"Plan with ID {plan_id} deleted successfully",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete plan: {str(e)}",
        )
