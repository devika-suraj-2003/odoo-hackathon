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
from app.schemas.user import CustomerCreate, StaffCreate, UserResponse, UserUpdate
from app.core.security import get_password_hash
from app.core.dependencies import require_admin, require_staff_or_admin

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
    current_user: User = Depends(require_staff_or_admin),
):
    """
    List users for management pages:
    - Accessible to authenticated staff and admin users (per frontend route permissions).
    - Accepts optional role query parameter: 'customer' or 'staff'.
    - Rejects invalid role values with HTTP 400 Bad Request.
    - Returns a JSON array of safe user fields (id, name, email, role, phone, state, created_at).
    - Returns an empty array if no matching users exist.
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
    current_user: User = Depends(require_staff_or_admin),
):
    """
    Create a customer account:
    - Accessible to staff and admin users.
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
        role="customer",  # Always customer
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


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update customer or staff details (admin only)",
)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update a user profile:
    - Restricted to administrators (role='admin').
    - Updates name, email, phone, state, and optional new password.
    - Rejects duplicate email with HTTP 409 Conflict.
    - Hashes password if provided.
    - Never exposes password_hash in response.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check for email conflict
    if user_in.email is not None and user_in.email.strip().lower() != user.email.lower():
        norm_email = user_in.email.strip().lower()
        conflict = db.query(User).filter(User.email == norm_email, User.id != user_id).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )
        user.email = norm_email

    if user_in.name is not None:
        user.name = user_in.name.strip()

    if user_in.phone is not None:
        user.phone = user_in.phone.strip() if user_in.phone else None

    if user_in.state is not None:
        user.state = user_in.state.strip() if user_in.state else None

    if user_in.password:
        user.password_hash = get_password_hash(user_in.password)

    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    summary="Delete a customer or staff user (admin only)",
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete a user account:
    - Restricted to administrators (role='admin').
    - Prevents admin from deleting their own account (HTTP 400).
    - Safely removes associated records (subscriptions, lines, invoices, payments, reset tokens)
      to maintain foreign-key referential integrity.
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own admin account",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Clean up associated records before deleting user:
    from app.models.subscription import Subscription, SubscriptionLine, SubscriptionHistory
    from app.models.invoice import Invoice, InvoiceLine
    from app.models.payment import Payment
    from app.models.razorpay_order import RazorpayOrder
    from app.models.password_reset_token import PasswordResetToken

    # 1. Subscriptions where customer_id == user_id
    subscriptions = db.query(Subscription).filter(Subscription.customer_id == user_id).all()
    for sub in subscriptions:
        sub_invoices = db.query(Invoice).filter(Invoice.subscription_id == sub.id).all()
        for inv in sub_invoices:
            db.query(RazorpayOrder).filter(RazorpayOrder.invoice_id == inv.id).delete()
            db.query(Payment).filter(Payment.invoice_id == inv.id).delete()
            db.query(InvoiceLine).filter(InvoiceLine.invoice_id == inv.id).delete()
            db.delete(inv)
        db.query(SubscriptionLine).filter(SubscriptionLine.subscription_id == sub.id).delete()
        db.query(SubscriptionHistory).filter(SubscriptionHistory.subscription_id == sub.id).delete()
        db.delete(sub)

    # 2. Invoices directly linked to customer_id == user_id (if any without subscription)
    user_invoices = db.query(Invoice).filter(Invoice.customer_id == user_id).all()
    for inv in user_invoices:
        db.query(RazorpayOrder).filter(RazorpayOrder.invoice_id == inv.id).delete()
        db.query(Payment).filter(Payment.invoice_id == inv.id).delete()
        db.query(InvoiceLine).filter(InvoiceLine.invoice_id == inv.id).delete()
        db.delete(inv)

    # 3. Clear changed_by in subscription history
    db.query(SubscriptionHistory).filter(SubscriptionHistory.changed_by == user_id).update(
        {SubscriptionHistory.changed_by: None}
    )

    # 4. Remove password reset tokens
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()

    # 5. Delete the user
    db.delete(user)
    db.commit()
    return {"detail": "User deleted successfully", "id": user_id}
