from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.product import Product
from app.models.invoice import Invoice
from app.models.subscription import Subscription, SubscriptionLine
from app.models.tax import Tax
from app.models.user import User
from app.schemas.subscription import SubscriptionCreate
from app.services.discount import calculate_discount, consume_discount


def _add_billing_period(value: date, billing_period: str) -> date:
    if billing_period == "daily":
        return value + timedelta(days=1)
    if billing_period == "weekly":
        return value + timedelta(days=7)
    month_increment = 12 if billing_period == "yearly" else 1
    serial = value.year * 12 + value.month - 1 + month_increment
    year, month0 = divmod(serial, 12)
    month = month0 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def create_subscription(db: Session, subscription_in: SubscriptionCreate) -> Subscription:
    customer = db.query(User).filter(User.id == subscription_in.customer_id).first()
    if customer is None:
        raise ValueError("Customer not found.")
    plan = db.query(Plan).filter(Plan.id == subscription_in.plan_id).first()
    if plan is None or not plan.is_active:
        raise ValueError("An active plan is required.")
    product_ids = sorted({line.product_id for line in subscription_in.lines})
    products = {
        product.id: product
        for product in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }
    if len(products) != len(product_ids):
        raise ValueError("One or more selected products could not be found.")
    tax_ids = sorted({line.tax_id for line in subscription_in.lines if line.tax_id is not None})
    taxes = {
        tax.id: tax for tax in db.query(Tax).filter(Tax.id.in_(tax_ids)).all()
    }
    if len(taxes) != len(tax_ids):
        raise ValueError("One or more selected taxes could not be found.")
    if any(not tax.is_active for tax in taxes.values()):
        raise ValueError("Inactive taxes cannot be applied to a subscription.")

    subtotal = sum(line.unit_price * line.quantity for line in subscription_in.lines)
    discount_total = 0
    if subscription_in.discount_id is not None:
        from app.models.discount import Discount

        discount = db.query(Discount).filter(Discount.id == subscription_in.discount_id).first()
        if discount is None:
            raise ValueError("Discount not found.")
        discount_total = calculate_discount(
            discount=discount,
            subtotal=subtotal,
            quantity=sum(line.quantity for line in subscription_in.lines),
            applies_to="subscription",
            product_ids=[],
        )

    lines = [
        {
            "product_id": line.product_id,
            "product_name": products[line.product_id].name,
            "variant_id": line.variant_id,
            "tax_id": line.tax_id,
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "tax_amount": 0,
            "amount": line.unit_price * line.quantity,
        }
        for line in subscription_in.lines
    ]
    now = datetime.now(timezone.utc).isoformat()
    subscription = Subscription(
        number=f"SUB-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}",
        customer_id=customer.id,
        plan_id=plan.id,
        status="draft",
        start_date=subscription_in.start_date,
        expiry_date=plan.end_date,
        next_billing_date=_add_billing_period(
            subscription_in.start_date, plan.billing_period
        ),
        payment_terms=subscription_in.payment_terms,
        lines=lines,
        subtotal=subtotal,
        discount_id=subscription_in.discount_id,
        discount_total=discount_total,
        total=subtotal - discount_total,
        history=[
            {
                "at": now,
                "from_status": None,
                "to_status": "draft",
                "note": "Subscription created",
            }
        ],
        line_items=[
            SubscriptionLine(
                product_id=line["product_id"],
                variant_id=line["variant_id"],
                tax_id=line["tax_id"],
                product_name=line["product_name"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                tax_amount=line["tax_amount"],
                amount=line["amount"],
            )
            for line in lines
        ],
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_subscriptions(db: Session) -> list[Subscription]:
    return db.query(Subscription).order_by(Subscription.id.desc()).all()


def get_subscription(db: Session, subscription_id: int) -> Subscription | None:
    return db.query(Subscription).filter(Subscription.id == subscription_id).first()


def _create_subscription_invoice(
    db: Session,
    subscription: Subscription,
    renewal: bool = False,
) -> Invoice | None:
    if not renewal and (
        db.query(Invoice.id)
        .filter(Invoice.subscription_id == subscription.id)
        .first()
        is not None
    ):
        return None

    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if plan is None:
        raise ValueError("The subscription plan could not be found.")
    period_start = (
        subscription.next_billing_date
        if renewal and subscription.next_billing_date
        else subscription.start_date
    )
    period_end = _add_billing_period(period_start, plan.billing_period)
    raw_lines = subscription.lines
    allocated = [0] * len(raw_lines)
    if subscription.discount_total and subscription.subtotal:
        for index, line in enumerate(raw_lines):
            line_subtotal = line["unit_price"] * line["quantity"]
            allocated[index] = subscription.discount_total * line_subtotal // subscription.subtotal
        remaining = subscription.discount_total - sum(allocated)
        for index in reversed(range(len(raw_lines))):
            line_subtotal = raw_lines[index]["unit_price"] * raw_lines[index]["quantity"]
            extra = min(remaining, line_subtotal - allocated[index])
            allocated[index] += extra
            remaining -= extra
            if remaining == 0:
                break

    invoice_lines = [
        {
            "description": line["product_name"],
            "product_id": line["product_id"],
            "quantity": line["quantity"],
            "unit_price": line["unit_price"],
            "tax_id": None,
            "tax_amount": 0,
            "discount_amount": allocated[index],
            "amount": line["unit_price"] * line["quantity"] - allocated[index],
            "gst_breakdown": None,
        }
        for index, line in enumerate(raw_lines)
    ]
    invoice_date = date.today()
    due_date = invoice_date
    if subscription.payment_terms == "15_days":
        due_date += timedelta(days=15)
    elif subscription.payment_terms == "30_days":
        due_date += timedelta(days=30)
    elif subscription.payment_terms == "end_of_month":
        due_date = date(
            invoice_date.year,
            invoice_date.month,
            monthrange(invoice_date.year, invoice_date.month)[1],
        )

    invoice = Invoice(
        number=f"INV-{invoice_date:%Y%m%d}-{uuid4().hex[:8].upper()}",
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        status="confirmed",
        invoice_date=invoice_date,
        due_date=due_date,
        period_start=period_start,
        period_end=period_end,
        lines=invoice_lines,
        subtotal=subscription.subtotal,
        discount_total=subscription.discount_total,
        discount_subtotal=subscription.subtotal,
        tax_total=0,
        total=subscription.total,
        amount_due=subscription.total,
    )
    db.add(invoice)
    if renewal:
        subscription.next_billing_date = period_end
    return invoice


def transition_subscription(
    db: Session,
    subscription: Subscription,
    action: str,
) -> Subscription:
    allowed = {
        "draft": {"send-quotation": "quotation"},
        "quotation": {"confirm": "confirmed"},
        "confirmed": {"activate": "active"},
        "active": {"pause": "paused", "close": "closed", "renew": "active"},
        "paused": {"resume": "active", "close": "closed"},
        "closed": {"renew": "active"},
    }
    target = allowed.get(subscription.status, {}).get(action)
    if target is None:
        raise ValueError(f"Action '{action}' is not valid for a {subscription.status} subscription.")
    if action == "confirm" and subscription.discount_id and not subscription.discount_usage_recorded:
        try:
            amount = consume_discount(
                db,
                subscription.discount_id,
                subscription.subtotal,
                sum(line["quantity"] for line in subscription.lines),
                "subscription",
                [],
            )
        except ValueError:
            db.rollback()
            raise
        subscription.discount_total = amount
        subscription.total = subscription.subtotal - amount
        subscription.discount_usage_recorded = True

    previous = subscription.status
    subscription.status = target
    subscription.history = [
        *subscription.history,
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "from_status": previous,
            "to_status": target,
            "note": action.replace("-", " ").capitalize(),
        },
    ]
    if action == "activate":
        _create_subscription_invoice(db, subscription)
    elif action == "renew":
        _create_subscription_invoice(db, subscription, renewal=True)
    db.commit()
    db.refresh(subscription)
    return subscription


def subscription_response(db: Session, subscription: Subscription) -> dict:
    customer = db.query(User).filter(User.id == subscription.customer_id).first()
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    return {
        "id": subscription.id,
        "number": subscription.number,
        "customer": (
            {"id": customer.id, "name": customer.name, "email": customer.email}
            if customer is not None
            else None
        ),
        "plan": (
            {
                "id": plan.id,
                "name": plan.name,
                "billing_period": plan.billing_period,
            }
            if plan is not None
            else None
        ),
        "status": subscription.status,
        "start_date": subscription.start_date,
        "expiry_date": subscription.expiry_date,
        "next_billing_date": subscription.next_billing_date,
        "payment_terms": subscription.payment_terms,
        "lines": subscription.lines,
        "subtotal": subscription.subtotal,
        "discount_total": subscription.discount_total,
        "total": subscription.total,
        "history": subscription.history,
    }
