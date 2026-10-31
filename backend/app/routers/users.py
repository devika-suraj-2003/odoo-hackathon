"""
users.py — User management endpoints for Brightloop Subscription Management System.
Supports Customers and Staff management pages.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import CustomerCreate, StaffCreate, UserResponse
from app.core.security import get_password_hash
from app.core.dependencies import require_admin

router = APIRouter(tags=["Users"])

SUPPORTED_ROLES = {"customer", "staff"}


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List users filtered by role (customer or staff)",
)
def list_users(
    role: Optional[str] = Query(None, description="Filter users by role: 'customer' or 'staff'"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    List users for management pages:
    - Restricted to administrators (role='admin').
    - Optional role query parameter supports 'customer' and 'staff'.
    - Rejects invalid role values with HTTP 400 Bad Request.
    - Returns safe user fields (id, name, email, role, phone, state, created_at).
    - Never exposes password_hash.
    """
    stmt = select(User)
    if role is not None:
        norm_role = role.strip().lower()
        if norm_role not in SUPPORTED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{role}'. Supported roles are: {', '.join(sorted(SUPPORTED_ROLES))}",
            )
        stmt = stmt.where(User.role == norm_role)

    stmt = stmt.offset(skip).limit(limit)
    users = db.scalars(stmt).all()
    return users


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer account",
)
def create_customer(
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a customer account:
    - Restricted to administrators (role='admin').
    - Accepts name, email, password, phone, and state.
    - Validates password complexity via CustomerCreate schema.
    - Rejects duplicate email registration with HTTP 409 Conflict.
    - Hashes password using bcrypt.
    - Always assigns role='customer' on the backend.
    - Never allows the client to assign admin or staff roles.
    - Returns safe user profile (never exposes password_hash).
    """
    existing_user = db.query(User).filter(User.email == customer_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    new_customer = User(
        name=customer_in.name,
        email=customer_in.email,
        password_hash=get_password_hash(customer_in.password),
        role="customer",
        phone=customer_in.phone,
        state=customer_in.state,
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer


@router.post(
    "/staff",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new staff member account",
)
def create_staff(
    staff_in: StaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a staff account:
    - Restricted to administrators (role='admin').
    - Hashes password using bcrypt.
    - Prevents duplicate email registration returning HTTP 409 Conflict.
    - Always assigns role='staff'.
    - Returns safe user profile (never exposes password_hash).
    """
    existing_user = db.query(User).filter(User.email == staff_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    new_staff = User(
        name=staff_in.name,
        email=staff_in.email,
        password_hash=get_password_hash(staff_in.password),
        role="staff",
        phone=staff_in.phone,
        state=staff_in.state,
    )
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)
    return new_staff
