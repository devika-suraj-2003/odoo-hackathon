"""
user.py — Pydantic schemas for user signup, creation, and profile responses.
"""

from datetime import datetime
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Standard email regex pattern using built-in re (no external email-validator package required)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email_address(value: str) -> str:
    """Normalize and validate email format."""
    if not isinstance(value, str):
        raise ValueError("Email must be a string.")
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("Email cannot be empty.")
    if not EMAIL_REGEX.match(normalized):
        raise ValueError("Invalid email format.")
    return normalized


def validate_password_rules(value: str) -> str:
    """
    Validate password requirements:
    - More than 8 characters long
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one special character
    """
    if not isinstance(value, str):
        raise TypeError("Password must be a string.")
    if len(value) <= 8:
        raise ValueError("Password must be more than 8 characters long.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must contain at least one special character.")
    return value


# ==============================================================================
# User Schemas
# ==============================================================================

class UserSignup(BaseModel):
    """
    Schema for public customer signup requests.
    Explicitly forbids the 'role' field; new public users are always customers.
    """
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=150, description="Full name of the user")
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Plaintext password meeting complexity criteria")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    state: Optional[str] = Field(None, max_length=100, description="State or province")

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, v: str) -> str:
        return validate_email_address(v)

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        return validate_password_rules(v)


class CustomerCreate(UserSignup):
    """
    Schema for administrator-driven customer creation (POST /api/users).
    Explicitly forbids client-assigned roles; always assigned role='customer' on backend.
    """
    pass


class StaffCreate(BaseModel):
    """
    Schema for administrator-driven staff member creation (POST /users/staff).
    """
    name: str = Field(..., min_length=1, max_length=150, description="Full name of the staff member")
    email: str = Field(..., description="Staff member email address")
    password: str = Field(..., description="Temporary or initial plaintext password")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    state: Optional[str] = Field(None, max_length=100, description="State or province")

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, v: str) -> str:
        return validate_email_address(v)

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        return validate_password_rules(v)


class UserResponse(BaseModel):
    """
    Public response schema for user profiles.
    Never exposes password_hash.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    phone: Optional[str] = None
    state: Optional[str] = None
    created_at: datetime

