from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import SubscriptionCreate
from app.services import subscription as subscription_service

router = APIRouter(tags=["Subscriptions"])


def _require_staff(user: User) -> None:
    if user.role not in {"admin", "staff"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff and admin can perform this action.",
        )


def _get_or_404(db: Session, subscription_id: int) -> Subscription:
    subscription = subscription_service.get_subscription(db, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    return subscription


def _authorize_read(subscription: Subscription, user: User) -> None:
    if user.role == "customer" and subscription.customer_id != user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to access this subscription.")
    if user.role not in {"admin", "staff", "customer"}:
        raise HTTPException(status_code=403, detail="You are not authorized to access subscriptions.")


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_subscription(
    subscription_in: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    try:
        subscription = subscription_service.create_subscription(db, subscription_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return subscription_service.subscription_response(db, subscription)


@router.get("")
@router.get("/", include_in_schema=False)
def list_subscriptions(
    status_filter: str | None = Query(default=None, alias="status"),
    customer_id: int | None = Query(default=None, ge=1),
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Subscription)
    if current_user.role == "customer":
        query = query.filter(Subscription.customer_id == current_user.id)
    elif current_user.role not in {"admin", "staff"}:
        raise HTTPException(status_code=403, detail="You are not authorized to view subscriptions.")
    elif customer_id is not None:
        query = query.filter(Subscription.customer_id == customer_id)

    if status_filter:
        query = query.filter(Subscription.status == status_filter)
    if search:
        query = query.filter(Subscription.number.ilike(f"%{search}%"))
    subscriptions = query.order_by(Subscription.id.desc()).offset(skip).limit(limit).all()
    return [
        subscription_service.subscription_response(db, subscription)
        for subscription in subscriptions
    ]


@router.get("/{subscription_id}")
def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subscription = _get_or_404(db, subscription_id)
    _authorize_read(subscription, current_user)
    return subscription_service.subscription_response(db, subscription)


@router.put("/{subscription_id}")
def update_subscription(
    subscription_id: int,
    subscription_in: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    subscription = _get_or_404(db, subscription_id)
    try:
        subscription = subscription_service.update_subscription(
            db,
            subscription,
            subscription_in,
            is_admin=(current_user.role == "admin"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return subscription_service.subscription_response(db, subscription)


@router.post("/{subscription_id}/{action}")
def update_subscription_status(
    subscription_id: int,
    action: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    subscription = _get_or_404(db, subscription_id)
    try:
        subscription = subscription_service.transition_subscription(
            db,
            subscription,
            action,
            changed_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return subscription_service.subscription_response(db, subscription)


@router.delete("/{subscription_id}")
def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete subscriptions.",
        )
    subscription = _get_or_404(db, subscription_id)
    subscription_service.delete_subscription(db, subscription)
    return {"detail": "Subscription deleted successfully", "id": subscription_id}
