from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.invoice import Invoice
from app.models.invoice import InvoiceLine

router = APIRouter(tags=["Invoices"])


class InvoiceLineResponse(BaseModel):
    id: int
    description: Optional[str] = None
    quantity: int
    unit_price: int
    tax_amount: int = 0
    amount: int


class CustomerResponse(BaseModel):
    id: int
    name: str


class InvoiceResponse(BaseModel):
    id: int
    number: str
    subscription_id: int
    customer: Optional[CustomerResponse]
    status: str
    invoice_date: date
    due_date: date
    period_start: date
    period_end: date
    lines: List[InvoiceLineResponse]
    subtotal: int
    discount_total: int
    tax_total: int
    total: int
    amount_paid: int = 0
    amount_due: int


def get_invoice_or_404(db: Session, invoice_id: int):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice


def serialize_invoice(invoice, db):
    from app.models.user import User

    customer = db.query(User).filter(
        User.id == invoice.customer_id
    ).first()

    lines = []
    for line in invoice.lines:
        lines.append({
            "id": line.id,
            "description": line.description,
            "quantity": line.qty,
            "unit_price": line.unit_price,
            "tax_amount": 0,
            "amount": line.amount
        })

    return {
        "id": invoice.id,
        "number": invoice.number,
        "subscription_id": invoice.subscription_id,
        "customer": {
            "id": customer.id,
            "name": customer.name
        } if customer else None,
        "status": invoice.status,
        "invoice_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "period_start": invoice.period_start,
        "period_end": invoice.period_end,
        "lines": lines,
        "subtotal": invoice.subtotal,
        "discount_total": invoice.discount_total,
        "tax_total": invoice.tax_total,
        "total": invoice.total,
        "amount_paid": 0,
        "amount_due": invoice.total
    }


@router.get("/")
def get_invoices(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Invoice)

    if status:
        query = query.filter(Invoice.status == status)

    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)

    invoices = query.order_by(
        Invoice.issue_date.desc()
    ).offset(skip).limit(limit).all()

    return [serialize_invoice(invoice, db) for invoice in invoices]


@router.get("/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = get_invoice_or_404(db, invoice_id)
    return serialize_invoice(invoice, db)


@router.post("/{invoice_id}/confirm")
def confirm_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = get_invoice_or_404(db, invoice_id)

    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be confirmed")

    invoice.status = "confirmed"
    db.commit()
    db.refresh(invoice)

    return serialize_invoice(invoice, db)


@router.post("/{invoice_id}/send")
def send_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = get_invoice_or_404(db, invoice_id)

    if invoice.status != "confirmed":
        raise HTTPException(status_code=400, detail="Only confirmed invoices can be sent")

    return {"message": "Invoice is ready to be sent", "invoice_id": invoice.id}


@router.post("/{invoice_id}/cancel")
def cancel_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = get_invoice_or_404(db, invoice_id)

    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Paid invoices cannot be cancelled")

    if invoice.status == "cancelled":
        raise HTTPException(status_code=400, detail="Invoice is already cancelled")

    invoice.status = "cancelled"
    db.commit()

    return serialize_invoice(invoice, db)