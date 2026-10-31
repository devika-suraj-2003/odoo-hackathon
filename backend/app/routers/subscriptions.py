from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.subscription import SubscriptionCreate
from app.services import subscription as subscription_service

router = APIRouter(tags=["Subscriptions"])


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_subscription(
    subscription_in: SubscriptionCreate,
    db: Session = Depends(get_db),
):
    try:
        subscription = subscription_service.create_subscription(db, subscription_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return subscription_service.subscription_response(db, subscription)


@router.get("")
@router.get("/", include_in_schema=False)
def list_subscriptions(db: Session = Depends(get_db)):
    subscriptions = subscription_service.get_subscriptions(db)
    return [
        subscription_service.subscription_response(db, subscription)
        for subscription in subscriptions
    ]


@router.get("/{subscription_id}")
def get_subscription(subscription_id: int, db: Session = Depends(get_db)):
    subscription = subscription_service.get_subscription(db, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    return subscription_service.subscription_response(db, subscription)


@router.post("/{subscription_id}/{action}")
def update_subscription_status(
    subscription_id: int,
    action: str,
    db: Session = Depends(get_db),
):
    subscription = subscription_service.get_subscription(db, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    try:
        subscription = subscription_service.transition_subscription(
            db, subscription, action
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return subscription_service.subscription_response(db, subscription)
