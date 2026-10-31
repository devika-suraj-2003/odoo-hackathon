from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services import invoice as invoice_service

router = APIRouter(tags=["Invoices"])


def _get_or_404(db: Session, invoice_id: int) -> Invoice:
    invoice = invoice_service.get_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return invoice


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_invoice(invoice_in: InvoiceCreate, db: Session = Depends(get_db)):
    try:
        invoice = invoice_service.create_invoice(db, invoice_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return invoice_service.invoice_response(db, invoice)


@router.get("", response_model=list[InvoiceResponse])
@router.get("/", response_model=list[InvoiceResponse], include_in_schema=False)
def list_invoices(
    subscription_id: int | None = None,
    db: Session = Depends(get_db),
):
    invoices = invoice_service.get_invoices(db, subscription_id=subscription_id)
    return [invoice_service.invoice_response(db, invoice) for invoice in invoices]


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return invoice_service.invoice_response(db, _get_or_404(db, invoice_id))


@router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
def confirm_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_or_404(db, invoice_id)
    try:
        invoice = invoice_service.confirm_invoice(db, invoice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return invoice_service.invoice_response(db, invoice)


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_or_404(db, invoice_id)
    if invoice.status not in {"draft", "confirmed"} or invoice.amount_paid:
        raise HTTPException(status_code=400, detail="This invoice cannot be cancelled.")
    invoice.status = "cancelled"
    invoice.amount_due = 0
    db.commit()
    db.refresh(invoice)
    return invoice_service.invoice_response(db, invoice)


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
def send_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_or_404(db, invoice_id)
    if invoice.status != "confirmed":
        raise HTTPException(status_code=400, detail="Only confirmed invoices can be emailed.")
    from app.services.email import send_invoice_email

    try:
        send_invoice_email(db, invoice)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return invoice_service.invoice_response(db, invoice)


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_or_404(db, invoice_id)
    from app.services.pdf import generate_invoice_pdf

    pdf = generate_invoice_pdf(db, invoice)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.number}.pdf"'},
    )
