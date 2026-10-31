"""
setting.py — SQLAlchemy model for application settings in Brightloop Subscription Management System.
"""

from datetime import date
from typing import Optional

from sqlalchemy import String, Text, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Setting(Base):
    """
    Setting entity storing application configurations, including simulated_today for Time Machine.
    Supports both key-value lookups and dedicated fields.
    """
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    simulated_today: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Setting(id={self.id}, key='{self.key}', "
            f"value='{self.value}', simulated_today={self.simulated_today})>"
        )

