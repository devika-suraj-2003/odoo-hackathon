"""
Tax ORM Model.

Represents a tax rate or GST rule applicable to subscriptions, products, and invoices.
Tax rates are stored as exact Numeric/Decimal percentages (e.g. 18.00 for 18%).
Monetary calculations using this tax must be performed in integer paise (₹1 = 100 paise).
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String
from sqlalchemy.orm import relationship
from app.database import Base


class Tax(Base):
    """
    Tax Model.
    
    Can be referenced by subscriptions, invoices, and invoice line items via:
    `tax_id = Column(Integer, ForeignKey("taxes.id"), nullable=True)`
    """
    __tablename__ = "taxes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    rate = Column(Numeric(precision=5, scale=2), nullable=False)
    tax_type = Column(String(50), nullable=False, default="gst", index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    subscription_lines = relationship("SubscriptionLine", back_populates="tax")

    def __repr__(self) -> str:
        return f"<Tax id={self.id} name='{self.name}' rate={self.rate}% type='{self.tax_type}' active={self.is_active}>"
