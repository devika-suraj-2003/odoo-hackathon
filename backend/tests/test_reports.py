from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services.report import monthly_revenue, report_summary


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
        email="reports@example.test",
        password_hash="not-a-real-password",
    )
    monthly_plan = Plan(
        name="Monthly", price=50000, billing_period="monthly", start_date=date.today()
    )
    annual_plan = Plan(
        name="Annual", price=120000, billing_period="yearly", start_date=date.today()
    )
    session.add_all([customer, monthly_plan, annual_plan])
    session.commit()
    session.add_all(
        [
            Subscription(
                number="SUB-MONTH",
                customer_id=customer.id,
                plan_id=monthly_plan.id,
                status="active",
                start_date=date.today(),
                total=50000,
            ),
            Subscription(
                number="SUB-YEAR",
                customer_id=customer.id,
                plan_id=annual_plan.id,
                status="active",
                start_date=date.today(),
                total=120000,
            ),
            Subscription(
                number="SUB-PAUSED",
                customer_id=customer.id,
                plan_id=monthly_plan.id,
                status="paused",
                start_date=date.today(),
                total=999999,
            ),
            Invoice(
                number="INV-OVERDUE",
                customer_id=customer.id,
                status="confirmed",
                invoice_date=date.today(),
                due_date=date.today() - timedelta(days=1),
                total=15000,
                amount_paid=5000,
                amount_due=10000,
            ),
            Invoice(
                number="INV-CURRENT",
                customer_id=customer.id,
                status="confirmed",
                invoice_date=date.today(),
                due_date=date.today() + timedelta(days=10),
                total=15000,
                amount_due=15000,
            ),
            Invoice(
                number="INV-PAID",
                customer_id=customer.id,
                status="paid",
                invoice_date=date.today(),
                due_date=date.today() - timedelta(days=3),
                total=5000,
                amount_due=0,
            ),
        ]
    )
    session.commit()
    session.add_all(
        [
            Payment(
                invoice_id=1,
                amount=3000,
                method="upi",
                payment_date=date.today(),
            ),
            Payment(
                invoice_id=2,
                amount=4000,
                method="cash",
                payment_date=date.today(),
            ),
        ]
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_summary_aggregates_recurring_collected_and_outstanding_amounts(db):
    summary = report_summary(db)
    assert summary == {
        "active_subscriptions": 2,
        "mrr": 60000,
        "arr": 720000,
        "revenue": 7000,
        "payments_total": 7000,
        "outstanding": 25000,
        "overdue_amount": 10000,
        "overdue_count": 1,
    }


def test_monthly_revenue_returns_requested_months_and_paise(db):
    revenue = monthly_revenue(db, months=3)
    assert len(revenue) == 3
    assert revenue[-1]["revenue"] == 7000
    assert all(len(item["month"]) == 7 for item in revenue)
