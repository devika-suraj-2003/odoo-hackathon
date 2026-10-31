"""
product.py — SQLAlchemy model for products in the Brightloop Subscription Management System.
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product_variant import ProductVariant


class Product(Base):
    """
    Product entity representing goods or services offered in the system.
    Monetary values (sales_price, cost_price) are stored in paise (e.g. ₹499 = 49900).
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    sales_price: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_price: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship: One product can have multiple product variants
    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Product(id={self.id}, name='{self.name}', type='{self.type}', "
            f"sales_price={self.sales_price}, cost_price={self.cost_price})>"
        )

