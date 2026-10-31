# Subscription Management System - Money Management Backend

A modular FastAPI backend service managing taxes, discounts, payments, financial reports, invoice generation, and notifications for the Subscription Management System.

This stage establishes the **Backend Foundation** and **Tax Management & Indian GST Engine**.

---

## 🛠️ Technology Stack
- **Python 3.10+** (developed & tested with Python 3.14)
- **FastAPI**: Modern, high-performance web framework for APIs.
- **SQLAlchemy 2.0**: SQL toolkit and Object-Relational Mapper.
- **SQLite**: Zero-configuration, file-based relational database.
- **Pydantic v2**: High-speed data validation and settings management.
- **Uvicorn**: Lightning-fast ASGI web server implementation.

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
* **Configurable Location:** The company state is not hard-coded; it is configurable via the `COMPANY_STATE` environment variable (defaults to `"Karnataka"`).

### 4. Audit Trail & Soft Deletion
* Deleting a tax rule (`DELETE /taxes/{tax_id}`) performs a **soft deactivation** (`is_active = False`).
* This ensures existing invoices, receipts, and historical financial records remain valid and audit-compliant.

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py             # Environment configuration & defaults
│   ├── database.py           # SQLite connection, sessionmaker & get_db dependency
│   ├── main.py               # FastAPI app, lifespan setup, CORS & error handling
│   ├── models/
│   │   ├── __init__.py
│   │   └── tax.py            # SQLAlchemy Tax database model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── tax.py            # Pydantic validation schemas & request/response types
│   ├── routers/
│   │   ├── __init__.py
│   │   └── taxes.py          # RESTful endpoints for Tax CRUD & calculations
│   └── services/
│       ├── __init__.py
│       └── tax.py            # Business logic, Decimal math, GST split & seed logic
├── tests/
│   ├── __init__.py
│   └── test_tax.py           # Unit tests for calculations, GST rules, and seed data
├── .env.example              # Sample environment configuration file
└── requirements.txt          # Python dependencies
README.md                     # Documentation
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.10 or higher installed.

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

### 4. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

---

## ⚙️ Configuration (Environment Variables)

Create a `.env` file in the `backend/` directory or set environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./subscription_system.db` | SQLAlchemy connection string |
| `COMPANY_STATE` | `Karnataka` | State where the company is registered for GST |
| `APP_NAME` | `Subscription Management System - Money API` | Name of the FastAPI application |
| `DEBUG` | `true` | Toggle SQL query logs and debug mode |

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

### Running Unit Tests
To run the automated test suite verifying tax calculations and GST splits:
```bash
python -m unittest backend/tests/test_tax.py
```
*(Or with pytest: `pytest backend/tests/`)*

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
curl -X GET "http://127.0.0.1:8000/taxes/"
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
curl -X POST "http://127.0.0.1:8000/taxes/" \
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

#### A. Intra-State Example (Karnataka customer, Karnataka company)
Subtotal: ₹1,000.00 (`100000` paise), Tax Rate: `18.00`%:
```bash
curl -X POST "http://127.0.0.1:8000/taxes/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "subtotal_paise": 100000,
    "tax_rate": 18.00,
    "customer_state": "Karnataka"
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
    "company_state": "Karnataka",
    "customer_state": "Karnataka",
    "cgst_rate": "9.00",
    "cgst_amount_paise": 9000,
    "sgst_rate": "9.00",
    "sgst_amount_paise": 9000,
    "igst_rate": "0.0",
    "igst_amount_paise": 0
  }
}
```

#### B. Inter-State Example (Maharashtra customer, Karnataka company)
Subtotal: ₹1,000.00 (`100000` paise), Tax Rate: `18.00`%:
```bash
curl -X POST "http://127.0.0.1:8000/taxes/calculate" \
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
    "company_state": "Karnataka",
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
curl -X DELETE "http://127.0.0.1:8000/taxes/1"
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
