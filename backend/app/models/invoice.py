from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(30), unique=True, nullable=False, index=True)

    subscription_id = Column(
        Integer, ForeignKey("subscriptions.id"), nullable=False
    )
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)

    subtotal = Column(Integer, nullable=False, default=0)
    discount_total = Column(Integer, nullable=False, default=0)
    tax_total = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)

    status = Column(String(20), nullable=False, default="draft")

    lines = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "period_start",
            name="uq_invoice_subscription_period"
        ),
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    description = Column(String(255), nullable=True)

    qty = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=False, default=0)
    amount = Column(Integer, nullable=False, default=0)

    invoice = relationship("Invoice", back_populates="lines")