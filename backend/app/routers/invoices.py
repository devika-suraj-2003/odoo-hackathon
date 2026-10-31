from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services import invoice as invoice_service

router = APIRouter(tags=["Invoices"])


def _get_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = invoice_service.get_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return invoice


def _require_staff(user: User) -> None:
    if user.role not in {"admin", "staff"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff and admin can perform this action.",
        )


def _authorize_read(invoice: Invoice, user: User) -> None:
    if user.role == "customer" and invoice.customer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this invoice.",
        )
    if user.role not in {"admin", "staff", "customer"}:
        raise HTTPException(status_code=403, detail="You are not authorized to access invoices.")


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
@router.post(
    "/", response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    try:
        invoice = invoice_service.create_invoice(db, invoice_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return invoice_service.invoice_response(db, invoice)


@router.get("", response_model=list[InvoiceResponse])
@router.get("/", response_model=list[InvoiceResponse], include_in_schema=False)
def list_invoices(
    subscription_id: Optional[int] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    customer_id: Optional[int] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Invoice)

    if subscription_id is not None:
        query = query.filter(Invoice.subscription_id == subscription_id)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if current_user.role == "customer":
        query = query.filter(Invoice.customer_id == current_user.id)
    elif current_user.role not in {"admin", "staff"}:
        raise HTTPException(status_code=403, detail="You are not authorized to view invoices.")
    elif customer_id is not None:
        query = query.filter(Invoice.customer_id == customer_id)

    invoices = query.order_by(Invoice.id.desc()).offset(skip).limit(limit).all()
    return [invoice_service.invoice_response(db, invoice) for invoice in invoices]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = _get_or_404(db, invoice_id)
    _authorize_read(invoice, current_user)
    return invoice_service.invoice_response(db, invoice)


@router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
def confirm_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    invoice = _get_or_404(db, invoice_id)
    try:
        invoice = invoice_service.confirm_invoice(db, invoice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return invoice_service.invoice_response(db, invoice)


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    invoice = _get_or_404(db, invoice_id)

    if invoice.status not in {"draft", "confirmed"} or invoice.amount_paid:
        raise HTTPException(status_code=400, detail="This invoice cannot be cancelled.")

    invoice.status = "cancelled"
    invoice.amount_due = 0
    db.commit()
    db.refresh(invoice)
    return invoice_service.invoice_response(db, invoice)


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_staff(current_user)
    invoice = _get_or_404(db, invoice_id)
    if invoice.status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Only confirmed invoices can be emailed.",
        )

    from app.services.email import send_invoice_email

    try:
        send_invoice_email(db, invoice)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return invoice_service.invoice_response(db, invoice)


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invoice = _get_or_404(db, invoice_id)
    _authorize_read(invoice, current_user)

    from app.services.pdf import generate_invoice_pdf

    pdf = generate_invoice_pdf(db, invoice)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'
        },
    )