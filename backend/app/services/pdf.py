from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.user import User
from app.services.report import monthly_revenue, report_summary


def _money(amount_paise: int | None) -> str:
    return f"INR {(amount_paise or 0) / 100:,.2f}"


def _pdf_document(story: list) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Brightloop report",
        author="Brightloop",
    )
    document.build(story)
    return buffer.getvalue()


def generate_invoice_pdf(db: Session, invoice: Invoice) -> bytes:
    customer = db.query(User).filter(User.id == invoice.customer_id).first()
    if customer is None:
        raise ValueError("The invoice customer record could not be found.")

    styles = getSampleStyleSheet()
    title = ParagraphStyle("InvoiceTitle", parent=styles["Title"], alignment=TA_RIGHT)
    story = [
        Table(
            [
                [
                    Paragraph("<b>Brightloop Software</b><br/>Subscription Management", styles["Normal"]),
                    Paragraph(f"<b>INVOICE</b><br/>{escape(invoice.number)}", title),
                ]
            ],
            colWidths=[90 * mm, 85 * mm],
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            f"<b>Billed to:</b> {escape(customer.name)}"
            + (f" &lt;{escape(customer.email)}&gt;" if customer.email else ""),
            styles["Normal"],
        ),
        Paragraph(
            f"Status: {escape(invoice.status)} &nbsp;&nbsp; "
            f"Invoice date: {invoice.invoice_date:%d %b %Y} &nbsp;&nbsp; "
            f"Due date: {invoice.due_date:%d %b %Y}" if invoice.due_date else
            f"Status: {escape(invoice.status)} &nbsp;&nbsp; Invoice date: {invoice.invoice_date:%d %b %Y}",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
    ]

    rows = [["Description", "Qty", "Unit price", "Tax", "Amount"]]
    for line in invoice.lines:
        rows.append(
            [
                Paragraph(escape(str(line.get("description", ""))), styles["Normal"]),
                str(line.get("quantity", 0)),
                _money(line.get("unit_price")),
                _money(line.get("tax_amount")),
                _money(line.get("amount")),
            ]
        )
    table = Table(rows, colWidths=[75 * mm, 15 * mm, 28 * mm, 25 * mm, 30 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([table, Spacer(1, 7 * mm)])

    totals = [
        ["Subtotal", _money(invoice.subtotal)],
        ["Discount", f"- {_money(invoice.discount_total)}"],
        ["Tax", _money(invoice.tax_total)],
        ["Total", _money(invoice.total)],
        ["Paid", _money(invoice.amount_paid)],
        ["Amount due", _money(invoice.amount_due)],
    ]
    totals_table = Table(totals, colWidths=[35 * mm, 35 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -3), (-1, -3), 0.7, colors.HexColor("#64748b")),
                ("TEXTCOLOR", (1, -1), (1, -1), colors.HexColor("#b45309")),
            ]
        )
    )
    story.append(totals_table)
    payments = (
        db.query(Payment)
        .filter(Payment.invoice_id == invoice.id)
        .order_by(Payment.payment_date.asc(), Payment.id.asc())
        .all()
    )
    if payments:
        story.extend([Spacer(1, 8 * mm), Paragraph("<b>Payment history</b>", styles["Heading2"])])
        history_rows = [["Date", "Method", "Amount", "Note"]]
        history_rows.extend(
            [
                [
                    payment.payment_date.strftime("%d %b %Y"),
                    escape(payment.method.replace("_", " ").title()),
                    _money(payment.amount),
                    escape(payment.note or ""),
                ]
                for payment in payments
            ]
        )
        history = Table(history_rows, colWidths=[30 * mm, 35 * mm, 35 * mm, 70 * mm], repeatRows=1)
        history.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ]
            )
        )
        story.append(history)
    return _pdf_document(story)


def generate_report_pdf(db: Session) -> bytes:
    summary = report_summary(db)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Brightloop subscription & revenue report", styles["Title"]),
        Paragraph("Generated from recorded subscriptions, invoices, and payments.", styles["Normal"]),
        Spacer(1, 8 * mm),
    ]
    summary_rows = [
        ["Metric", "Value"],
        ["Active subscriptions", str(summary["active_subscriptions"])],
        ["Monthly recurring revenue (MRR)", _money(summary["mrr"])],
        ["Annual recurring revenue (ARR)", _money(summary["arr"])],
        ["Collected revenue", _money(summary["revenue"])],
        ["Outstanding payments", _money(summary["outstanding"])],
        [
            f"Overdue invoices ({summary['overdue_count']})",
            _money(summary["overdue_amount"]),
        ],
    ]
    table = Table(summary_rows, colWidths=[105 * mm, 65 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([table, Spacer(1, 8 * mm), Paragraph("Monthly collected revenue", styles["Heading2"])])
    revenue_rows = [["Month", "Collected"]]
    revenue_rows.extend(
        [[item["month"], _money(item["revenue"])] for item in monthly_revenue(db, 12)]
    )
    revenue_table = Table(revenue_rows, colWidths=[85 * mm, 85 * mm], repeatRows=1)
    revenue_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ]
        )
    )
    story.append(revenue_table)
    return _pdf_document(story)
