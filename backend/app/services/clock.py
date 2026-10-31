"""
clock.py — Centralized Time Service and Time Machine implementation for Brightloop.

All backend date-dependent operations (such as subscription intervals, billing cycles,
and renewals) should use clock.today() instead of datetime.date.today().
"""

from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.setting import Setting


def today(db: Optional[Session] = None) -> date:
    """
    Returns simulated_today from the settings table when configured,
    otherwise returns the real current system date (date.today()).

    Args:
        db: Optional active SQLAlchemy session. If None, a temporary session is opened.

    Returns:
        datetime.date: The effective system date.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # Check settings table for simulated_today
        setting = db.query(Setting).filter(
            (Setting.key == "simulated_today") | (Setting.id == 1)
        ).first()

        if setting:
            # 1. Check dedicated simulated_today date field
            if setting.simulated_today is not None:
                return setting.simulated_today
            # 2. Check value field (ISO formatted date string)
            if setting.key == "simulated_today" and setting.value:
                try:
                    return date.fromisoformat(setting.value)
                except ValueError:
                    pass

        return date.today()
    except Exception:
        # Fallback safely to real system date if database is unreachable or table not ready
        return date.today()
    finally:
        if should_close:
            db.close()


def get_simulated_today(db: Optional[Session] = None) -> Optional[date]:
    """
    Returns the configured simulated_today date if time travel is active,
    or None if the system is running on real time.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        setting = db.query(Setting).filter(
            (Setting.key == "simulated_today") | (Setting.id == 1)
        ).first()

        if setting:
            if setting.simulated_today is not None:
                return setting.simulated_today
            if setting.key == "simulated_today" and setting.value:
                try:
                    return date.fromisoformat(setting.value)
                except ValueError:
                    pass
        return None
    except Exception:
        return None
    finally:
        if should_close:
            db.close()


def is_simulated(db: Optional[Session] = None) -> bool:
    """
    Returns True if simulated time travel is currently active, False otherwise.
    """
    return get_simulated_today(db=db) is not None


def set_simulated_today(target_date: date, db: Optional[Session] = None) -> date:
    """
    Idempotently sets the simulated date in the settings table.
    Ensures no duplicate setting records are created.

    Args:
        target_date: The simulated date to set.
        db: Optional active SQLAlchemy session.

    Returns:
        The newly set simulated date.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        setting = db.query(Setting).filter(
            (Setting.key == "simulated_today") | (Setting.id == 1)
        ).first()

        if setting is None:
            setting = Setting(
                id=1,
                key="simulated_today",
                value=target_date.isoformat(),
                simulated_today=target_date,
            )
            db.add(setting)
        else:
            setting.key = "simulated_today"
            setting.value = target_date.isoformat()
            setting.simulated_today = target_date

        db.commit()
        db.refresh(setting)
        return target_date
    except Exception:
        db.rollback()
        raise
    finally:
        if should_close:
            db.close()


def advance_time(days: int, db: Optional[Session] = None) -> date:
    """
    Advances time by the specified number of days relative to the current effective today().

    Args:
        days: Number of days to advance (must be >= 1).
        db: Optional active SQLAlchemy session.

    Returns:
        The new simulated date.
    """
    if days <= 0:
        raise ValueError(f"Days must be positive, got {days}")

    current_effective = today(db=db)
    new_simulated = current_effective + timedelta(days=days)
    set_simulated_today(new_simulated, db=db)
    return new_simulated


def reset_simulated_today(db: Optional[Session] = None) -> None:
    """
    Clears the simulated_today setting in the settings table, reverting clock.today()
    to the real current system date.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        setting = db.query(Setting).filter(
            (Setting.key == "simulated_today") | (Setting.id == 1)
        ).first()

        if setting:
            setting.value = None
            setting.simulated_today = None
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if should_close:
            db.close()


# Shorthand alias
reset_clock = reset_simulated_today

__all__ = [
    "today",
    "get_simulated_today",
    "is_simulated",
    "set_simulated_today",
    "advance_time",
    "reset_simulated_today",
    "reset_clock",
]

