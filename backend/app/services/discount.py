from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.discount import Discount
from app.models.product import Product
from app.schemas.discount import DiscountCreate, DiscountUpdate


def get_discounts(db: Session, is_active: Optional[bool] = None) -> list[Discount]:
    query = db.query(Discount)
    if is_active is not None:
        query = query.filter(Discount.is_active == is_active)
    return query.order_by(Discount.id.asc()).all()


def get_discount_by_id(db: Session, discount_id: int) -> Optional[Discount]:
    return db.query(Discount).filter(Discount.id == discount_id).first()


def get_discount_by_name(db: Session, name: str) -> Optional[Discount]:
    return db.query(Discount).filter(func.lower(Discount.name) == name.strip().lower()).first()


def validate_product_ids(db: Session, product_ids: list[int]) -> None:
    if not product_ids:
        return
    found = {
        product_id
        for (product_id,) in db.query(Product.id).filter(Product.id.in_(product_ids)).all()
    }
    missing = sorted(set(product_ids) - found)
    if missing:
        raise ValueError(f"Unknown product IDs: {', '.join(map(str, missing))}.")


def create_discount(db: Session, discount_in: DiscountCreate) -> Discount:
    validate_product_ids(db, discount_in.product_ids)
    values = discount_in.model_dump()
    values["discount_type"] = discount_in.discount_type.value
    values["applies_to"] = discount_in.applies_to.value
    discount = Discount(**values)
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return discount


def update_discount(db: Session, discount: Discount, discount_in: DiscountUpdate) -> Discount:
    updates = discount_in.model_dump(exclude_unset=True)
    validate_product_ids(db, updates.get("product_ids", discount.product_ids) or [])
    for field, value in updates.items():
        if hasattr(value, "value"):
            value = value.value
        setattr(discount, field, value)
    if discount.discount_type == "percent" and discount.value > 100:
        raise ValueError("Percentage discounts cannot exceed 100%.")
    if discount.discount_type == "fixed" and Decimal(str(discount.value)) != Decimal(str(discount.value)).to_integral_value():
        raise ValueError("Fixed discounts must be an integer amount in paise.")
    if discount.start_date and discount.end_date and discount.end_date < discount.start_date:
        raise ValueError("End date must be on or after start date.")
    if discount.applies_to == "products" and not discount.product_ids:
        raise ValueError("Select at least one product for a product-specific discount.")
    if discount.applies_to == "subscription" and discount.product_ids:
        raise ValueError("Product IDs are only valid for product-specific discounts.")
    if discount.usage_limit is not None and discount.usage_limit < discount.used_count:
        raise ValueError("Usage limit cannot be lower than the current usage count.")
    db.commit()
    db.refresh(discount)
    return discount


def deactivate_discount(db: Session, discount: Discount) -> Discount:
    discount.is_active = False
    db.commit()
    db.refresh(discount)
    return discount


def calculate_discount(
    discount: Discount,
    subtotal: int,
    quantity: int,
    applies_to: str,
    product_ids: list[int],
) -> int:
    if not discount.is_active:
        raise ValueError("This discount is inactive.")
    if discount.start_date and date.today() < discount.start_date:
        raise ValueError("This discount is not active yet.")
    if discount.end_date and date.today() > discount.end_date:
        raise ValueError("This discount has expired.")
    if discount.usage_limit is not None and discount.used_count >= discount.usage_limit:
        raise ValueError("This discount has reached its usage limit.")
    if discount.applies_to != applies_to:
        raise ValueError(f"This discount applies to {discount.applies_to} only.")
    if discount.min_purchase is not None and subtotal < discount.min_purchase:
        raise ValueError("The purchase does not meet the minimum amount for this discount.")
    if discount.min_qty is not None and quantity < discount.min_qty:
        raise ValueError("The purchase does not meet the minimum quantity for this discount.")
    if discount.applies_to == "products" and not set(discount.product_ids).intersection(product_ids):
        raise ValueError("This discount does not apply to the selected products.")

    if discount.discount_type == "percent":
        amount = (
            Decimal(subtotal) * Decimal(str(discount.value)) / Decimal("100")
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return min(subtotal, int(amount))
    return min(subtotal, int(discount.value))


def consume_discount(
    db: Session,
    discount_id: int,
    subtotal: int,
    quantity: int,
    applies_to: str,
    product_ids: list[int],
) -> int:
    discount = db.query(Discount).filter(Discount.id == discount_id).first()
    if discount is None:
        raise ValueError("Discount not found.")
    amount = calculate_discount(discount, subtotal, quantity, applies_to, product_ids)
    usage_condition = or_(
        Discount.usage_limit.is_(None),
        Discount.used_count < Discount.usage_limit,
    )
    updated = (
        db.query(Discount)
        .filter(
            Discount.id == discount_id,
            Discount.is_active.is_(True),
            usage_condition,
        )
        .update(
            {Discount.used_count: Discount.used_count + 1},
            synchronize_session=False,
        )
    )
    if updated != 1:
        raise ValueError("This discount has reached its usage limit or is inactive.")
    db.refresh(discount)
    return amount
