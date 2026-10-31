"""
product_variant.py — SQLAlchemy model for product variants in the Brightloop Subscription Management System.
"""

from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.product import Product


class ProductVariant(Base):
    """
    ProductVariant entity representing distinct variations of a product (e.g. Size: Large, Color: Blue).
    Monetary values (extra_price) are stored in paise (e.g. ₹50 = 5000).
    """
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    attribute: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    extra_price: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    # Relationship: Each variant belongs to one product
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="variants",
    )

    def __repr__(self) -> str:
        return (
            f"<ProductVariant(id={self.id}, product_id={self.product_id}, "
            f"attribute='{self.attribute}', value='{self.value}', extra_price={self.extra_price})>"
        )

