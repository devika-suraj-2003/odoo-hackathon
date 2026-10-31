from datetime import date, datetime
from typing import List, Optional

from app.core.dependencies import get_current_user

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.billing import (
    get_next_billing_date,
    calculate_billing_period
)

from app.database import get_db
from app.models.subscription import (
    Subscription,
    SubscriptionLine,
    SubscriptionHistory,
)
from app.models.user import User
from app.models.plan import Plan
from app.models.product import Product
from app.models.product_variant import ProductVariant

router = APIRouter(tags=["Subscriptions"])


# ---------- Schemas ----------

class SubscriptionLineCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(default=1, gt=0)
    unit_price: int = Field(ge=0)


class SubscriptionCreate(BaseModel):
    customer_id: int
    plan_id: int
    template_id: Optional[int] = None
    start_date: date
    payment_terms: int = Field(default=0, ge=0)
    lines: List[SubscriptionLineCreate] = []


class HistoryResponse(BaseModel):
    at: Optional[datetime]
    from_status: Optional[str]
    to_status: str
    note: Optional[str] = None


class LineResponse(BaseModel):
    id: int
    product_name: Optional[str] = None
    quantity: int
    unit_price: int
    tax_amount: int = 0
    amount: int


class SubscriptionResponse(BaseModel):
    id: int
    number: str
    customer: dict
    plan: dict
    status: str
    start_date: date
    expiry_date: Optional[date]
    next_billing_date: Optional[date]
    payment_terms: int
    lines: List[LineResponse]
    subtotal: int
    tax_total: int
    total: int
    history: List[HistoryResponse]


# ---------- Helpers ----------

def get_subscription_or_404(db: Session, subscription_id: int):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return subscription



def generate_subscription_number(db: Session):
    last_subscription = (
        db.query(Subscription)
        .order_by(Subscription.id.desc())
        .first()
    )

    next_number = (
        last_subscription.id + 1
        if last_subscription
        else 1
    )

    return f"SUB-{next_number:04d}"


def serialize_subscription(subscription, db):
    customer = db.query(User).filter(
        User.id == subscription.customer_id
    ).first()

    plan = db.query(Plan).filter(
        Plan.id == subscription.plan_id
    ).first()

    lines = []
    subtotal = 0

    for line in subscription.lines:
        product = db.query(Product).filter(
            Product.id == line.product_id
        ).first()

        amount = line.qty * line.unit_price
        subtotal += amount

        lines.append({
            "id": line.id,
            "product_name": product.name if product else None,
            "quantity": line.qty,
            "unit_price": line.unit_price,
            "tax_amount": 0,
            "amount": amount
        })

    return {
        "id": subscription.id,
        "number": subscription.number,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email
        } if customer else None,
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "billing_period": plan.billing_period
        } if plan else None,
        "status": (
            "paused" if subscription.is_paused
            else subscription.status
        ),
        "start_date": subscription.start_date,
        "expiry_date": subscription.expiry_date,
        "next_billing_date": subscription.next_billing_date,
        "payment_terms": subscription.payment_terms_days,
        "lines": lines,
        "subtotal": subtotal,
        "tax_total": 0,
        "total": subtotal,
        "history": [
            {
                "at": item.changed_at,
                "from_status": item.from_status,
                "to_status": item.to_status,
                "note": item.note
            }
            for item in subscription.history
        ]
    }



def change_status(db, subscription, new_status, note=None):
    old_status = subscription.status

    subscription.status = new_status

    history = SubscriptionHistory(
        subscription_id=subscription.id,
        from_status=old_status,
        to_status=new_status,
        note=note
    )

    db.add(history)

    try:
        db.commit()
        db.refresh(subscription)
    except Exception:
        db.rollback()
        raise

    return serialize_subscription(subscription, db)


# ---------- List and Create ----------


@router.get("/")
def get_subscriptions(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Subscription)

    # Role-based access control
    if current_user.role == "customer":
        query = query.filter(
            Subscription.customer_id == current_user.id
        )

    elif current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view subscriptions"
        )

    # Optional filters
    if status:
        query = query.filter(Subscription.status == status)

    # Customers cannot override their own customer ID
    if customer_id and current_user.role != "customer":
        query = query.filter(
            Subscription.customer_id == customer_id
        )

    if search:
        query = query.filter(
            Subscription.number.ilike(f"%{search}%")
        )

    subscriptions = query.offset(skip).limit(limit).all()

    return [
        serialize_subscription(subscription, db)
        for subscription in subscriptions
    ]

@router.get("/{subscription_id}")
def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subscription = get_subscription_or_404(db, subscription_id)

    if current_user.role == "customer" and subscription.customer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this subscription"
        )

    if current_user.role not in ["admin", "staff", "customer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return serialize_subscription(subscription, db)

@router.post("/")
def create_subscription(
    data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Only staff and admin can create subscriptions")
    # 1. Validate plan
    plan = db.query(Plan).filter(
        Plan.id == data.plan_id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan not found"
        )

    if not plan.is_active:
        raise HTTPException(
            status_code=400,
            detail="This plan is currently inactive"
        )

    # 2. Validate plan validity dates
    if plan.start_date and data.start_date < plan.start_date:
        raise HTTPException(
            status_code=400,
            detail="Subscription start date is before plan validity"
        )

    if plan.end_date and data.start_date > plan.end_date:
        raise HTTPException(
            status_code=400,
            detail="Plan validity has expired"
        )

    # 3. Validate customer
    customer = db.query(User).filter(
        User.id == data.customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    # 4. Validate subscription lines
    if not data.lines:
        raise HTTPException(
            status_code=400,
            detail="At least one line is required"
        )

    if any(line.quantity < plan.min_qty for line in data.lines):
        raise HTTPException(
            status_code=400,
            detail="Minimum quantity not met"
        )

    # Validate all products and variants before creating subscription
    validated_lines = []

    for line in data.lines:

        if line.unit_price < 0:
            raise HTTPException(
                status_code=400,
                detail="Unit price cannot be negative"
            )

        product = db.query(Product).filter(
            Product.id == line.product_id
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {line.product_id} not found"
            )

        if line.variant_id is not None:
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == line.variant_id,
                ProductVariant.product_id == line.product_id
            ).first()

            if not variant:
                raise HTTPException(
                    status_code=400,
                    detail="Selected variant does not belong to this product"
                )

        validated_lines.append(line)

    # 5. Create subscription
    subscription = Subscription(
        number=generate_subscription_number(db),
        customer_id=data.customer_id,
        plan_id=data.plan_id,
        start_date=data.start_date,
        payment_terms_days=data.payment_terms,
        status="draft",
        next_billing_date=data.start_date
    )

    db.add(subscription)
    db.flush()

    # 6. Add subscription lines
    for line in validated_lines:

        # unit_price represents the final agreed price in paise
        unit_price = line.unit_price

        subscription.lines.append(
            SubscriptionLine(
                product_id=line.product_id,
                variant_id=line.variant_id,
                qty=line.quantity,
                unit_price=unit_price,
                amount=line.quantity * unit_price
            )
        )

    # 7. Record initial history
    db.add(
        SubscriptionHistory(
            subscription_id=subscription.id,
            from_status=None,
            to_status="draft"
        )
    )

    # 8. Save to database
    try:
        db.commit()
        db.refresh(subscription)
    except Exception:
        db.rollback()
        raise

    return serialize_subscription(subscription, db)



# ---------- Update ----------

@router.put("/{subscription_id}")
def update_subscription(
    subscription_id: int,
    data: SubscriptionCreate,
    db: Session = Depends(get_db)
):
    subscription = get_subscription_or_404(db, subscription_id)

    if subscription.status not in ["draft", "quotation"]:
        raise HTTPException(status_code=400, detail="Subscription cannot be edited")

    subscription.customer_id = data.customer_id
    subscription.plan_id = data.plan_id
    subscription.start_date = data.start_date
    subscription.payment_terms_days = data.payment_terms

    subscription.lines.clear()

    for line in data.lines:
        subscription.lines.append(
            SubscriptionLine(
                product_id=line.product_id,
                variant_id=line.variant_id,
                qty=line.quantity,
                unit_price=line.unit_price,
                amount=line.quantity * line.unit_price
            )
        )

    db.commit()
    db.refresh(subscription)

    return serialize_subscription(subscription, db)


# ---------- Status Actions ----------

@router.post("/{subscription_id}/send-quotation")
def send_quotation(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="Only staff and admin can send quotations"
        )

    subscription = get_subscription_or_404(db, subscription_id)

    if subscription.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft subscriptions can be sent")

    return change_status(db, subscription, "quotation")


@router.post("/{subscription_id}/confirm")
def confirm_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="Only staff and admin can confirm quotations"
        )

    subscription = get_subscription_or_404(db, subscription_id)

    if subscription.status != "quotation":
        raise HTTPException(status_code=400, detail="Only quotations can be confirmed")

    return change_status(db, subscription, "confirmed")


@router.post("/{subscription_id}/activate")
def activate_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="Only staff and admin can activate subscriptions"
        )

    subscription = get_subscription_or_404(db, subscription_id)

    if subscription.status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Only confirmed subscriptions can be activated"
        )

    return change_status(db, subscription, "active")

@router.post("/{subscription_id}/pause")
def pause_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="Only staff and admin can pause subscriptions"
        )

    subscription = get_subscription_or_404(db, subscription_id)

    if subscription.status != "active" or subscription.is_paused:
        raise HTTPException(
            status_code=400,
            detail="Only active subscriptions can be paused"
        )

    plan = db.query(Plan).filter(
        Plan.id == subscription.plan_id
    ).first()

    if not plan or not plan.pausable:
        raise HTTPException(
            status_code=400,
            detail="Pausing is not allowed for this plan"
        )

    subscription.is_paused = True

    db.add(SubscriptionHistory(
        subscription_id=subscription.id,
        from_status="active",
        to_status="paused",
        note="Subscription paused"
    ))

    try:
        db.commit()
        db.refresh(subscription)
    except Exception:
        db.rollback()
        raise

    return serialize_subscription(subscription, db)

@router.post("/{subscription_id}/resume")
def resume_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="Only staff and admin can resume subscriptions"
        )

    subscription = get_subscription_or_404(db, subscription_id)

    if subscription.status != "active" or not subscription.is_paused:
        raise HTTPException(
            status_code=400,
            detail="Subscription is not paused"
        )

    subscription.is_paused = False

    db.add(SubscriptionHistory(
        subscription_id=subscription.id,
        from_status="paused",
        to_status="active",
        note="Subscription resumed"
    ))

    try:
        db.commit()
        db.refresh(subscription)
    except Exception:
        db.rollback()
        raise

    return serialize_subscription(subscription, db)

@router.post("/{subscription_id}/renew")
def renew_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="Only staff and admin can renew subscriptions"
        )

    subscription = get_subscription_or_404(db, subscription_id)

    plan = db.query(Plan).filter(
        Plan.id == subscription.plan_id
    ).first()

    if not plan or not plan.renewable:
        raise HTTPException(
            status_code=400,
            detail="Renewal is not allowed"
        )

    if subscription.status != "closed":
        raise HTTPException(
            status_code=400,
            detail="Only closed subscriptions can be renewed"
        )

    today = date.today()

    try:
        next_date = get_next_billing_date(
            today,
            plan.billing_period
        )

        _, expiry_date = calculate_billing_period(
            today,
            plan.billing_period
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    old_status = subscription.status

    subscription.status = "active"
    subscription.is_paused = False
    subscription.start_date = today
    subscription.expiry_date = expiry_date
    subscription.next_billing_date = next_date

    db.add(SubscriptionHistory(
        subscription_id=subscription.id,
        from_status=old_status,
        to_status="active",
        note="Subscription renewed"
    ))

    try:
        db.commit()
        db.refresh(subscription)
    except Exception:
        db.rollback()
        raise

    return serialize_subscription(subscription, db)

@router.post("/{subscription_id}/close")
def close_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="Only staff and admin can close subscriptions"
        )

    subscription = get_subscription_or_404(db, subscription_id)

    if subscription.status not in ["active", "draft", "quotation"]:
        raise HTTPException(
            status_code=400,
            detail="Subscription cannot be closed"
        )

    plan = db.query(Plan).filter(
        Plan.id == subscription.plan_id
    ).first()

    if subscription.status == "active" and (
        not plan or not plan.closable
    ):
        raise HTTPException(
            status_code=400,
            detail="Closing is not allowed for this plan"
        )

    old_status = (
        "paused" if subscription.is_paused
        else subscription.status
    )

    subscription.status = "closed"
    subscription.is_paused = False

    db.add(SubscriptionHistory(
        subscription_id=subscription.id,
        from_status=old_status,
        to_status="closed",
        note="Subscription closed"
    ))

    try:
        db.commit()
        db.refresh(subscription)
    except Exception:
        db.rollback()
        raise

    return serialize_subscription(subscription, db)