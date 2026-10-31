from datetime import date
import hashlib
import hmac

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models.plan import Plan
from app.models.product import Product
from app.models.user import User
from app.routers import discounts, invoices, payments, reports, subscriptions


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with test_session() as db:
        db.add_all(
            [
                User(
                    name="API Customer",
                    email="api-customer@example.test",
                    password_hash="not-a-real-password",
                    state="Kerala",
                ),
                Plan(
                    name="API Monthly",
                    price=10000,
                    billing_period="monthly",
                    start_date=date.today(),
                ),
                Product(name="API Service", type="digital", sales_price=10000, cost_price=0),
            ]
        )
        db.commit()

    api = FastAPI()
    api.include_router(discounts.router, prefix="/api/discounts")
    api.include_router(subscriptions.router, prefix="/api/subscriptions")
    api.include_router(invoices.router, prefix="/api/invoices")
    api.include_router(payments.router, prefix="/api/payments")
    api.include_router(reports.router, prefix="/api/reports")

    def override_get_db():
        with test_session() as db:
            yield db

    api.dependency_overrides[get_db] = override_get_db
    with TestClient(api) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_subscription_confirmation_consumes_discount_and_updates_reports(client):
    discount_response = client.post(
        "/api/discounts",
        json={
            "name": "API subscription offer",
            "discount_type": "percent",
            "value": 20,
            "applies_to": "subscription",
        },
    )
    assert discount_response.status_code == 201
    discount = discount_response.json()
    assert discount["is_active"] is True
    assert discount["used_count"] == 0

    subscription_response = client.post(
        "/api/subscriptions",
        json={
            "customer_id": 1,
            "plan_id": 1,
            "start_date": date.today().isoformat(),
            "lines": [{"product_id": 1, "quantity": 1, "unit_price": 10000}],
            "discount_id": discount["id"],
        },
    )
    assert subscription_response.status_code == 201
    subscription = subscription_response.json()
    assert subscription["total"] == 8000
    assert client.post(
        f"/api/subscriptions/{subscription['id']}/send-quotation"
    ).status_code == 200
    confirmed = client.post(f"/api/subscriptions/{subscription['id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert client.get(f"/api/discounts/{discount['id']}").json()["used_count"] == 1
    assert client.post(f"/api/subscriptions/{subscription['id']}/activate").status_code == 200
    generated_invoices = client.get(
        f"/api/invoices?subscription_id={subscription['id']}"
    ).json()
    assert len(generated_invoices) == 1
    assert generated_invoices[0]["status"] == "confirmed"
    assert generated_invoices[0]["total"] == 8000

    summary = client.get("/api/reports/summary").json()
    assert set(summary) == {
        "active_subscriptions",
        "mrr",
        "arr",
        "revenue",
        "payments_total",
        "outstanding",
        "overdue_count",
        "overdue_amount",
    }
    assert summary["active_subscriptions"] == 1
    assert summary["mrr"] == 8000
    assert summary["outstanding"] == 8000


def test_invoice_payment_history_partial_balance_and_overpayment(client):
    invoice_response = client.post(
        "/api/invoices",
        json={
            "customer_id": 1,
            "lines": [{"description": "Monthly service", "quantity": 1, "unit_price": 10000}],
        },
    )
    assert invoice_response.status_code == 201
    invoice = invoice_response.json()
    assert client.post(f"/api/invoices/{invoice['id']}/confirm").status_code == 200

    partial = client.post(
        "/api/payments",
        json={"invoice_id": invoice["id"], "amount": 4000, "method": "upi"},
    )
    assert partial.status_code == 201
    current = client.get(f"/api/invoices/{invoice['id']}").json()
    assert current["status"] == "confirmed"
    assert current["amount_paid"] == 4000
    assert current["amount_due"] == 6000

    overpayment = client.post(
        "/api/payments",
        json={"invoice_id": invoice["id"], "amount": 6001, "method": "card"},
    )
    assert overpayment.status_code == 400
    final = client.post(
        "/api/payments",
        json={"invoice_id": invoice["id"], "amount": 6000, "method": "bank_transfer"},
    )
    assert final.status_code == 201
    history = client.get(f"/api/payments?invoice_id={invoice['id']}").json()
    assert sum(item["amount"] for item in history) == 10000
    assert set(history[0]) == {
        "id",
        "invoice_id",
        "method",
        "amount",
        "payment_date",
        "note",
    }
    assert client.get(f"/api/invoices/{invoice['id']}").json()["status"] == "paid"


def test_razorpay_order_and_verification_api_are_test_mode_and_idempotent(client, monkeypatch):
    invoice_response = client.post(
        "/api/invoices",
        json={
            "customer_id": 1,
            "lines": [{"description": "Online service", "quantity": 1, "unit_price": 12345}],
        },
    )
    invoice = invoice_response.json()
    client.post(f"/api/invoices/{invoice['id']}/confirm")

    missing_configuration = client.post(
        "/api/payments/razorpay/order",
        json={"invoice_id": invoice["id"]},
    )
    assert missing_configuration.status_code == 503

    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_api")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "api-test-secret")
    monkeypatch.setattr(
        "app.services.razorpay.create_order",
        lambda amount, invoice_id: {
            "id": "order_api_test",
            "amount": amount,
            "currency": "INR",
        },
    )
    order = client.post(
        "/api/payments/razorpay/order",
        json={"invoice_id": invoice["id"]},
    )
    assert order.status_code == 200
    assert order.json() == {
        "order_id": "order_api_test",
        "amount": 12345,
        "currency": "INR",
        "key_id": "rzp_test_api",
    }

    monkeypatch.setattr(
        "app.services.razorpay.get_payment",
        lambda payment_id: {
            "id": payment_id,
            "order_id": "order_api_test",
            "amount": 12345,
            "currency": "INR",
            "status": "captured",
        },
    )
    signature = hmac.new(
        b"api-test-secret",
        b"order_api_test|pay_api_test",
        hashlib.sha256,
    ).hexdigest()
    verification_payload = {
        "invoice_id": invoice["id"],
        "razorpay_order_id": "order_api_test",
        "razorpay_payment_id": "pay_api_test",
        "razorpay_signature": signature,
    }
    verified = client.post("/api/payments/razorpay/verify", json=verification_payload)
    assert verified.status_code == 201
    assert verified.json()["method"] == "razorpay"
    assert verified.json()["amount"] == 12345
    repeated = client.post("/api/payments/razorpay/verify", json=verification_payload)
    assert repeated.status_code == 400
    assert client.get(f"/api/invoices/{invoice['id']}").json()["status"] == "paid"
