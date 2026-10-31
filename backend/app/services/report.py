from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Subscription


MONTHLY_MULTIPLIERS = {
    "daily": Decimal(365) / Decimal(12),
    "weekly": Decimal(52) / Decimal(12),
    "monthly": Decimal(1),
    "yearly": Decimal(1) / Decimal(12),
}


def _round_paise(value: Decimal | int) -> int:
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def monthly_revenue(db: Session, months: int = 12) -> list[dict]:
    today = date.today()
    month_keys = []
    current = today.year * 12 + today.month - 1
    for offset in range(months - 1, -1, -1):
        serial = current - offset
        year, month0 = divmod(serial, 12)
        month_keys.append((year, month0 + 1))
    start_year, start_month = month_keys[0]
    start_date = date(start_year, start_month, 1)
    last_month = month_keys[-1]
    end_date = date(last_month[0], last_month[1], monthrange(*last_month)[1])

    totals: dict[tuple[int, int], int] = {}
    rows = (
        db.query(Payment.payment_date, func.sum(Payment.amount))
        .filter(Payment.payment_date >= start_date, Payment.payment_date <= end_date)
        .group_by(Payment.payment_date)
        .all()
    )
    for payment_date, amount in rows:
        key = (payment_date.year, payment_date.month)
        totals[key] = totals.get(key, 0) + int(amount or 0)
    return [
        {
            "month": f"{year:04d}-{month:02d}",
            "revenue": totals.get((year, month), 0),
        }
        for year, month in month_keys
    ]


def report_summary(db: Session) -> dict:
    active_rows = (
        db.query(Subscription.total, Plan.billing_period)
        .join(Plan, Plan.id == Subscription.plan_id)
        .filter(Subscription.status == "active")
        .all()
    )
    mrr = _round_paise(
        sum(
            (Decimal(total) * MONTHLY_MULTIPLIERS.get(period, Decimal(1)))
            for total, period in active_rows
        )
    )
    collected = int(db.query(func.coalesce(func.sum(Payment.amount), 0)).scalar() or 0)

    unpaid = db.query(Invoice).filter(
        Invoice.status == "confirmed",
        Invoice.amount_due > 0,
    )
    outstanding = int(
        db.query(func.coalesce(func.sum(Invoice.amount_due), 0))
        .filter(Invoice.status == "confirmed", Invoice.amount_due > 0)
        .scalar()
        or 0
    )
    overdue = unpaid.filter(Invoice.due_date < date.today())
    return {
        "active_subscriptions": len(active_rows),
        "mrr": mrr,
        "arr": mrr * 12,
        "revenue": collected,
        "payments_total": collected,
        "outstanding": outstanding,
        "overdue_amount": int(
            db.query(func.coalesce(func.sum(Invoice.amount_due), 0))
            .filter(
                Invoice.status == "confirmed",
                Invoice.amount_due > 0,
                Invoice.due_date < date.today(),
            )
            .scalar()
            or 0
        ),
        "overdue_count": overdue.count(),
    }
