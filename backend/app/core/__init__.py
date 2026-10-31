"""
core package — Centralized configurations, security services, dependencies, and seed utilities.
"""

from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    JWTError,
    ExpiredSignatureError,
)
from app.core.dependencies import (
    get_current_user,
    http_bearer,
    require_roles,
    require_admin,
    require_staff_or_admin,
)
from app.core.seed import seed_admin, seed_dev_accounts

__all__ = [
    "settings",
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "JWTError",
    "ExpiredSignatureError",
    "get_current_user",
    "http_bearer",
    "require_roles",
    "require_admin",
    "require_staff_or_admin",
    "seed_admin",
    "seed_dev_accounts",
]
