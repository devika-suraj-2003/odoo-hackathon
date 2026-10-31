from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    RazorpayOrderRequest,
    RazorpayOrderResponse,
    RazorpayVerifyRequest,
)
from app.services import payment as payment_service
from app.services.razorpay import RazorpayConfigurationError, RazorpayGatewayError

router = APIRouter(tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_payment(payment_in: PaymentCreate, db: Session = Depends(get_db)):
    try:
        payment = payment_service.record_payment(db, payment_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return payment_service.payment_response(db, payment)


@router.post("/razorpay/order", response_model=RazorpayOrderResponse)
def create_razorpay_order(
    request: RazorpayOrderRequest,
    db: Session = Depends(get_db),
):
    try:
        return payment_service.create_razorpay_order(db, request.invoice_id)
    except RazorpayConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RazorpayGatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/razorpay/verify", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def verify_razorpay_payment(
    request: RazorpayVerifyRequest,
    db: Session = Depends(get_db),
):
    try:
        payment = payment_service.verify_razorpay_payment(db, request)
    except RazorpayConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RazorpayGatewayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return payment_service.payment_response(db, payment)


@router.get("", response_model=list[PaymentResponse])
@router.get("/", response_model=list[PaymentResponse], include_in_schema=False)
def list_payments(
    invoice_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    payments = payment_service.get_payments(db, invoice_id=invoice_id)
    return [payment_service.payment_response(db, payment) for payment in payments]
