"""
auth.py — Pydantic schemas for authentication, token issuance, and password recovery.
"""

from pydantic import BaseModel, Field, field_validator

from app.schemas.user import validate_email_address, validate_password_rules


# ==============================================================================
# Authentication Schemas
# ==============================================================================

class UserLogin(BaseModel):
    """
    Schema for user authentication requests (POST /auth/login).
    """
    email: str = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, v: str) -> str:
        return validate_email_address(v)


class Token(BaseModel):
    """
    Schema for JWT access token responses.
    """
    access_token: str = Field(..., description="Encoded JWT access token")
    token_type: str = Field(default="bearer", description="Token authentication scheme")


class PasswordResetRequest(BaseModel):
    """
    Schema for initiating a password reset (POST /auth/forgot-password).
    """
    email: str = Field(..., description="Email address associated with the account")

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, v: str) -> str:
        return validate_email_address(v)


class PasswordResetConfirm(BaseModel):
    """
    Schema for completing a password reset using a token (POST /auth/reset-password).
    """
    token: str = Field(..., min_length=1, description="Single-use password reset token")
    new_password: str = Field(..., description="New password meeting complexity criteria")

    @field_validator("new_password")
    @classmethod
    def check_new_password_complexity(cls, v: str) -> str:
        return validate_password_rules(v)

