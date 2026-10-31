from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    subscription_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("subscriptions.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    invoice_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lines: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    subtotal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_subtotal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tax_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_paid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_due: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_id: Mapped[Optional[int]] = mapped_column(ForeignKey("discounts.id"), nullable=True)
    discount_usage_recorded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discount_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    customer_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
