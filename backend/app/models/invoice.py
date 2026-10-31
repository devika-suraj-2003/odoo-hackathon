from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "period_start",
            name="uq_invoice_subscription_period",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    subscription_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False, index=True
    )
    invoice_date: Mapped[date] = mapped_column(
        Date, default=date.today, nullable=False
    )
    issue_date = synonym("invoice_date")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Keep the existing JSON API/service contract; relational rows are available
    # separately for consumers that need line-level foreign keys.
    lines: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    line_items: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.id",
    )

    subtotal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_subtotal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tax_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_paid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_due: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("discounts.id"), nullable=True
    )
    discount_usage_recorded: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    discount_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    customer_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    tax_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("taxes.id"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    quantity = synonym("qty")
    unit_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tax_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    invoice: Mapped["Invoice"] = relationship(
        "Invoice", back_populates="line_items"
    )
