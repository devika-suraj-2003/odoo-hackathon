from sqlalchemy import (
    Column, Integer, String, Date, Boolean,
    ForeignKey, DateTime
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(30), unique=True, nullable=False)

    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)

    start_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    payment_terms_days = Column(Integer, default=0)

    status = Column(String(30), default="draft", nullable=False)
    next_billing_date = Column(Date, nullable=True)
    is_paused = Column(Boolean, default=False)

    lines = relationship(
        "SubscriptionLine",
        back_populates="subscription",
        cascade="all, delete-orphan"
    )

    history = relationship(
        "SubscriptionHistory",
        back_populates="subscription",
        cascade="all, delete-orphan"
    )


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"

    id = Column(Integer, primary_key=True, index=True)

    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id"),
        nullable=False
    )

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)

    qty = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=False)
    tax_id = Column(Integer, ForeignKey("taxes.id"), nullable=True)
    amount = Column(Integer, nullable=False)

    subscription = relationship(
        "Subscription",
        back_populates="lines"
    )


class SubscriptionHistory(Base):
    __tablename__ = "subscription_history"

    id = Column(Integer, primary_key=True, index=True)

    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id"),
        nullable=False
    )

    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=False)

    note = Column(String(255), nullable=True)

    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)

    subscription = relationship(
        "Subscription",
        back_populates="history"
    )