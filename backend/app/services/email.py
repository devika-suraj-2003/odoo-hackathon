import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.user import User


def _environment_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _smtp_settings() -> dict:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    required = (
        "SMTP_HOST",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM_EMAIL",
    )
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise ValueError(
            "Email is not configured. Set these environment variables: "
            + ", ".join(missing)
            + "."
        )
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be a valid port number.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("SMTP_PORT must be between 1 and 65535.")

    use_ssl = _environment_flag("SMTP_USE_SSL", False)
    return {
        "host": os.environ["SMTP_HOST"],
        "port": port,
        "username": os.environ["SMTP_USERNAME"],
        "password": os.environ["SMTP_PASSWORD"],
        "from_email": os.environ["SMTP_FROM_EMAIL"],
        "use_tls": _environment_flag("SMTP_USE_TLS", True) and not use_ssl,
        "use_ssl": use_ssl,
    }


def send_invoice_email(db: Session, invoice: Invoice) -> None:
    from app.services.pdf import generate_invoice_pdf

    customer = db.query(User).filter(User.id == invoice.customer_id).first()
    if customer is None or not customer.email:
        raise ValueError("The invoice customer does not have an email address.")
    settings = _smtp_settings()

    message = EmailMessage()
    message["Subject"] = f"Brightloop invoice {invoice.number}"
    message["From"] = settings["from_email"]
    message["To"] = customer.email
    message.set_content(
        f"Hello {customer.name},\n\n"
        f"Please find invoice {invoice.number} attached. "
        f"The outstanding balance is INR {invoice.amount_due / 100:,.2f}.\n\n"
        "Regards,\nBrightloop Software"
    )
    message.add_attachment(
        generate_invoice_pdf(db, invoice),
        maintype="application",
        subtype="pdf",
        filename=f"{invoice.number}.pdf",
    )

    try:
        smtp_class = smtplib.SMTP_SSL if settings["use_ssl"] else smtplib.SMTP
        with smtp_class(settings["host"], settings["port"], timeout=15) as server:
            if settings["use_tls"]:
                server.starttls(context=ssl.create_default_context())
            server.login(settings["username"], settings["password"])
            refused = server.send_message(message)
            if customer.email in refused:
                raise RuntimeError(
                    f"The configured SMTP server refused the recipient {customer.email}."
                )
    except (smtplib.SMTPException, OSError) as exc:
        raise RuntimeError(
            f"Could not send invoice email using the configured SMTP server: {exc}"
        ) from exc
