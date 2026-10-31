"""
auth.py — Authentication endpoints for Brightloop Subscription Management System.
Provides user registration, credential authentication, JWT token issuance, profile retrieval,
and password recovery flows (forgot-password, reset-password).
"""

from datetime import datetime, timezone, timedelta
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.schemas import (
    UserSignup,
    UserResponse,
    UserLogin,
    Token,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(tags=["Auth"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer account",
)
def signup(user_in: UserSignup, db: Session = Depends(get_db)):
    """
    Register a new customer:
    - Accepts name, email, password, phone, and state.
    - Normalizes email and validates password strength via UserSignup schema.
    - Hashes password using bcrypt.
    - Always assigns role="customer".
    - Enforces duplicate email prevention returning HTTP 409 Conflict.
    - Never exposes password_hash in the response.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role="customer",
        phone=user_in.phone,
        state=user_in.state,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and obtain JWT access token",
)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user:
    - Accepts email and password.
    - Verifies password against stored bcrypt hash using constant-time comparison.
    - Returns signed JWT containing user ID and role.
    - Returns generic HTTP 401 error on invalid credentials.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user_id=user.id, role=user.role)
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get authenticated user profile",
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve authenticated user profile:
    - Requires a valid, non-expired Bearer JWT.
    - Returns safe profile (never exposes password_hash).
    - Automatically rejects expired or invalid tokens with HTTP 401.
    """
    return current_user


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request a password reset link",
)
def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Initiate password reset:
    - Accepts email address.
    - Generates a secure single-use reset token with a 30-minute expiry.
    - Generates frontend link: http://localhost:5173/reset?token=...
    - Prints link to terminal (simulating email dispatch).
    - Returns generic message to prevent email enumeration.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if user:
        token_str = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_str,
            expires_at=expires_at,
            used=False,
        )
        db.add(reset_token)
        db.commit()

        reset_link = f"http://localhost:5173/reset?token={token_str}"
        print(f"\n[PASSWORD RESET EMAIL SIMULATION]")
        print(f"Recipient: {user.email}")
        print(f"Reset Link: {reset_link}")
        print(f"Expires At: {expires_at.isoformat()}\n", flush=True)

    return {
        "status": "ok",
        "message": "If an account with this email exists, a password reset link has been sent.",
    }


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password using reset token",
)
def reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """
    Complete password reset:
    - Validates token against database.
    - Rejects invalid tokens (HTTP 400).
    - Rejects already used tokens (HTTP 400).
    - Rejects expired tokens (HTTP 400).
    - Updates user password hash with the new password.
    - Marks token as used.
    """
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == request.token)
        .first()
    )
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if reset_token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has already been used",
        )

    # Check expiration safely handling naive/aware datetimes
    now_utc = datetime.now(timezone.utc)
    token_exp = reset_token.expires_at
    if token_exp.tzinfo is None:
        token_exp = token_exp.replace(tzinfo=timezone.utc)

    if now_utc > token_exp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has expired",
        )

    # Fetch corresponding user
    user = db.get(User, reset_token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        user.password_hash = get_password_hash(request.new_password)
        reset_token.used = True
        db.commit()
        return {
            "status": "ok",
            "message": "Password reset successfully",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}",
        )
