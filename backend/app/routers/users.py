"""
users.py — User management endpoints for Brightloop Subscription Management System.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import StaffCreate, UserResponse
from app.core.security import get_password_hash
from app.core.dependencies import require_admin

router = APIRouter(tags=["Users"])


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
    # Check for duplicate email
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
