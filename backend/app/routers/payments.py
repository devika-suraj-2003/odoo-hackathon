from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_staff_or_admin
from app.database import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.payment import (
    PaymentCreate,
    PaymentResponse,
    RazorpayOrderRequest,
    RazorpayOrderResponse,
    RazorpayVerifyRequest,
)
from app.services import payment as payment_service
from app.services.razorpay import RazorpayConfigurationError, RazorpayGatewayError

# Every payment route needs a logged-in user.
router = APIRouter(tags=["Payments"], dependencies=[Depends(get_current_user)])


def _check_invoice_owner(db: Session, invoice_id: int, user: User) -> None:
    """Customers may only pay their own invoices; admin and staff may act on any invoice."""
    if user.role in ("admin", "staff"):
        return
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None or invoice.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only pay your own invoices.")


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_payment(
    payment_in: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin),
):
    try:
        payment = payment_service.record_payment(db, payment_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return payment_service.payment_response(db, payment)


@router.post("/razorpay/order", response_model=RazorpayOrderResponse)
def create_razorpay_order(
    request: RazorpayOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_invoice_owner(db, request.invoice_id, current_user)
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
    current_user: User = Depends(get_current_user),
):
    _check_invoice_owner(db, request.invoice_id, current_user)
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
    current_user: User = Depends(get_current_user),
):
    payments = payment_service.get_payments(db, invoice_id=invoice_id)
    if current_user.role not in ("admin", "staff"):
        own_invoice_ids = {
            row.id for row in db.query(Invoice.id).filter(Invoice.customer_id == current_user.id).all()
        }
        payments = [payment for payment in payments if payment.invoice_id in own_invoice_ids]
    return [payment_service.payment_response(db, payment) for payment in payments]