"""
dependencies.py — Common FastAPI dependencies for authentication and authorization.
Uses HTTPBearer to support direct JWT token authorization in Swagger UI and API requests.
"""

from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import decode_access_token, JWTError, ExpiredSignatureError

# HTTPBearer security scheme: In Swagger UI, this opens an Authorize dialog
# with a single input box to paste the JWT access token directly.
http_bearer = HTTPBearer(
    auto_error=False,
    description="Bearer JWT access token. Paste your access token in Swagger Authorize dialog.",
)


def get_current_user(
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate the incoming JWT access token from HTTP Authorization header,
    extract user identity, and return the corresponding User model instance.

    Raises:
        HTTPException 401: If token is missing, expired, invalid, or user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if auth_credentials is None or not auth_credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token: str = auth_credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id_raw = payload.get("sub") or payload.get("user_id")
        if user_id_raw is None:
            raise credentials_exception
        user_id = int(user_id_raw)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Dependency factory verifying the current authenticated user possesses one of the allowed roles.

    Raises:
        HTTPException 403: If user does not have an authorized role.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker


# Role-based dependency shortcuts
require_admin = require_roles(["admin"])
require_staff_or_admin = require_roles(["admin", "staff"])
