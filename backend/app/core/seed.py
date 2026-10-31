"""
seed.py — Comprehensive demo seed data pipeline for Brightloop Subscription Management System.

Seeds:
  1. Accounts: 1 Admin, 3 Staff members, 500 Customers across Indian states.
  2. Products & Plans: 10 Products with variants, 6 Subscription Plans.
  3. Subscriptions: Exactly 5,000 subscriptions across all 6 supported statuses.
  4. Invoices & Payments: 1,500 Invoices (Paid with linked Payments, Overdue, Confirmed, Draft).
"""

from datetime import date, timedelta, datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionLine
from app.models.invoice import Invoice, InvoiceLine
from app.models.payment import Payment
from app.models.tax import Tax
from app.core.security import get_password_hash
from app.services import clock

# ==============================================================================
# 1. Accounts Configuration
# ==============================================================================

DEV_SEED_ACCOUNTS: List[Dict[str, str]] = [
    {
        "name": "System Administrator",
        "email": "admin@brightloop.com",
        "password": "Admin@1234",
        "role": "admin",
        "phone": "+91 9847000001",
        "state": "Kerala",
    },
    {
        "name": "Brightloop Staff",
        "email": "staff@brightloop.com",
        "password": "Staff@1234",
        "role": "staff",
        "phone": "+91 9847000002",
        "state": "Kerala",
    },
    {
        "name": "Kavya Nair",
        "email": "kavya.nair@brightloop.com",
        "password": "Staff@1234",
        "role": "staff",
        "phone": "+91 9847000003",
        "state": "Kerala",
    },
    {
        "name": "Rahul Sharma",
        "email": "rahul.sharma@brightloop.com",
        "password": "Staff@1234",
        "role": "staff",
        "phone": "+91 9847000004",
        "state": "Delhi",
    },
    {
        "name": "Brightloop Customer",
        "email": "customer@brightloop.com",
        "password": "Customer@1234",
        "role": "customer",
        "phone": "+91 9847000005",
        "state": "Kerala",
    },
]

INDIAN_COMPANY_PREFIXES = [
    "Tata", "Infosys", "Wipro", "Reliance", "HDFC", "Swiggy", "Zerodha", "Zoho",
    "Freshworks", "Malabar", "Kerala Spice", "Kochi Marine", "Bangalore Software",
    "Chennai Auto", "Hyderabad Pharma", "Pune Precision", "Delhi Analytics",
    "Gurgaon Cloud", "Noida AI", "Mumbai FinTech", "Ahmedabad Textiles",
    "Kolkata Agro", "Jaipur Crafts", "Goa Digital", "Bhopal IT", "Trivandrum Space",
    "Calicut Logistics", "Coimbatore Foundry", "Madurai Mills", "Mysore Silks",
    "Mangalore Marine", "Hubli Motors", "Thane Polymers", "Nashik Vintners",
    "Nagpur Freight", "Surat Diamonds", "Vadodara Power", "Rajkot Forgings",
    "Indore Confectionery", "Gwalior Potteries", "Ludhiana Woolens", "Amritsar Exports",
    "Chandigarh Biotech", "Lucknow Chikan", "Kanpur Leather", "Varanasi Weavers",
    "Patna Infotech", "Ranchi Minerals", "Bhubaneswar Metals", "Cuttack Silver"
]

INDIAN_COMPANY_SUFFIXES = [
    "Technologies", "Solutions", "Enterprises", "Private Limited", "Ventures",
    "Labs", "Systems", "Networks", "Industries", "Logistics", "Services",
    "Global", "Digital", "Hub", "Works", "Innovations", "Consulting", "Cloud"
]

INDIAN_STATES = [
    "Kerala", "Tamil Nadu", "Karnataka", "Maharashtra", "Telangana", "Delhi",
    "Gujarat", "Uttar Pradesh", "West Bengal", "Andhra Pradesh", "Rajasthan",
    "Punjab", "Goa", "Madhya Pradesh", "Haryana", "Bihar", "Odisha", "Assam"
]


def seed_accounts(db: Session) -> Dict[str, User]:
    """
    Idempotently seeds:
      - 1 Admin (admin@brightloop.com)
      - 3 Staff members
      - 500 Customers across Indian states
    """
    existing_emails = {u[0] for u in db.query(User.email).all()}
    results: Dict[str, User] = {}

    # 1. Dev accounts
    for acc in DEV_SEED_ACCOUNTS:
        email_clean = acc["email"].strip().lower()
        if email_clean not in existing_emails:
            user = User(
                name=acc["name"],
                email=email_clean,
                password_hash=get_password_hash(acc["password"]),
                role=acc["role"],
                phone=acc.get("phone"),
                state=acc.get("state"),
            )
            db.add(user)
            existing_emails.add(email_clean)
            results[acc["role"]] = user
        else:
            existing = db.query(User).filter(User.email == email_clean).first()
            if existing:
                results[acc["role"]] = existing
    db.commit()

    # 2. 500 Customers
    current_customer_count = db.query(User).filter(User.role == "customer").count()
    needed = 500 - current_customer_count
    if needed > 0:
        cust_hash = get_password_hash("Customer@1234")
        new_customers = []
        for i in range(1, needed + 1):
            prefix = INDIAN_COMPANY_PREFIXES[(i - 1) % len(INDIAN_COMPANY_PREFIXES)]
            suffix = INDIAN_COMPANY_SUFFIXES[(i // len(INDIAN_COMPANY_PREFIXES)) % len(INDIAN_COMPANY_SUFFIXES)]
            company_name = f"{prefix} {suffix}"
            email = f"customer{i:03d}@{prefix.lower().replace(' ', '')}.in"
            if email in existing_emails:
                email = f"cust{i:03d}_{prefix.lower().replace(' ', '')}@brightloop.com"
            existing_emails.add(email)
            state = INDIAN_STATES[(i - 1) % len(INDIAN_STATES)]
            phone = f"+91 {9800000000 + i}"
            new_customers.append(User(
                name=company_name,
                email=email,
                password_hash=cust_hash,
                role="customer",
                phone=phone,
                state=state,
            ))
        db.add_all(new_customers)
        db.commit()

    return results


def seed_dev_accounts(db: Optional[Session] = None) -> Dict[str, User]:
    """
    Backwards-compatible account seeder.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        return seed_accounts(db)
    finally:
        if should_close:
            db.close()


def seed_admin(db: Optional[Session] = None) -> User:
    """
    Seeds accounts and returns the admin User.
    """
    accounts = seed_dev_accounts(db=db)
    return accounts["admin"]


# ==============================================================================
# 2. Products and Plans Configuration
# ==============================================================================

PRODUCTS_DATA = [
    {
        "name": "Cloud Compute Engine",
        "type": "cloud_service",
        "notes": "High-performance virtual machines with dedicated vCPU and RAM.",
        "sales_price": 150000,
        "cost_price": 80000,
        "variants": [
            ("Instance Type", "General Purpose (2 vCPU / 8GB)", 0),
            ("Instance Type", "Compute Optimized (4 vCPU / 16GB)", 100000),
            ("Instance Type", "Memory Optimized (8 vCPU / 32GB)", 250000),
        ]
    },
    {
        "name": "Managed Postgres Cluster",
        "type": "database_service",
        "notes": "Fully managed PostgreSQL with automated daily backups and high availability.",
        "sales_price": 200000,
        "cost_price": 110000,
        "variants": [
            ("Storage Tier", "20GB SSD Storage", 0),
            ("Storage Tier", "100GB NVMe Storage", 150000),
            ("Storage Tier", "500GB HA Multi-Region", 400000),
        ]
    },
    {
        "name": "Enterprise Email Suite",
        "type": "saas_software",
        "notes": "Custom domain corporate email with spam defense and webmail interface.",
        "sales_price": 50000,
        "cost_price": 20000,
        "variants": [
            ("Mailbox Quota", "10 Inboxes (15GB each)", 0),
            ("Mailbox Quota", "50 Inboxes (50GB each)", 120000),
            ("Mailbox Quota", "Unlimited Corporate Seats", 300000),
        ]
    },
    {
        "name": "API Gateway & Rate Limiter",
        "type": "cloud_service",
        "notes": "Low-latency API proxy with JWT authentication and traffic throttling.",
        "sales_price": 80000,
        "cost_price": 35000,
        "variants": [
            ("Monthly Traffic", "1 Million API Calls", 0),
            ("Monthly Traffic", "10 Million API Calls", 80000),
            ("Monthly Traffic", "50 Million API Calls", 250000),
        ]
    },
    {
        "name": "Object Storage Vault",
        "type": "storage_service",
        "notes": "S3-compatible scalable object storage with 99.999999999% durability.",
        "sales_price": 40000,
        "cost_price": 18000,
        "variants": [
            ("Storage Class", "1 TB Standard Hot Storage", 0),
            ("Storage Class", "5 TB Infrequent Archive", 90000),
            ("Storage Class", "20 TB Deep Glacier Coldline", 250000),
        ]
    },
    {
        "name": "Real-time Analytics Engine",
        "type": "analytics_software",
        "notes": "Event ingestion and streaming business intelligence analytics.",
        "sales_price": 350000,
        "cost_price": 180000,
        "variants": [
            ("Analytics Tier", "Basic Event Stream", 0),
            ("Analytics Tier", "Team BI Dashboard", 150000),
            ("Analytics Tier", "Executive C-Level Suite", 350000),
        ]
    },
    {
        "name": "AI Copilot & Code Assistant",
        "type": "ai_service",
        "notes": "Fine-tuned enterprise AI coding assistant with private repo isolation.",
        "sales_price": 120000,
        "cost_price": 60000,
        "variants": [
            ("Team Seats", "5 Developer License", 0),
            ("Team Seats", "25 Developer License", 300000),
            ("Team Seats", "100 Developer License", 800000),
        ]
    },
    {
        "name": "NextGen Web Application Firewall",
        "type": "security_service",
        "notes": "Automated DDoS protection, bot filtering, and OWASP top-10 mitigation.",
        "sales_price": 180000,
        "cost_price": 90000,
        "variants": [
            ("Security Level", "Standard Edge WAF", 0),
            ("Security Level", "Advanced DDoS Mitigation Pro", 120000),
            ("Security Level", "Zero-Trust Military Shield", 280000),
        ]
    },
    {
        "name": "Edge CDN Accelerator",
        "type": "network_service",
        "notes": "Global points of presence with smart edge caching and TLS termination.",
        "sales_price": 90000,
        "cost_price": 40000,
        "variants": [
            ("Data Transfer", "5 TB Domestic CDN", 0),
            ("Data Transfer", "25 TB Pan-Asian Edge", 150000),
            ("Data Transfer", "100 TB Global Enterprise CDN", 450000),
        ]
    },
    {
        "name": "Automated Compliance & Audit Logger",
        "type": "compliance_software",
        "notes": "Tamper-evident log forwarding for SOC-2, ISO-27001, and HIPAA compliance.",
        "sales_price": 250000,
        "cost_price": 120000,
        "variants": [
            ("Certification", "SOC-2 Type II Automated", 0),
            ("Certification", "ISO-27001 & GDPR Pack", 150000),
            ("Certification", "Banking & Financial Grade Shield", 350000),
        ]
    },
]

PLANS_DATA = [
    {
        "name": "Starter Monthly",
        "price": 99900,
        "billing_period": "monthly",
        "min_qty": 1,
        "start_date": date(2026, 1, 1),
        "end_date": None,
        "auto_close": False,
        "closable": True,
        "pausable": True,
        "renewable": True,
    },
    {
        "name": "Growth Monthly",
        "price": 249900,
        "billing_period": "monthly",
        "min_qty": 1,
        "start_date": date(2026, 1, 1),
        "end_date": None,
        "auto_close": False,
        "closable": True,
        "pausable": True,
        "renewable": True,
    },
    {
        "name": "Enterprise Monthly",
        "price": 799900,
        "billing_period": "monthly",
        "min_qty": 2,
        "start_date": date(2026, 1, 1),
        "end_date": None,
        "auto_close": False,
        "closable": True,
        "pausable": True,
        "renewable": True,
    },
    {
        "name": "Professional Annual",
        "price": 2499900,
        "billing_period": "yearly",
        "min_qty": 1,
        "start_date": date(2026, 1, 1),
        "end_date": None,
        "auto_close": False,
        "closable": True,
        "pausable": True,
        "renewable": True,
    },
    {
        "name": "Enterprise Annual High-Volume",
        "price": 7999900,
        "billing_period": "yearly",
        "min_qty": 2,
        "start_date": date(2026, 1, 1),
        "end_date": None,
        "auto_close": False,
        "closable": True,
        "pausable": True,
        "renewable": True,
    },
    {
        "name": "Weekly Sprint Trial",
        "price": 19900,
        "billing_period": "weekly",
        "min_qty": 1,
        "start_date": date(2026, 1, 1),
        "end_date": None,
        "auto_close": False,
        "closable": True,
        "pausable": True,
        "renewable": True,
    },
]


def seed_products_and_plans(db: Session) -> None:
    """
    Idempotently seeds 10 products with variants and 6 plans.
    """
    # 1. Products & Variants
    if db.query(Product).count() < len(PRODUCTS_DATA):
        for pdata in PRODUCTS_DATA:
            existing = db.query(Product).filter(Product.name == pdata["name"]).first()
            if not existing:
                p = Product(
                    name=pdata["name"],
                    type=pdata["type"],
                    sales_price=pdata["sales_price"],
                    cost_price=pdata["cost_price"],
                    notes=pdata["notes"],
                )
                db.add(p)
                db.flush()
                for attr_name, attr_val, p_extra in pdata["variants"]:
                    pv = ProductVariant(
                        product_id=p.id,
                        attribute=attr_name,
                        value=attr_val,
                        extra_price=p_extra,
                    )
                    db.add(pv)
        db.commit()

    # 2. Plans
    if db.query(Plan).count() < len(PLANS_DATA):
        for pldata in PLANS_DATA:
            existing = db.query(Plan).filter(Plan.name == pldata["name"]).first()
            if not existing:
                plan = Plan(
                    name=pldata["name"],
                    price=pldata["price"],
                    billing_period=pldata["billing_period"],
                    min_qty=pldata["min_qty"],
                    start_date=pldata["start_date"],
                    end_date=pldata["end_date"],
                    auto_close=pldata["auto_close"],
                    closable=pldata["closable"],
                    pausable=pldata["pausable"],
                    renewable=pldata["renewable"],
                    is_active=True,
                )
                db.add(plan)
        db.commit()


# ==============================================================================
# 3. Subscriptions Seeding (5,000 across 6 supported statuses)
# ==============================================================================

STATUS_DISTRIBUTION = [
    ("active", 2500),
    ("paused", 500),
    ("closed", 600),
    ("confirmed", 500),
    ("quotation", 500),
    ("draft", 400),
]


def seed_subscriptions(db: Session) -> None:
    """
    Idempotently seeds exactly 5,000 subscriptions across 6 supported statuses.
    """
    if db.query(Subscription).count() >= 5000:
        return

    customers = db.query(User.id).filter(User.role == "customer").order_by(User.id).all()
    cust_ids = [c[0] for c in customers]
    if not cust_ids:
        return

    plans = db.query(Plan).order_by(Plan.id).all()
    products = db.query(Product).order_by(Product.id).all()
    variants = db.query(ProductVariant).order_by(ProductVariant.id).all()
    prod_var_map = {}
    for v in variants:
        prod_var_map.setdefault(v.product_id, []).append(v)

    default_tax = db.query(Tax).filter(Tax.name == "GST 18%").first() or db.query(Tax).first()
    tax_id = default_tax.id if default_tax else None

    effective_today = clock.today(db=db)

    target_statuses = []
    for st, count in STATUS_DISTRIBUTION:
        target_statuses.extend([st] * count)

    sub_number_idx = 1
    for i, status in enumerate(target_statuses):
        cust_id = cust_ids[i % len(cust_ids)]
        plan = plans[i % len(plans)]
        prod = products[i % len(products)]
        avail_vars = prod_var_map.get(prod.id, [])
        var = avail_vars[i % len(avail_vars)] if avail_vars else None

        unit_price = prod.sales_price + (var.extra_price if var else 0)
        qty = plan.min_qty
        tax_amount = int(round(unit_price * qty * 0.18))
        total_amount = unit_price * qty

        start_date = effective_today - timedelta(days=((i % 180) + 30))
        if status in {"draft", "quotation"}:
            start_date = effective_today - timedelta(days=(i % 10))
            next_billing = start_date + timedelta(days=30)
            expiry_date = None
        elif status == "closed":
            expiry_date = effective_today - timedelta(days=((i % 30) + 1))
            next_billing = None
        elif status == "paused":
            expiry_date = None
            next_billing = effective_today + timedelta(days=((i % 30) + 1))
        else:  # active, confirmed
            expiry_date = None
            next_billing = effective_today + timedelta(days=((i % 30) + 1))

        sub_num = f"SUB-{sub_number_idx:05d}"
        sub_number_idx += 1

        json_line = [{
            "product_id": prod.id,
            "product_name": prod.name,
            "variant_id": var.id if var else None,
            "tax_id": tax_id,
            "quantity": qty,
            "unit_price": unit_price,
            "tax_amount": tax_amount,
            "amount": total_amount,
        }]

        json_history = [{
            "at": datetime.now(timezone.utc).isoformat(),
            "from_status": "draft" if status != "draft" else None,
            "to_status": status,
            "note": f"Initial seed status set to {status}",
        }]

        sub = Subscription(
            number=sub_num,
            customer_id=cust_id,
            plan_id=plan.id,
            status=status,
            start_date=start_date,
            expiry_date=expiry_date,
            next_billing_date=next_billing,
            payment_terms="immediate",
            payment_terms_days=0,
            is_paused=(status == "paused"),
            lines=json_line,
            history=json_history,
            subtotal=total_amount,
            total=total_amount,
        )
        db.add(sub)
        db.flush()

        sub_line = SubscriptionLine(
            subscription_id=sub.id,
            product_id=prod.id,
            variant_id=var.id if var else None,
            tax_id=tax_id,
            product_name=prod.name,
            quantity=qty,
            unit_price=unit_price,
            tax_amount=tax_amount,
            amount=total_amount,
        )
        db.add(sub_line)

        if i > 0 and i % 500 == 0:
            db.commit()

    db.commit()


# ==============================================================================
# 4. Invoices and Payments Seeding
# ==============================================================================

def seed_invoices_and_payments(db: Session) -> None:
    """
    Idempotently seeds 1,500 invoices across:
      - 800 Paid invoices with corresponding Payment records
      - 350 Overdue invoices (status='confirmed', due_date < today, amount_due > 0)
      - 250 Confirmed / Active invoices (due_date in future)
      - 100 Draft invoices
    """
    if db.query(Invoice).count() >= 1500:
        return

    effective_today = clock.today(db=db)
    subs = db.query(Subscription).order_by(Subscription.id).limit(1500).all()
    if not subs:
        return

    default_tax = db.query(Tax).filter(Tax.name == "GST 18%").first() or db.query(Tax).first()
    tax_id = default_tax.id if default_tax else None

    categories = (
        ["paid"] * 800 +
        ["overdue"] * 350 +
        ["confirmed"] * 250 +
        ["draft"] * 100
    )

    inv_num_idx = 1
    for i, sub in enumerate(subs):
        cat = categories[i]
        line = sub.lines[0]
        subtotal = line["amount"]
        tax_amount = int(round(subtotal * 0.18))
        total = subtotal + tax_amount

        period_start = sub.start_date
        period_end = period_start + timedelta(days=30)
        inv_num = f"INV-2026-{inv_num_idx:05d}"
        inv_num_idx += 1

        inv_line_dict = [{
            "description": f"{line['product_name']} Subscription Period",
            "product_id": line["product_id"],
            "quantity": line["quantity"],
            "unit_price": line["unit_price"],
            "tax_id": tax_id,
            "tax_amount": tax_amount,
            "discount_amount": 0,
            "amount": total,
        }]

        if cat == "paid":
            inv_status = "paid"
            inv_date = effective_today - timedelta(days=45)
            due_date = inv_date + timedelta(days=15)
            amount_paid = total
            amount_due = 0
        elif cat == "overdue":
            inv_status = "confirmed"
            inv_date = effective_today - timedelta(days=30)
            due_date = effective_today - timedelta(days=10)
            amount_paid = 0
            amount_due = total
        elif cat == "confirmed":
            inv_status = "confirmed"
            inv_date = effective_today - timedelta(days=5)
            due_date = effective_today + timedelta(days=15)
            amount_paid = 0
            amount_due = total
        else:  # draft
            inv_status = "draft"
            inv_date = effective_today
            due_date = effective_today + timedelta(days=15)
            amount_paid = 0
            amount_due = total

        invoice = Invoice(
            number=inv_num,
            customer_id=sub.customer_id,
            subscription_id=sub.id,
            status=inv_status,
            invoice_date=inv_date,
            due_date=due_date,
            period_start=period_start,
            period_end=period_end,
            lines=inv_line_dict,
            subtotal=subtotal,
            discount_total=0,
            discount_subtotal=subtotal,
            tax_total=tax_amount,
            total=total,
            amount_paid=amount_paid,
            amount_due=amount_due,
        )
        db.add(invoice)
        db.flush()

        inv_line = InvoiceLine(
            invoice_id=invoice.id,
            product_id=line["product_id"],
            tax_id=tax_id,
            description=f"{line['product_name']} Subscription Period",
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            tax_amount=tax_amount,
            discount_amount=0,
            amount=total,
        )
        db.add(inv_line)

        if cat == "paid":
            payment = Payment(
                invoice_id=invoice.id,
                amount=total,
                method="upi" if i % 2 == 0 else "bank_transfer",
                payment_date=due_date - timedelta(days=2),
                note=f"Automated settlement for {invoice.number}",
            )
            db.add(payment)

        if i > 0 and i % 500 == 0:
            db.commit()

    db.commit()


# ==============================================================================
# 5. Master Pipeline Seeder
# ==============================================================================

def seed_all_demo_data(db: Optional[Session] = None) -> None:
    """
    Idempotent master seeder for the complete Brightloop demo dataset.
    Populates:
      - 1 Admin, 3 Staff, 500 Customers
      - 10 Products with variants, 6 Plans
      - 5,000 Subscriptions across 6 supported statuses
      - 1,500 Invoices (Paid, Overdue, Confirmed, Draft) & 800 Payments
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        seed_accounts(db)
        seed_products_and_plans(db)
        seed_subscriptions(db)
        seed_invoices_and_payments(db)
    finally:
        if should_close:
            db.close()


# Aliases
seed_initial_data = seed_dev_accounts
seed_users = seed_dev_accounts

__all__ = [
    "seed_dev_accounts",
    "seed_admin",
    "seed_accounts",
    "seed_products_and_plans",
    "seed_subscriptions",
    "seed_invoices_and_payments",
    "seed_all_demo_data",
    "seed_initial_data",
    "seed_users",
    "DEV_SEED_ACCOUNTS",
]
