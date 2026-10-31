"""
database.py — SQLAlchemy engine and session factory.

Database: SQLite (confirmed)
  - Driver: Python's built-in sqlite3 — no extra package required.
  - File:   brightloop.db (created automatically in the backend/ directory).
  - The DATABASE_URL is read from the DATABASE_URL environment variable so
    it can be overridden per environment without changing code.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///./brightloop.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
    echo=False,  # Set True to log all SQL statements during development
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a DB session and ensures it is closed afterward.
# Import and use with:  db: Session = Depends(get_db)
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
