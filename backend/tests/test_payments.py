from datetime import date
from decimal import Decimal
import hashlib
import hmac

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.plan import Plan
from app.models.razorpay_order import RazorpayOrder
from app.models.product import Product
from app.models.tax import Tax
from app.models.user import User
from app.schemas.discount import DiscountCreate
from app.schemas.invoice import InvoiceCreate, InvoiceLineCreate
from app.schemas.payment import PaymentCreate, RazorpayVerifyRequest
from app.schemas.subscription import SubscriptionCreate, SubscriptionLineCreate
from app.services.discount import create_discount
from app.services.invoice import confirm_invoice, create_invoice
from app.services.payment import (
    create_razorpay_order,
    get_payments,
    record_payment,
    verify_razorpay_payment,
)
from app.services.subscription import create_subscription, transition_subscription


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    customer = User(
        name="Customer",
        email="customer@example.test",
        password_hash="not-a-real-password",
        state="Kerala",
    )
    plan = Plan(
        name="Monthly",
        price=10000,
        billing_period="monthly",
        start_date=date.today(),
    )
    product = Product(name="Service", type="digital", sales_price=10000, cost_price=0)
    tax = Tax(name="GST 18%", rate=Decimal("18.00"), tax_type="gst", is_active=True)
    db_objects = [customer, plan, product, tax]
    session.add_all(db_objects)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def new_invoice(db, **options):
    customer = db.query(User).first()
    return create_invoice(
        db,
        InvoiceCreate(
            customer_id=customer.id,
            lines=[
                InvoiceLineCreate(
                    description="Service",
                    quantity=1,
                    unit_price=10000,
                    **options.pop("line_options", {}),
                )
            ],
            **options,
        ),
    )


def test_invoice_uses_gst_and_confirms_discount_only_once(db):
    product = db.query(Product).first()
    tax = db.query(Tax).first()
    discount = create_discount(
        db,
        DiscountCreate(
            name="Product promo",
            discount_type="percent",
            value=Decimal("10"),
            applies_to="products",
            product_ids=[product.id],
        ),
    )
    invoice = new_invoice(
        db,
        discount_id=discount.id,
        line_options={"product_id": product.id, "tax_id": tax.id},
    )
    assert invoice.total == 10620
    assert invoice.discount_usage_recorded is False
    assert discount.used_count == 0

    confirmed = confirm_invoice(db, invoice)
    assert confirmed.status == "confirmed"
    assert confirmed.discount_usage_recorded is True
    assert discount.used_count == 1
    assert confirmed.discount_total == 1000
    assert confirmed.tax_total == 1620
    assert confirmed.total == 10620
    with pytest.raises(ValueError, match="Only draft invoices"):
        confirm_invoice(db, confirmed)
    db.refresh(discount)
    assert discount.used_count == 1


def test_product_discount_only_reduces_eligible_invoice_lines(db):
    eligible = db.query(Product).first()
    other = Product(name="Other", type="digital", sales_price=20000, cost_price=0)
    db.add(other)
    db.commit()
    discount = create_discount(
        db,
        DiscountCreate(
            name="Eligible product promo",
            discount_type="percent",
            value=Decimal("10"),
            applies_to="products",
            product_ids=[eligible.id],
        ),
    )
    invoice = create_invoice(
        db,
        InvoiceCreate(
            customer_id=db.query(User.id).scalar(),
            lines=[
                InvoiceLineCreate(
                    description="Eligible",
                    product_id=eligible.id,
                    quantity=1,
                    unit_price=10000,
                ),
                InvoiceLineCreate(
                    description="Not eligible",
                    product_id=other.id,
                    quantity=1,
                    unit_price=20000,
                ),
            ],
            discount_id=discount.id,
        ),
    )
    assert invoice.discount_total == 1000
    assert invoice.lines[0]["discount_amount"] == 1000
    assert invoice.lines[1]["discount_amount"] == 0
    assert invoice.total == 29000


def test_payments_support_partial_payment_and_reject_overpayment(db):
    invoice = new_invoice(db)
    with pytest.raises(ValueError, match="confirmed"):
        record_payment(
            db,
            PaymentCreate(invoice_id=invoice.id, amount=1000, method="cash"),
        )
    invoice = confirm_invoice(db, invoice)
    first = record_payment(
        db,
        PaymentCreate(invoice_id=invoice.id, amount=4000, method="upi"),
    )
    db.refresh(invoice)
    assert first.amount == 4000
    assert invoice.status == "confirmed"
    assert invoice.amount_paid == 4000
    assert invoice.amount_due == 6000

    with pytest.raises(ValueError, match="exceeds the outstanding balance"):
        record_payment(
            db,
            PaymentCreate(invoice_id=invoice.id, amount=6001, method="card"),
        )
    second = record_payment(
        db,
        PaymentCreate(invoice_id=invoice.id, amount=6000, method="bank_transfer"),
    )
    db.refresh(invoice)
    assert second.amount == 6000
    assert invoice.status == "paid"
    assert invoice.amount_paid == 10000
    assert invoice.amount_due == 0
    assert [payment.amount for payment in get_payments(db, invoice.id)] == [6000, 4000]


def test_subscription_usage_is_incremented_on_confirmation(db):
    customer = db.query(User).first()
    plan = db.query(Plan).first()
    discount = create_discount(
        db,
        DiscountCreate(
            name="Subscription promo",
            discount_type="fixed",
            value=Decimal("2000"),
            applies_to="subscription",
        ),
    )
    subscription = create_subscription(
        db,
        SubscriptionCreate(
            customer_id=customer.id,
            plan_id=plan.id,
            start_date=date.today(),
            lines=[
                SubscriptionLineCreate(
                    product_id=db.query(Product.id).scalar(),
                    quantity=1,
                    unit_price=10000,
                    tax_id=db.query(Tax.id).scalar(),
                )
            ],
            discount_id=discount.id,
        ),
    )
    assert subscription.total == 8000
    assert discount.used_count == 0
    transition_subscription(db, subscription, "send-quotation")
    confirmed = transition_subscription(db, subscription, "confirm")
    assert confirmed.status == "confirmed"
    assert confirmed.discount_usage_recorded is True
    assert confirmed.total == 8000
    assert subscription.line_items[0].tax_id == db.query(Tax.id).scalar()
    db.refresh(discount)
    assert discount.used_count == 1


def test_razorpay_verification_records_once_and_settles_invoice(db, monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_example")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "test-secret")
    invoice = confirm_invoice(db, new_invoice(db))
    monkeypatch.setattr(
        "app.services.razorpay.create_order",
        lambda amount, invoice_id: {
            "id": "order_test_1",
            "amount": amount,
            "currency": "INR",
        },
    )
    order_response = create_razorpay_order(db, invoice.id)
    assert order_response == {
        "order_id": "order_test_1",
        "amount": 10000,
        "currency": "INR",
        "key_id": "rzp_test_example",
    }

    signature = hmac.new(
        b"test-secret",
        b"order_test_1|pay_test_1",
        hashlib.sha256,
    ).hexdigest()
    monkeypatch.setattr(
        "app.services.razorpay.get_payment",
        lambda payment_id: {
            "id": payment_id,
            "order_id": "order_test_1",
            "amount": 10000,
            "currency": "INR",
            "status": "captured",
        },
    )
    request = RazorpayVerifyRequest(
        invoice_id=invoice.id,
        razorpay_order_id="order_test_1",
        razorpay_payment_id="pay_test_1",
        razorpay_signature=signature,
    )
    payment = verify_razorpay_payment(db, request)
    assert payment.method == "razorpay"
    assert payment.amount == 10000
    db.refresh(invoice)
    assert invoice.status == "paid"
    assert invoice.amount_due == 0
    assert db.query(RazorpayOrder).one().payment_id == "pay_test_1"
    with pytest.raises(ValueError, match="already been processed"):
        verify_razorpay_payment(db, request)


def test_razorpay_rejects_bad_signatures_and_live_mode_credentials(db, monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_example")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "test-secret")
    invoice = confirm_invoice(db, new_invoice(db))
    monkeypatch.setattr(
        "app.services.razorpay.create_order",
        lambda amount, invoice_id: {
            "id": "order_test_2",
            "amount": amount,
            "currency": "INR",
        },
    )
    create_razorpay_order(db, invoice.id)
    with pytest.raises(ValueError, match="signature is invalid"):
        verify_razorpay_payment(
            db,
            RazorpayVerifyRequest(
                invoice_id=invoice.id,
                razorpay_order_id="order_test_2",
                razorpay_payment_id="pay_test_2",
                razorpay_signature="invalid",
            ),
        )
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_not_allowed")
    with pytest.raises(ValueError, match="test-mode"):
        create_razorpay_order(db, invoice.id)
