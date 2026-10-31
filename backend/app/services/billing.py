from datetime import date, timedelta
from calendar import monthrange


def get_next_billing_date(current_date: date, billing_period: str) -> date:
    """Calculate the next billing date."""

    if billing_period == "daily":
        return current_date + timedelta(days=1)

    if billing_period == "weekly":
        return current_date + timedelta(weeks=1)

    if billing_period == "monthly":
        year = current_date.year + (current_date.month // 12)
        month = (current_date.month % 12) + 1
        day = min(current_date.day, monthrange(year, month)[1])
        return date(year, month, day)

    if billing_period == "yearly":
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            return current_date.replace(
                year=current_date.year + 1,
                day=28,
            )

    raise ValueError(f"Unsupported billing period: {billing_period}")


def calculate_billing_period(
    start_date: date,
    billing_period: str,
) -> tuple[date, date]:
    """Return the start and inclusive end dates of a billing period."""

    next_date = get_next_billing_date(start_date, billing_period)
    return start_date, next_date - timedelta(days=1)


def run_billing(db, simulated_today: date) -> int:
    """Generate all due recurring invoices and return their count."""

    from app.models.subscription import Subscription
    from app.models.plan import Plan
    from app.models.invoice import Invoice
    from app.services.subscription import _create_subscription_invoice

    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.status == "active",
            Subscription.is_paused.is_(False),
            Subscription.next_billing_date.isnot(None),
            Subscription.next_billing_date <= simulated_today,
        )
        .all()
    )

    invoices_created = 0

    try:
        for subscription in subscriptions:
            plan = db.query(Plan).filter(
                Plan.id == subscription.plan_id
            ).first()

            if plan is None:
                continue

            while (
                subscription.next_billing_date is not None
                and subscription.next_billing_date <= simulated_today
            ):
                period_start = subscription.next_billing_date

                if (
                    subscription.expiry_date is not None
                    and period_start > subscription.expiry_date
                ):
                    break

                existing_invoice = (
                    db.query(Invoice.id)
                    .filter(
                        Invoice.subscription_id == subscription.id,
                        Invoice.period_start == period_start,
                    )
                    .first()
                )

                if existing_invoice:
                    subscription.next_billing_date = get_next_billing_date(
                        period_start,
                        plan.billing_period,
                    )
                    continue

                invoice = _create_subscription_invoice(
                    db,
                    subscription,
                    renewal=True,
                )

                if invoice is None:
                    break

                invoices_created += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    return invoices_created