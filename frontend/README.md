# Brightloop Subscriptions – Frontend

React + Vite + TypeScript + Tailwind v4 dashboard for the Brightloop Subscription Management System.

## Run it

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (backend must run on http://localhost:8000).

## Demo logins

| Role | Email | Password |
|---|---|---|
| Admin | admin@brightloop.com | Admin@1234 |
| Staff | staff@brightloop.com | Staff@1234 |
| Customer | customer@brightloop.com | Customer@1234 |

The **Quick demo** buttons on the login page log in with these.

## Pages

- **Auth:** login, signup (live password rules), forgot / reset password
- **Admin & staff:** Dashboard, Customers, Subscriptions (list + Kanban), Invoices, Payments
- **Admin only:** Products (variants), Plans, Quotation templates, Taxes (GST split), Discounts, Staff
- **Customer portal:** My subscriptions, My invoices (Pay now with Razorpay), Profile

## Highlights

- ⏰ **Time machine**: jump +1 day / week / month to watch billing run
- 📋 **Kanban board**: move subscriptions Draft → Quotation → Confirmed → Active in one click
- 🔍 **Ctrl+K** command palette to jump to any page, subscription, invoice or customer
- 📈 MRR / ARR, revenue chart, **MRR forecast**, **customers at risk**
- 🧾 Live **GST split preview** (CGST + SGST in Kerala, IGST elsewhere)
- ⚡ "Loaded in X ms" speed badge, 🌙 dark mode, print-ready invoices
- 💰 All money handled as integer **paise**, so there are no rounding errors