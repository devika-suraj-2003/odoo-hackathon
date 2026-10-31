from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class QuotationTemplate(Base):
    __tablename__ = "quotation_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    validity_days = Column(Integer, nullable=False, default=30)

    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)

    lines = relationship(
        "TemplateLine",
        back_populates="template",
        cascade="all, delete-orphan"
    )


class TemplateLine(Base):
    __tablename__ = "template_lines"

    id = Column(Integer, primary_key=True, index=True)

    template_id = Column(
        Integer,
        ForeignKey("quotation_templates.id"),
        nullable=False
    )

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)

    qty = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=False, default=0)

    template = relationship(
        "QuotationTemplate",
        back_populates="lines"
    )