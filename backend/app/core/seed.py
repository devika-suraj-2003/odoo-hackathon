"""
seed.py — Database seeding functions for Brightloop Subscription Management System.
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal, Base, engine
import app.models  # Ensure all four models are registered on Base.metadata
from app.models.user import User
from app.core.security import get_password_hash

# Development accounts configuration (demo/local development only)
DEV_SEED_ACCOUNTS: List[Dict[str, str]] = [
    {
        "name": "System Administrator",
        "email": "admin@brightloop.com",
        "password": "Admin@1234",
        "role": "admin",
    },
    {
        "name": "Brightloop Staff",
        "email": "staff@brightloop.com",
        "password": "Staff@1234",
        "role": "staff",
    },
    {
        "name": "Brightloop Customer",
        "email": "customer@brightloop.com",
        "password": "Customer@1234",
        "role": "customer",
    },
]


def seed_dev_accounts(db: Optional[Session] = None) -> Dict[str, User]:
    """
    Idempotently seeds the three development accounts (Admin, Staff, Customer).

    Accounts:
        - Admin:    admin@brightloop.com    / Admin@1234    (role: admin)
        - Staff:    staff@brightloop.com    / Staff@1234    (role: staff)
        - Customer: customer@brightloop.com / Customer@1234 (role: customer)

    Requirements:
        - Uses the existing User model.
        - Hashes passwords using bcrypt (get_password_hash). Never stores plaintext passwords.
        - Normalizes email addresses (lowercased, trimmed).
        - Prevents duplicate accounts.
        - Does NOT overwrite existing accounts, passwords, or roles.
        - Does NOT expose passwords in logs.
    """
    # Ensure database tables exist before querying or inserting
    Base.metadata.create_all(bind=engine)

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    results: Dict[str, User] = {}
    try:
        for account in DEV_SEED_ACCOUNTS:
            normalized_email = account["email"].strip().lower()
            existing_user = db.query(User).filter(User.email == normalized_email).first()

            if existing_user:
                # Preserve existing account without modifying password or role
                results[account["role"]] = existing_user
            else:
                new_user = User(
                    name=account["name"],
                    email=normalized_email,
                    password_hash=get_password_hash(account["password"]),
                    role=account["role"],
                    phone=None,
                    state=None,
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                results[account["role"]] = new_user

        return results
    except Exception:
        db.rollback()
        raise
    finally:
        if should_close:
            db.close()


def seed_admin(db: Optional[Session] = None) -> User:
    """
    Extended idempotent seed function.
    Seeds development accounts (Admin, Staff, Customer) and returns the admin User.
    Maintains compatibility with existing callers.
    """
    accounts = seed_dev_accounts(db=db)
    return accounts["admin"]


# Aliases for convenience
seed_initial_data = seed_dev_accounts
seed_users = seed_dev_accounts

__all__ = [
    "seed_dev_accounts",
    "seed_admin",
    "seed_initial_data",
    "seed_users",
    "DEV_SEED_ACCOUNTS",
]
