"""
security.py — Cryptographic and authentication foundation for Brightloop Subscription Management System.
Implements secure password hashing via direct bcrypt and JWT lifecycle operations via python-jose.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Union

import bcrypt
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.core.config import settings


# ==============================================================================
# Password Hashing & Verification (bcrypt)
# ==============================================================================

def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with automatic salt generation.

    Args:
        password: Plaintext password string.

    Returns:
        Formatted bcrypt hash string ($2b$12$...).
    """
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash using constant-time comparison.

    Args:
        plain_password: The plaintext password supplied during authentication.
        hashed_password: The stored bcrypt hash string.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Malformed hash or invalid encoding safely rejected
        return False


# ==============================================================================
# JWT Generation & Decoding (python-jose)
# ==============================================================================

def create_access_token(
    user_id: Union[int, str],
    role: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a signed JWT access token containing the user identity, role, and expiration.

    Args:
        user_id: Unique identifier of the user (stored in 'sub' and 'user_id').
        role: User role (e.g., 'admin', 'staff', 'customer').
        expires_delta: Custom expiration duration. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.
        extra_claims: Optional additional key-value claims to bundle into the token.

    Returns:
        Encoded and signed JWT string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "user_id": user_id,
        "role": str(role),
        "exp": expire,
        "iat": now,
    }

    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt: str = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and cryptographically verify a JWT access token.
    Validates signature integrity, algorithm consistency, and token expiration.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded claims dictionary.

    Raises:
        ExpiredSignatureError: If the token expiration timestamp ('exp') has passed.
        JWTError: If the signature is invalid, malformed, or verification fails.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )


__all__ = [
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "JWTError",
    "ExpiredSignatureError",
]

