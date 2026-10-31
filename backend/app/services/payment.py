import hashlib
import hmac
from datetime import date
from typing import Optional

from sqlalchemy import case
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.razorpay_order import RazorpayOrder
from app.schemas.payment import PaymentCreate, RazorpayVerifyRequest
from app.services import razorpay


def get_payments(db: Session, invoice_id: Optional[int] = None) -> list[Payment]:
    query = db.query(Payment)
    if invoice_id is not None:
        query = query.filter(Payment.invoice_id == invoice_id)
    return query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()


def record_payment(
    db: Session,
    payment_in: PaymentCreate,
    *,
    commit: bool = True,
) -> Payment:
    invoice = db.query(Invoice).filter(Invoice.id == payment_in.invoice_id).first()
    if invoice is None:
        raise ValueError("Invoice not found.")
    if invoice.status != "confirmed":
        raise ValueError("Payments can only be recorded against confirmed, unpaid invoices.")
    outstanding = invoice.amount_due
    if outstanding <= 0:
        raise ValueError("This invoice has no outstanding balance.")
    if payment_in.amount > outstanding:
        raise ValueError(
            f"Payment amount exceeds the outstanding balance of {outstanding} paise."
        )

    updated = (
        db.query(Invoice)
        .filter(
            Invoice.id == invoice.id,
            Invoice.status == "confirmed",
            Invoice.amount_due >= payment_in.amount,
        )
        .update(
            {
                Invoice.amount_paid: Invoice.amount_paid + payment_in.amount,
                Invoice.amount_due: Invoice.amount_due - payment_in.amount,
                Invoice.status: case(
                    (Invoice.amount_due == payment_in.amount, "paid"),
                    else_="confirmed",
                ),
            },
            synchronize_session=False,
        )
    )
    if updated != 1:
        db.rollback()
        raise ValueError("Payment exceeds the outstanding balance or invoice status changed.")

    payment = Payment(
        invoice_id=invoice.id,
        amount=payment_in.amount,
        method=payment_in.method.value,
        payment_date=payment_in.payment_date,
        note=payment_in.note.strip() if payment_in.note else None,
    )
    db.add(payment)
    if commit:
        db.commit()
        db.refresh(payment)
    return payment


def payment_response(db: Session, payment: Payment) -> dict:
    return {
        "id": payment.id,
        "invoice_id": payment.invoice_id,
        "method": payment.method,
        "amount": payment.amount,
        "payment_date": payment.payment_date,
        "note": payment.note,
    }


def create_razorpay_order(db: Session, invoice_id: int) -> dict:
    key_id, _ = razorpay.credentials()
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise ValueError("Invoice not found.")
    if invoice.status != "confirmed" or invoice.amount_due <= 0:
        raise ValueError("Only confirmed invoices with an outstanding balance can be paid.")

    amount = invoice.amount_due
    gateway_order = razorpay.create_order(amount, invoice_id)
    order_id = gateway_order.get("id")
    if (
        not isinstance(order_id, str)
        or not order_id
        or gateway_order.get("amount") != amount
        or gateway_order.get("currency") != "INR"
    ):
        raise razorpay.RazorpayGatewayError(
            "Razorpay returned an order that does not match the invoice balance."
        )
    db.add(
        RazorpayOrder(
            order_id=order_id,
            invoice_id=invoice.id,
            amount=amount,
            currency="INR",
            status="created",
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise razorpay.RazorpayGatewayError(
            "Could not save the Razorpay order. Please request a new checkout order."
        ) from exc
    return {
        "order_id": order_id,
        "amount": amount,
        "currency": "INR",
        "key_id": key_id,
    }


def verify_razorpay_payment(
    db: Session,
    request: RazorpayVerifyRequest,
) -> Payment:
    _, key_secret = razorpay.credentials()
    order = (
        db.query(RazorpayOrder)
        .filter(RazorpayOrder.order_id == request.razorpay_order_id)
        .first()
    )
    if order is None or order.invoice_id != request.invoice_id:
        raise ValueError("Razorpay order does not belong to this invoice.")
    if order.status != "created":
        raise ValueError("This Razorpay order has already been processed.")
    if (
        db.query(RazorpayOrder.id)
        .filter(RazorpayOrder.payment_id == request.razorpay_payment_id)
        .first()
        is not None
    ):
        raise ValueError("This Razorpay payment has already been recorded.")

    expected_signature = hmac.new(
        key_secret.encode("utf-8"),
        f"{request.razorpay_order_id}|{request.razorpay_payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, request.razorpay_signature):
        raise ValueError("Razorpay payment signature is invalid.")

    provider_payment = razorpay.get_payment(request.razorpay_payment_id)
    if (
        provider_payment.get("order_id") != order.order_id
        or provider_payment.get("amount") != order.amount
        or provider_payment.get("currency") != order.currency
        or provider_payment.get("status") != "captured"
    ):
        raise ValueError("Razorpay payment is not captured for the expected invoice amount.")

    invoice = db.query(Invoice).filter(Invoice.id == order.invoice_id).first()
    if (
        invoice is None
        or invoice.status != "confirmed"
        or invoice.amount_due != order.amount
    ):
        raise ValueError("Invoice balance changed after this Razorpay order was created.")

    try:
        payment = record_payment(
            db,
            PaymentCreate(
                invoice_id=order.invoice_id,
                amount=order.amount,
                method="razorpay",
                payment_date=date.today(),
                note="Razorpay payment",
            ),
            commit=False,
        )
        updated = (
            db.query(RazorpayOrder)
            .filter(
                RazorpayOrder.id == order.id,
                RazorpayOrder.status == "created",
            )
            .update(
                {
                    RazorpayOrder.status: "paid",
                    RazorpayOrder.payment_id: request.razorpay_payment_id,
                },
                synchronize_session=False,
            )
        )
        if updated != 1:
            db.rollback()
            raise ValueError("This Razorpay order has already been processed.")
        db.commit()
        db.refresh(payment)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("This Razorpay payment has already been recorded.") from exc
    except SQLAlchemyError:
        db.rollback()
        raise
    return payment
