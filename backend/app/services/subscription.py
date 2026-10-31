from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.invoice import Invoice
from app.models.subscription import (
    Subscription,
    SubscriptionHistory,
    SubscriptionLine,
)
from app.models.tax import Tax
from app.models.user import User
from app.schemas.subscription import SubscriptionCreate
from app.services.discount import calculate_discount, consume_discount
from app.services.clock import today as business_today


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
    today = business_today(db)
    customer = db.query(User).filter(User.id == subscription_in.customer_id).first()
    if customer is None:
        raise ValueError("Customer not found.")
    plan = db.query(Plan).filter(Plan.id == subscription_in.plan_id).first()
    if plan is None or not plan.is_active:
        raise ValueError("An active plan is required.")
    if plan.start_date and subscription_in.start_date < plan.start_date:
        raise ValueError("Subscription start date is before plan validity.")
    if plan.end_date and subscription_in.start_date > plan.end_date:
        raise ValueError("Plan validity has expired.")
    if any(line.quantity < plan.min_qty for line in subscription_in.lines):
        raise ValueError("Minimum quantity not met.")
    product_ids = sorted({line.product_id for line in subscription_in.lines})
    products = {
        product.id: product
        for product in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }
    if len(products) != len(product_ids):
        raise ValueError("One or more selected products could not be found.")
    for line in subscription_in.lines:
        if line.variant_id is not None and (
            db.query(ProductVariant.id)
            .filter(
                ProductVariant.id == line.variant_id,
                ProductVariant.product_id == line.product_id,
            )
            .first()
            is None
        ):
            raise ValueError("Selected variant does not belong to this product.")
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
        number=f"SUB-{today:%Y%m%d}-{uuid4().hex[:8].upper()}",
        customer_id=customer.id,
        plan_id=plan.id,
        status="draft",
        start_date=subscription_in.start_date,
        expiry_date=plan.end_date,
        next_billing_date=_add_billing_period(
            subscription_in.start_date, plan.billing_period
        ),
        payment_terms=subscription_in.payment_terms,
        payment_terms_days={
            "immediate": 0,
            "15_days": 15,
            "30_days": 30,
        }.get(subscription_in.payment_terms, 0),
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
        history_entries=[
            SubscriptionHistory(
                from_status=None,
                to_status="draft",
                note="Subscription created",
            )
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


def update_subscription(
    db: Session,
    subscription: Subscription,
    subscription_in: SubscriptionCreate,
) -> Subscription:
    if subscription.status not in {"draft", "quotation"}:
        raise ValueError("Subscription cannot be edited.")

    customer = db.query(User).filter(User.id == subscription_in.customer_id).first()
    plan = db.query(Plan).filter(Plan.id == subscription_in.plan_id).first()
    if customer is None:
        raise ValueError("Customer not found.")
    if plan is None or not plan.is_active:
        raise ValueError("An active plan is required.")
    if plan.start_date and subscription_in.start_date < plan.start_date:
        raise ValueError("Subscription start date is before plan validity.")
    if plan.end_date and subscription_in.start_date > plan.end_date:
        raise ValueError("Plan validity has expired.")
    if any(line.quantity < plan.min_qty for line in subscription_in.lines):
        raise ValueError("Minimum quantity not met.")

    product_ids = sorted({line.product_id for line in subscription_in.lines})
    products = {
        product.id: product
        for product in db.query(Product).filter(Product.id.in_(product_ids)).all()
    }
    if len(products) != len(product_ids):
        raise ValueError("One or more selected products could not be found.")
    tax_ids = sorted(
        {line.tax_id for line in subscription_in.lines if line.tax_id is not None}
    )
    taxes = {
        tax.id: tax for tax in db.query(Tax).filter(Tax.id.in_(tax_ids)).all()
    }
    if len(taxes) != len(tax_ids):
        raise ValueError("One or more selected taxes could not be found.")
    if any(not tax.is_active for tax in taxes.values()):
        raise ValueError("Inactive taxes cannot be applied to a subscription.")
    for line in subscription_in.lines:
        if line.variant_id is not None and (
            db.query(ProductVariant.id)
            .filter(
                ProductVariant.id == line.variant_id,
                ProductVariant.product_id == line.product_id,
            )
            .first()
            is None
        ):
            raise ValueError("Selected variant does not belong to this product.")

    subtotal = sum(line.unit_price * line.quantity for line in subscription_in.lines)
    discount_total = 0
    if subscription_in.discount_id is not None:
        from app.models.discount import Discount

        discount = (
            db.query(Discount)
            .filter(Discount.id == subscription_in.discount_id)
            .first()
        )
        if discount is None:
            raise ValueError("Discount not found.")
        discount_total = calculate_discount(
            discount=discount,
            subtotal=subtotal,
            quantity=sum(line.quantity for line in subscription_in.lines),
            applies_to="subscription",
            product_ids=[],
        )

    raw_lines = [
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
    subscription.customer_id = customer.id
    subscription.plan_id = plan.id
    subscription.start_date = subscription_in.start_date
    subscription.expiry_date = plan.end_date
    subscription.next_billing_date = _add_billing_period(
        subscription_in.start_date, plan.billing_period
    )
    subscription.payment_terms = subscription_in.payment_terms
    subscription.payment_terms_days = {
        "immediate": 0,
        "15_days": 15,
        "30_days": 30,
    }.get(subscription_in.payment_terms, 0)
    subscription.lines = raw_lines
    subscription.line_items = [
        SubscriptionLine(
            product_id=line["product_id"],
            variant_id=line["variant_id"],
            tax_id=line["tax_id"],
            product_name=line["product_name"],
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            tax_amount=0,
            amount=line["amount"],
        )
        for line in raw_lines
    ]
    subscription.subtotal = subtotal
    subscription.discount_id = subscription_in.discount_id
    subscription.discount_total = discount_total
    subscription.discount_usage_recorded = False
    subscription.total = subtotal - discount_total
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
    invoice_lines = [
        {
            "description": line["product_name"],
            "product_id": line["product_id"],
            "quantity": line["quantity"],
            "unit_price": line["unit_price"],
            "tax_id": line.get("tax_id"),
        }
        for line in raw_lines
    ]
    from app.services.invoice import _calculate_invoice_totals, _relational_lines

    customer = db.query(User).filter(User.id == subscription.customer_id).first()
    customer_state = (customer.state or "").strip() if customer is not None else None
    invoice_lines, subtotal, tax_total = _calculate_invoice_totals(
        db,
        invoice_lines,
        subscription.discount_total,
        customer_state or None,
    )
    total = sum(line["amount"] for line in invoice_lines)
    invoice_date = business_today(db)
    due_date = invoice_date
    if subscription.payment_terms_days:
        due_date += timedelta(days=subscription.payment_terms_days)
    elif subscription.payment_terms == "15_days":
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
        line_items=_relational_lines(invoice_lines),
        subtotal=subtotal,
        discount_total=subscription.discount_total,
        discount_subtotal=subtotal,
        tax_total=tax_total,
        total=total,
        amount_due=total,
        customer_state=customer_state or None,
    )
    db.add(invoice)
    if renewal:
        subscription.next_billing_date = period_end
    return invoice


def transition_subscription(
    db: Session,
    subscription: Subscription,
    action: str,
    changed_by: int | None = None,
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
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
    if action == "pause" and (plan is None or not plan.pausable):
        raise ValueError("Pausing is not allowed for this plan.")
    if action == "close" and subscription.status in {"active", "paused"} and (
        plan is None or not plan.closable
    ):
        raise ValueError("Closing is not allowed for this plan.")
    if action == "renew" and (plan is None or not plan.renewable):
        raise ValueError("Renewal is not allowed for this plan.")
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
    subscription.is_paused = target == "paused"
    note = action.replace("-", " ").capitalize()
    changed_at = datetime.now(timezone.utc)
    subscription.history = [
        *subscription.history,
        {
            "at": changed_at.isoformat(),
            "from_status": previous,
            "to_status": target,
            "note": note,
        },
    ]
    subscription.history_entries.append(
        SubscriptionHistory(
            from_status=previous,
            to_status=target,
            note=note,
            changed_by=changed_by,
            changed_at=changed_at,
        )
    )
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
