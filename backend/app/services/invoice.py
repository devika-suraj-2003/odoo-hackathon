from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.discount import Discount
from app.models.invoice import Invoice
from app.models.tax import Tax
from app.models.user import User
from app.schemas.invoice import InvoiceCreate
from app.services.discount import calculate_discount, consume_discount
from app.services.tax import apply_tax_to_amount


def _allocate_discount(
    lines: list[dict],
    discount_total: int,
    subtotal: int,
    discounted_product_ids: list[int] | None,
) -> list[int]:
    if not lines or not discount_total or not subtotal:
        return [0] * len(lines)
    eligible = [
        index
        for index, line in enumerate(lines)
        if discounted_product_ids is None
        or line.get("product_id") in discounted_product_ids
    ]
    eligible_subtotal = sum(
        lines[index]["unit_price"] * lines[index]["quantity"] for index in eligible
    )
    if discount_total > eligible_subtotal:
        raise ValueError("Discount amount exceeds the eligible invoice subtotal.")
    allocated = [0] * len(lines)
    for index in eligible:
        line = lines[index]
        line_subtotal = line["unit_price"] * line["quantity"]
        allocated[index] = discount_total * line_subtotal // eligible_subtotal
    remaining = discount_total - sum(allocated)
    for index in reversed(eligible):
        line_subtotal = lines[index]["unit_price"] * lines[index]["quantity"]
        extra = min(remaining, line_subtotal - allocated[index])
        allocated[index] += extra
        remaining -= extra
        if remaining == 0:
            break
    return allocated


def _calculate_invoice_totals(
    db: Session,
    lines: list[dict],
    discount_total: int,
    customer_state: str | None,
    discounted_product_ids: list[int] | None = None,
) -> tuple[list[dict], int, int]:
    subtotal = sum(line["unit_price"] * line["quantity"] for line in lines)
    allocated = _allocate_discount(lines, discount_total, subtotal, discounted_product_ids)
    calculated_lines = []
    tax_total = 0
    for line, line_discount in zip(lines, allocated):
        line_subtotal = line["unit_price"] * line["quantity"]
        taxable_amount = line_subtotal - line_discount
        line_tax = 0
        breakdown = None
        if line.get("tax_id") is not None:
            tax = db.query(Tax).filter(Tax.id == line["tax_id"]).first()
            if tax is None:
                raise ValueError(f"Tax rule with ID {line['tax_id']} was not found.")
            if not tax.is_active:
                raise ValueError(f"Tax rule '{tax.name}' is inactive.")
            tax_result = apply_tax_to_amount(taxable_amount, tax, customer_state)
            line_tax = tax_result["tax_amount_paise"]
            breakdown = tax_result.get("gst_breakdown")
            if breakdown is not None:
                breakdown = {
                    key: str(value) if isinstance(value, Decimal) else value
                    for key, value in breakdown.items()
                }
        tax_total += line_tax
        calculated_lines.append(
            {
                **line,
                "tax_amount": line_tax,
                "discount_amount": line_discount,
                "amount": taxable_amount + line_tax,
                "gst_breakdown": breakdown,
            }
        )
    return calculated_lines, subtotal, tax_total


def create_invoice(db: Session, invoice_in: InvoiceCreate) -> Invoice:
    customer = db.query(User).filter(User.id == invoice_in.customer_id).first()
    if customer is None:
        raise ValueError("Customer not found.")
    if invoice_in.subscription_id is not None:
        from app.models.subscription import Subscription

        if db.query(Subscription.id).filter(Subscription.id == invoice_in.subscription_id).first() is None:
            raise ValueError("Subscription not found.")

    raw_lines = [line.model_dump() for line in invoice_in.lines]
    product_ids = sorted({line["product_id"] for line in raw_lines if line["product_id"] is not None})
    subtotal = sum(line["unit_price"] * line["quantity"] for line in raw_lines)
    discount_total = 0
    discount_subtotal = subtotal
    discount_quantity = sum(line["quantity"] for line in raw_lines)
    discounted_product_ids = None
    applies_to = "subscription" if invoice_in.subscription_id is not None else "products"
    if invoice_in.discount_id is not None:
        discount = db.query(Discount).filter(Discount.id == invoice_in.discount_id).first()
        if discount is None:
            raise ValueError("Discount not found.")
        if discount.applies_to == "products":
            discounted_product_ids = discount.product_ids
            eligible_lines = [
                line for line in raw_lines if line.get("product_id") in discounted_product_ids
            ]
        else:
            eligible_lines = raw_lines
        discount_subtotal = sum(
            line["unit_price"] * line["quantity"] for line in eligible_lines
        )
        discount_quantity = sum(line["quantity"] for line in eligible_lines)
        discount_total = calculate_discount(
            discount=discount,
            subtotal=discount_subtotal,
            quantity=discount_quantity,
            applies_to=applies_to,
            product_ids=sorted(
                {
                    line["product_id"]
                    for line in eligible_lines
                    if line["product_id"] is not None
                }
            ),
        )

    customer_state = (invoice_in.customer_state or customer.state or "").strip() or None
    calculated_lines, subtotal, tax_total = _calculate_invoice_totals(
        db, raw_lines, discount_total, customer_state, discounted_product_ids
    )
    total = sum(line["amount"] for line in calculated_lines)
    invoice = Invoice(
        number=f"INV-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}",
        customer_id=customer.id,
        subscription_id=invoice_in.subscription_id,
        status="draft",
        due_date=invoice_in.due_date,
        period_start=invoice_in.period_start,
        period_end=invoice_in.period_end,
        lines=calculated_lines,
        subtotal=subtotal,
        discount_total=discount_total,
        discount_subtotal=discount_subtotal,
        tax_total=tax_total,
        total=total,
        amount_due=total,
        discount_id=invoice_in.discount_id,
        discount_quantity=discount_quantity,
        customer_state=customer_state,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def get_invoices(db: Session, subscription_id: int | None = None) -> list[Invoice]:
    query = db.query(Invoice)
    if subscription_id is not None:
        query = query.filter(Invoice.subscription_id == subscription_id)
    return query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).all()


def get_invoice(db: Session, invoice_id: int) -> Invoice | None:
    return db.query(Invoice).filter(Invoice.id == invoice_id).first()


def confirm_invoice(db: Session, invoice: Invoice) -> Invoice:
    if invoice.status != "draft":
        raise ValueError(f"Only draft invoices can be confirmed (current status: {invoice.status}).")
    try:
        if invoice.discount_id is not None and not invoice.discount_usage_recorded:
            discount = db.query(Discount).filter(Discount.id == invoice.discount_id).first()
            if discount is None:
                raise ValueError("Discount not found.")
            if discount.applies_to == "products":
                discounted_product_ids = discount.product_ids
                eligible_lines = [
                    line
                    for line in invoice.lines
                    if line.get("product_id") in discounted_product_ids
                ]
            else:
                discounted_product_ids = None
                eligible_lines = invoice.lines
            discount_subtotal = sum(
                line["unit_price"] * line["quantity"] for line in eligible_lines
            )
            discount_quantity = sum(line["quantity"] for line in eligible_lines)
            discount_total = consume_discount(
                db,
                discount_id=invoice.discount_id,
                subtotal=discount_subtotal,
                quantity=discount_quantity,
                applies_to=discount.applies_to,
                product_ids=sorted(
                    {
                        line["product_id"]
                        for line in eligible_lines
                        if line.get("product_id") is not None
                    }
                ),
            )
            calculated_lines, subtotal, tax_total = _calculate_invoice_totals(
                db,
                invoice.lines,
                discount_total,
                invoice.customer_state,
                discounted_product_ids,
            )
            invoice.lines = calculated_lines
            invoice.subtotal = subtotal
            invoice.discount_total = discount_total
            invoice.discount_subtotal = discount_subtotal
            invoice.discount_quantity = discount_quantity
            invoice.tax_total = tax_total
            invoice.total = sum(line["amount"] for line in calculated_lines)
            invoice.amount_due = invoice.total - invoice.amount_paid
            invoice.discount_usage_recorded = True
        invoice.status = "confirmed"
        db.commit()
    except ValueError:
        db.rollback()
        raise
    db.refresh(invoice)
    return invoice


def invoice_response(db: Session, invoice: Invoice) -> dict:
    customer = db.query(User).filter(User.id == invoice.customer_id).first()
    return {
        "id": invoice.id,
        "number": invoice.number,
        "subscription_id": invoice.subscription_id,
        "customer": (
            {"id": customer.id, "name": customer.name, "email": customer.email}
            if customer is not None
            else None
        ),
        "status": invoice.status,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "period_start": invoice.period_start,
        "period_end": invoice.period_end,
        "lines": invoice.lines,
        "subtotal": invoice.subtotal,
        "discount_total": invoice.discount_total,
        "tax_total": invoice.tax_total,
        "total": invoice.total,
        "amount_paid": invoice.amount_paid,
        "amount_due": invoice.amount_due,
    }
