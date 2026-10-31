# Brightloop Subscription Management System

A modular FastAPI backend service managing taxes, discounts, payments, financial reports, invoice generation, and notifications for the Subscription Management System.

Brightloop provides subscription billing, tax and discount management, invoice payments, reporting, PDF documents, and invoice email delivery.

---

## 🛠️ Technology Stack
- **Python 3.10+** (developed & tested with Python 3.14)
- **FastAPI**: Modern, high-performance web framework for APIs.
- **SQLAlchemy 2.0**: SQL toolkit and Object-Relational Mapper.
- **SQLite**: Zero-configuration, file-based relational database.
- **Pydantic v2**: High-speed data validation and settings management.
- **Uvicorn**: Lightning-fast ASGI web server implementation.
- **ReportLab**: Invoice and analytics PDF generation.
- **smtplib**: Python standard-library SMTP client; no separate email package is needed.
- **React, TypeScript, Vite, Tailwind CSS**: Frontend application and styling.

---

## 💰 Core Monetary & Tax Principles

### 1. Integer Paise Rule
All monetary values across the application are stored and calculated strictly as **integer paise** (₹1 = 100 paise).
* For example:
  * ₹1.00 = `100` paise
  * ₹50.00 = `5000` paise
  * ₹100.00 = `10000` paise
  * ₹1,499.00 = `149900` paise
* **Why?** Floating-point representations (like Python `float`) suffer from binary rounding errors (e.g., `0.1 + 0.2 != 0.3`). Integer arithmetic guarantees 100% financial accuracy with zero precision loss.

### 2. Exact Decimal Rates & Documented Rounding
* Tax rates are stored and processed using Python's `Decimal` type (e.g., `Decimal("18.00")` for 18%).
* Fractional paise are rounded using the standard **`ROUND_HALF_UP`** commercial rounding rule (i.e. half a paise or more rounds up to the next integer paise: 0.50 paise rounds up to 1 paise).

### 3. Indian GST Engine (Intra-State vs Inter-State)
The tax calculation service automatically handles Indian Goods & Services Tax (GST) rules:
* **Intra-State (Same State):** When the customer's state matches the company's operating state, GST is split equally into:
  * **CGST** (Central GST) = Rate ÷ 2
  * **SGST** (State GST) = Rate ÷ 2
  * *Example:* For an 18% GST rate on ₹100 (`10000` paise) intra-state:
    * CGST (9%) = `900` paise (₹9.00)
    * SGST (9%) = `900` paise (₹9.00)
    * Total Tax = `1800` paise (₹18.00)
* **Inter-State (Different State):** When customer's state is outside the company's state, **IGST** (Integrated GST) applies at the full rate:
  * *Example:* 18% IGST on ₹100 (`10000` paise) = `1800` paise (₹18.00).
* **Configurable Location:** The company state is configurable via the `COMPANY_STATE` environment variable (defaults to `"Kerala"`).

### 4. Audit Trail & Soft Deletion
* Deleting a tax rule (`DELETE /taxes/{tax_id}`) performs a **soft deactivation** (`is_active = False`).
* This ensures existing invoices, receipts, and historical financial records remain valid and audit-compliant.

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── database.py           # SQLite connection and session dependency
│   ├── main.py               # FastAPI app and router registration
│   ├── models/               # User, plan, subscription, invoice, payment, tax, discount
│   ├── schemas/              # API input/output validation
│   ├── routers/              # REST API endpoints
│   └── services/             # Billing, GST, analytics, PDF, and SMTP logic
├── tests/                    # Tax, discounts, payments, reporting, PDF, email tests
├── .env.example              # Safe environment-variable template
└── requirements.txt          # Backend dependencies
frontend/
├── src/api/                  # Shared Axios API client
├── src/pages/                # React pages, including Taxes, Discounts, Reports
└── package.json              # Vite, TypeScript, React, Tailwind dependencies
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.10 or higher.
- Node.js and npm for the React frontend.

### 2. Clone and Open Project
```bash
cd odoo-hackathon
```

### 3. Create and Activate a Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Backend Dependencies
```bash
pip install -r backend/requirements.txt
```

### 5. Install Frontend Dependencies
```bash
cd frontend
npm ci
cd ..
```

---

## ⚙️ Configuration (Environment Variables)

Copy [`backend/.env.example`](backend/.env.example) to `backend/.env` and set values as needed. Environment variables already set by the shell take precedence.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | Repository-root `brightloop.db` | SQLAlchemy connection string |
| `COMPANY_STATE` | `Kerala` | State where the company is registered for GST |
| `SMTP_HOST` | — | SMTP server hostname (required to send invoice email) |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USERNAME` | — | SMTP account username |
| `SMTP_PASSWORD` | — | SMTP account password; keep it in the local environment, never source code |
| `SMTP_FROM_EMAIL` | — | Sender address displayed on invoice emails |
| `SMTP_USE_TLS` | `true` | Start TLS for SMTP connections |
| `SMTP_USE_SSL` | `false` | Use implicit TLS (mutually exclusive with STARTTLS) |
| `RAZORPAY_KEY_ID` | — | Razorpay test-mode public key ID (`rzp_test_*`) |
| `RAZORPAY_KEY_SECRET` | — | Razorpay test-mode secret; server-side only, never sent to the frontend |

Email configuration is optional until an invoice email is sent. If settings are missing, the send endpoint reports which environment variables must be configured.
Razorpay test credentials are required for portal checkout. Checkout is intentionally restricted to test-mode key IDs. `.env` files are ignored by Git; do not commit real SMTP or Razorpay credentials. The frontend receives only `key_id`; `RAZORPAY_KEY_SECRET` stays on the backend.

---

## 🏃 Running the Application

From the `backend/` directory, start the Uvicorn development server:

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once started:
- **Interactive Swagger UI Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Alternative Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🧪 Testing the Application

Run backend tests against an isolated in-memory SQLite database so test cleanup cannot affect the configured application database:

**Windows PowerShell**
```powershell
$env:DATABASE_URL = "sqlite:///:memory:"
python -m pytest backend/tests -q
```

**macOS/Linux**
```bash
DATABASE_URL=sqlite:///:memory: python -m pytest backend/tests -q
```

Build and type-check the frontend:
```bash
cd frontend
npm run build
```

---

## 📡 Implemented API Endpoints

All routes below are prefixed with `/api`. Interactive API documentation is available at `/docs`.

| Area | Endpoints |
| :--- | :--- |
| Taxes | `GET/POST /taxes`, `GET/PUT/DELETE /taxes/{id}`, `POST /taxes/calculate` |
| Discounts | `GET/POST /discounts`, `GET/PUT/DELETE /discounts/{id}`, `POST /discounts/validate` |
| Subscriptions | `GET/POST /subscriptions`, `GET /subscriptions/{id}`, `POST /subscriptions/{id}/{action}` (workflow actions) |
| Invoices | `GET/POST /invoices`, `GET /invoices/{id}`, `POST /invoices/{id}/confirm`, `POST /invoices/{id}/cancel`, `POST /invoices/{id}/send`, `GET /invoices/{id}/pdf` |
| Payments | `GET /payments?invoice_id={id}`, `POST /payments`, `POST /payments/razorpay/order`, `POST /payments/razorpay/verify` |
| Reports | `GET /reports/summary`, `/mrr`, `/arr`, `/revenue`, `/outstanding`, `/overdue`, `/monthly-revenue`, `GET /reports/pdf` |

Monetary API values are integer paise. `POST /payments` accepts `invoice_id`, `method` (`upi`, `bank_transfer`, `card`, `cash`, or `razorpay`), positive integer `amount`, `payment_date`, and optional `note`. Responses contain the payment `id`, `invoice_id`, `method`, `amount`, `payment_date`, and `note`. Invoice payment status remains `confirmed` while a balance is outstanding and changes to `paid` when fully settled. Discounts are validated when applied, but their usage count is consumed only when the related invoice or subscription is confirmed.

The Razorpay order endpoint creates a test-mode order for the invoice's current outstanding balance. The verification endpoint checks the Checkout signature and confirms the captured payment against Razorpay before creating the payment record. The signing secret remains on the backend. Subscription line items can refer to an active tax through `tax_id`, backed by a foreign key to `taxes.id`.

Razorpay Checkout API sequence:
```json
POST /api/payments/razorpay/order
{"invoice_id": 5}
```
The response contains the provider's `order_id`, the outstanding `amount` in paise, `currency: "INR"`, and the public test `key_id`. After Checkout, submit `invoice_id`, `razorpay_order_id`, `razorpay_payment_id`, and `razorpay_signature` to `POST /api/payments/razorpay/verify`. The server validates the signature and the captured provider payment before settling the invoice.

Activating a confirmed subscription creates a confirmed invoice for its initial billing period, using the subscription's payment terms for the due date. Renewing a subscription creates a new billing-period invoice; the subscription discount is not consumed a second time on that invoice.

Start the frontend development server in a separate terminal:
```bash
cd frontend
npm run dev
```

---

## 📖 API Testing Guide (Swagger UI & cURL)

Open **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** in your browser to interactively test all endpoints.

### 1. Health Check
```bash
curl -X GET "http://127.0.0.1:8000/health"
```
**Response:**
```json
{
  "status": "ok"
}
```

### 2. List All Tax Rules (Includes Seeded Default GST Rates)
On initial startup, default taxes (**GST 5%** and **GST 18%**) are automatically seeded without duplicates.
```bash
curl -X GET "http://127.0.0.1:8000/api/taxes"
```
**Response:**
```json
[
  {
    "id": 1,
    "name": "GST 5%",
    "rate": "5.00",
    "tax_type": "gst",
    "description": "Standard Indian GST rate of 5% (Intra-state: 2.5% CGST + 2.5% SGST, Inter-state: 5% IGST)",
    "is_active": true,
    "created_at": "2026-10-31T09:30:00Z",
    "updated_at": "2026-10-31T09:30:00Z"
  },
  {
    "id": 2,
    "name": "GST 18%",
    "rate": "18.00",
    "tax_type": "gst",
    "description": "Standard Indian GST rate of 18% (Intra-state: 9% CGST + 9% SGST, Inter-state: 18% IGST)",
    "is_active": true,
    "created_at": "2026-10-31T09:30:00Z",
    "updated_at": "2026-10-31T09:30:00Z"
  }
]
```

### 3. Create a Custom Tax Rule
```bash
curl -X POST "http://127.0.0.1:8000/api/taxes" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GST 12%",
    "rate": 12.00,
    "tax_type": "gst",
    "description": "Concessional GST rate for specialized software services",
    "is_active": true
  }'
```

### 4. Calculate Tax & Indian GST Breakdown

#### A. Intra-State Example (Kerala customer, Kerala company)
Subtotal: ₹1,000.00 (`100000` paise), Tax Rate: `18.00`%:
```bash
curl -X POST "http://127.0.0.1:8000/api/taxes/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "subtotal_paise": 100000,
    "tax_rate": 18.00,
    "customer_state": "Kerala"
  }'
```
**Response (Split into 9% CGST + 9% SGST):**
```json
{
  "subtotal_paise": 100000,
  "effective_tax_rate": "18.00",
  "tax_amount_paise": 18000,
  "total_paise": 118000,
  "rounding_rule": "ROUND_HALF_UP to nearest 1 paise (0.50 paise rounds up)",
  "gst_breakdown": {
    "is_intra_state": true,
    "company_state": "Kerala",
    "customer_state": "Kerala",
    "cgst_rate": "9.00",
    "cgst_amount_paise": 9000,
    "sgst_rate": "9.00",
    "sgst_amount_paise": 9000,
    "igst_rate": "0.0",
    "igst_amount_paise": 0
  }
}
```

#### B. Inter-State Example (Maharashtra customer, Kerala company)
Subtotal: ₹1,000.00 (`100000` paise), Tax Rate: `18.00`%:
```bash
curl -X POST "http://127.0.0.1:8000/api/taxes/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "subtotal_paise": 100000,
    "tax_rate": 18.00,
    "customer_state": "Maharashtra"
  }'
```
**Response (18% IGST applied):**
```json
{
  "subtotal_paise": 100000,
  "effective_tax_rate": "18.00",
  "tax_amount_paise": 18000,
  "total_paise": 118000,
  "rounding_rule": "ROUND_HALF_UP to nearest 1 paise (0.50 paise rounds up)",
  "gst_breakdown": {
    "is_intra_state": false,
    "company_state": "Kerala",
    "customer_state": "Maharashtra",
    "cgst_rate": "0.0",
    "cgst_amount_paise": 0,
    "sgst_rate": "0.0",
    "sgst_amount_paise": 0,
    "igst_rate": "18.00",
    "igst_amount_paise": 18000
  }
}
```

### 5. Deactivate a Tax Rule (Soft Delete)
```bash
curl -X DELETE "http://127.0.0.1:8000/api/taxes/1"
```
**Response:**
Returns the updated tax record with `"is_active": false`.

---

## 🤝 Teammate Integration Notes
When other teammates build the core modules:
1. **Subscriptions & Plans:** Can store `tax_id` (foreign key to `taxes.id`) or inherit default active GST rates.
2. **Invoices & Invoice Lines:**
   * Each line item subtotal can be evaluated in integer paise.
   * Total invoice tax is computed by calling `tax_service.calculate_gst(subtotal_paise, tax_rate, customer_state)`.
   * CGST, SGST, and IGST components are mapped directly to invoice columns or line summaries.
3. **Database Sharing:** Teammate models (`User`, `Subscription`, `Invoice`) can simply import `Base` from `app.database` and add their models to `app.models`.
