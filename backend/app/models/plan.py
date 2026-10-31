"""
plan.py — SQLAlchemy model for subscription plans in the Brightloop Subscription Management System.
"""

from datetime import date
from typing import Optional

from sqlalchemy import String, Integer, Date, Boolean, CheckConstraint, true, false
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Plan(Base):
    """
    Plan entity representing recurring subscription tiers and configurations.
    Monetary values (price) are stored in paise (e.g. ₹999 = 99900).
    Allowed billing periods: 'daily', 'weekly', 'monthly', 'yearly'.
    """
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint(
            "billing_period IN ('daily', 'weekly', 'monthly', 'yearly')",
            name="check_valid_billing_period",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    billing_period: Mapped[str] = mapped_column(String(20), nullable=False)
    min_qty: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    auto_close: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )
    closable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    pausable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    renewable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Plan(id={self.id}, name='{self.name}', price={self.price}, "
            f"billing_period='{self.billing_period}', is_active={self.is_active})>"
        )

