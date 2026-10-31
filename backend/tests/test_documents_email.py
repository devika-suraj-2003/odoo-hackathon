from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.invoice import Invoice
from app.models.user import User
from app.services.email import _smtp_settings, send_invoice_email
from app.services.pdf import generate_invoice_pdf, generate_report_pdf


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    customer = User(
        name="Customer",
        email="customer@example.test",
        password_hash="not-a-real-password",
    )
    session.add(customer)
    session.commit()
    invoice = Invoice(
        number="INV-TEST",
        customer_id=customer.id,
        status="confirmed",
        invoice_date=date.today(),
        lines=[
            {
                "description": "Subscription",
                "quantity": 1,
                "unit_price": 10000,
                "tax_amount": 1800,
                "amount": 11800,
            }
        ],
        subtotal=10000,
        tax_total=1800,
        total=11800,
        amount_due=11800,
    )
    session.add(invoice)
    session.commit()
    try:
        yield session, invoice
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_invoice_and_report_pdf_are_downloadable_documents(db):
    session, invoice = db
    invoice_pdf = generate_invoice_pdf(session, invoice)
    report_pdf = generate_report_pdf(session)
    assert invoice_pdf.startswith(b"%PDF-")
    assert report_pdf.startswith(b"%PDF-")


def test_email_configuration_error_lists_missing_environment_variables(monkeypatch):
    monkeypatch.setattr("app.services.email.load_dotenv", lambda *args, **kwargs: None)
    for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="Email is not configured") as error:
        _smtp_settings()
    assert "SMTP_HOST" in str(error.value)
    assert "SMTP_PASSWORD" in str(error.value)


def test_invoice_email_authenticates_and_attaches_pdf(db, monkeypatch):
    session, invoice = db
    monkeypatch.setattr(
        "app.services.email._smtp_settings",
        lambda: {
            "host": "smtp.example.test",
            "port": 587,
            "username": "mailer",
            "password": "test-only",
            "from_email": "billing@example.test",
            "use_tls": True,
            "use_ssl": False,
        },
    )
    smtp = MagicMock()
    smtp_context = smtp.__enter__.return_value
    smtp_context.send_message.return_value = {}
    with (
        patch("app.services.email.smtplib.SMTP", return_value=smtp),
        patch("app.services.pdf.generate_invoice_pdf", return_value=b"%PDF-test"),
    ):
        send_invoice_email(session, invoice)

    smtp_context.starttls.assert_called_once()
    smtp_context.login.assert_called_once_with("mailer", "test-only")
    sent_message = smtp_context.send_message.call_args.args[0]
    assert sent_message["To"] == "customer@example.test"
    assert sent_message.get_payload()[1].get_filename() == "INV-TEST.pdf"
