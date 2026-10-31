"""
auth.py — Authentication endpoints for Brightloop Subscription Management System.
Provides user registration, credential authentication, JWT token issuance, and profile retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import UserSignup, UserResponse, UserLogin, Token
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
