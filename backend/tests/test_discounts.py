from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import ValidationError

from app.database import Base
from app.models.product import Product
from app.schemas.discount import DiscountCreate, DiscountUpdate, DiscountValidateRequest
from app.services.discount import (
    calculate_discount,
    consume_discount,
    create_discount,
    deactivate_discount,
    update_discount,
)
from app.routers.discounts import validate_discount


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Product(name="Analytics", type="digital", sales_price=10000, cost_price=0))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def create_percent_discount(db, **overrides):
    values = {
        "name": "Summer",
        "discount_type": "percent",
        "value": Decimal("10"),
        "applies_to": "subscription",
    }
    values.update(overrides)
    return create_discount(db, DiscountCreate(**values))


def test_percentage_fixed_and_minimum_validation(db):
    percent = create_percent_discount(db, min_purchase=5000, min_qty=2)
    assert calculate_discount(percent, 10000, 2, "subscription", []) == 1000
    with pytest.raises(ValueError, match="minimum amount"):
        calculate_discount(percent, 4999, 2, "subscription", [])
    with pytest.raises(ValueError, match="minimum quantity"):
        calculate_discount(percent, 10000, 1, "subscription", [])

    fixed = create_percent_discount(
        db,
        name="Fixed",
        discount_type="fixed",
        value=2500,
    )
    assert calculate_discount(fixed, 1000, 1, "subscription", []) == 1000


def test_discount_schema_validates_dates_types_and_applicability():
    with pytest.raises(ValidationError):
        DiscountCreate(
            name="Bad dates",
            discount_type="percent",
            value=10,
            applies_to="subscription",
            start_date=date.today(),
            end_date=date.today() - timedelta(days=1),
        )
    with pytest.raises(ValidationError):
        DiscountCreate(
            name="Too much",
            discount_type="percent",
            value=Decimal("100.01"),
            applies_to="subscription",
        )
    with pytest.raises(ValidationError):
        DiscountCreate(
            name="No products",
            discount_type="percent",
            value=10,
            applies_to="products",
        )
    with pytest.raises(ValidationError):
        DiscountUpdate(discount_type="fixed", value=Decimal("1.25"))


def test_product_applicability_and_unknown_product_rejected(db):
    with pytest.raises(ValueError, match="Unknown product IDs"):
        create_percent_discount(db, applies_to="products", product_ids=[999])
    product_discount = create_percent_discount(
        db,
        name="Product only",
        applies_to="products",
        product_ids=[1],
    )
    assert calculate_discount(product_discount, 5000, 1, "products", [1]) == 500
    with pytest.raises(ValueError, match="does not apply"):
        calculate_discount(product_discount, 5000, 1, "products", [2])


def test_validation_does_not_consume_usage_but_confirmation_can(db):
    discount = create_percent_discount(db, usage_limit=1)
    request = DiscountValidateRequest(
        discount_id=discount.id,
        subtotal=10000,
        applies_to="subscription",
    )
    response = validate_discount(request, db)
    assert response.discount_amount == 1000
    db.refresh(discount)
    assert discount.used_count == 0

    consumed = consume_discount(
        db,
        discount.id,
        subtotal=10000,
        quantity=1,
        applies_to="subscription",
        product_ids=[],
    )
    assert consumed == 1000
    db.commit()
    db.refresh(discount)
    assert discount.used_count == 1
    with pytest.raises(ValueError, match="usage limit"):
        calculate_discount(discount, 10000, 1, "subscription", [])


def test_update_and_deactivation_preserve_usage_rules(db):
    discount = create_percent_discount(db, usage_limit=2)
    consume_discount(db, discount.id, 1000, 1, "subscription", [])
    consume_discount(db, discount.id, 1000, 1, "subscription", [])
    db.commit()
    with pytest.raises(ValueError, match="lower than the current usage"):
        update_discount(db, discount, DiscountUpdate(usage_limit=1))
    db.rollback()
    inactive = deactivate_discount(db, discount)
    assert inactive.is_active is False
    with pytest.raises(ValueError, match="inactive"):
        calculate_discount(inactive, 1000, 1, "subscription", [])


def test_validate_endpoint_returns_discounted_total(db):
    discount = create_percent_discount(db)
    response = validate_discount(
        DiscountValidateRequest(
            discount_id=discount.id,
            subtotal=101,
            applies_to="subscription",
        ),
        db,
    )
    assert response.discount_amount == 10
    assert response.total == 91
