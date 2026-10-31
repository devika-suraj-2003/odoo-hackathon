import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { ArrowLeft, CircleCheck, CircleX, Send, Printer, Download, Wallet, LoaderCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { formatINR, toPaise, toRupees } from "../lib/money";

type Line = { description: string; quantity: number; unit_price: number; tax_amount?: number; amount: number };
type Invoice = {
  id: number;
  number: string;
  subscription_id?: number;
  customer?: { id: number; name: string; email?: string } | null;
  status: string;
  invoice_date?: string | null;
  due_date?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  lines?: Line[];
  subtotal?: number;
  discount_total?: number;
  tax_total?: number;
  total: number;
  amount_paid?: number;
  amount_due?: number;
};
type Payment = { id: number; method: string; amount: number; payment_date?: string; note?: string | null };

type Action = { key: string; label: string; icon: LucideIcon; style: string };

const METHODS = [
  { value: "upi", label: "UPI" },
  { value: "bank_transfer", label: "Bank transfer" },
  { value: "card", label: "Card" },
  { value: "cash", label: "Cash" },
];

const today = () => new Date().toISOString().slice(0, 10);

function formatDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export default function InvoiceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [inv, setInv] = useState<Invoice | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const [payOpen, setPayOpen] = useState(false);
  const [pay, setPay] = useState({ method: "upi", amount: "", date: today(), note: "" });
  const [paying, setPaying] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get(`/invoices/${id}`);
      setInv(data && data.id ? data : null);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load invoice"), { id: "inv-detail" });
    } finally {
      setLoading(false);
    }
    try {
      const { data } = await api.get("/payments", { params: { invoice_id: id } });
      setPayments(Array.isArray(data) ? data : []);
    } catch {
      setPayments([]);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  async function runAction(a: Action) {
    if (a.key === "cancel" && !confirm("Cancel this invoice?")) return;
    setBusy(a.key);
    try {
      const { data } = await api.post(`/invoices/${id}/${a.key}`);
      if (data && data.id) setInv(data);
      else await load();
      toast.success(a.key === "send" ? "Invoice sent to customer" : `${a.label} done`);
    } catch (err) {
      toast.error(errorMessage(err, `${a.label} failed`));
    } finally {
      setBusy(null);
    }
  }

  async function downloadPdf() {
    setBusy("pdf");
    try {
      const res = await api.get(`/invoices/${id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      window.open(url, "_blank");
    } catch {
      toast.error("PDF not available yet. Use Print instead.");
    } finally {
      setBusy(null);
    }
  }

  function openPayment() {
    setPay({ method: "upi", amount: toRupees(inv?.amount_due ?? inv?.total ?? 0), date: today(), note: "" });
    setPayOpen(true);
  }

  async function savePayment(e: FormEvent) {
    e.preventDefault();
    const amount = toPaise(pay.amount);
    if (amount <= 0) return toast.error("Enter an amount");
    setPaying(true);
    try {
      await api.post("/payments", {
        invoice_id: Number(id),
        method: pay.method,
        amount,
        payment_date: pay.date,
        note: pay.note.trim() || null,
      });
      toast.success("Payment recorded");
      setPayOpen(false);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not record payment"));
    } finally {
      setPaying(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-slate-200" />
        <div className="h-96 animate-pulse rounded-2xl bg-slate-100" />
      </div>
    );
  }

  if (!inv) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
        <p className="font-semibold text-slate-800">Invoice not found</p>
        <button onClick={() => navigate("/invoices")} className="mt-4 text-sm font-semibold text-indigo-600 hover:text-indigo-700">
          Back to invoices
        </button>
      </div>
    );
  }

  const status = inv.status?.toLowerCase() ?? "draft";
  const amountDue = inv.amount_due ?? inv.total;
  const overdue = status === "confirmed" && !!inv.due_date && inv.due_date < today() && amountDue > 0;

  const actions: Action[] = [];
  if (status === "draft") actions.push({ key: "confirm", label: "Confirm", icon: CircleCheck, style: "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm" });
  if (status === "confirmed") actions.push({ key: "send", label: "Send", icon: Send, style: "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50" });
  if (status === "draft" || status === "confirmed")
    actions.push({ key: "cancel", label: "Cancel", icon: CircleX, style: "bg-white text-red-600 ring-1 ring-red-200 hover:bg-red-50" });

  return (
    <div className="space-y-6">
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <Link to="/invoices" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-800">
          <ArrowLeft className="h-4 w-4" /> All invoices
        </Link>
        <div className="flex flex-wrap gap-2">
          {status === "confirmed" && amountDue > 0 && (
            <button onClick={openPayment} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700">
              <Wallet className="h-4 w-4" /> Record payment
            </button>
          )}
          {actions.map((a) => {
            const Icon = a.icon;
            return (
              <button
                key={a.key}
                onClick={() => runAction(a)}
                disabled={busy !== null}
                className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:opacity-60 ${a.style}`}
              >
                {busy === a.key ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                {a.label}
              </button>
            );
          })}
          <button onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 ring-1 ring-slate-300 transition hover:bg-slate-50">
            <Printer className="h-4 w-4" /> Print
          </button>
          <button onClick={downloadPdf} disabled={busy !== null} className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 ring-1 ring-slate-300 transition hover:bg-slate-50 disabled:opacity-60">
            {busy === "pdf" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />} PDF
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-linear-to-br from-indigo-500 to-violet-500 font-extrabold text-white">B</div>
              <div>
                <p className="font-bold text-slate-900">Brightloop Software</p>
                <p className="text-xs text-slate-500">Thiruvananthapuram, Kerala</p>
              </div>
            </div>
            <p className="mt-6 text-xs font-semibold uppercase tracking-wide text-slate-400">Billed to</p>
            <p className="mt-1 font-semibold text-slate-900">{inv.customer?.name ?? "—"}</p>
            {inv.customer?.email && <p className="text-sm text-slate-500">{inv.customer.email}</p>}
          </div>
          <div className="text-right">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Invoice</p>
            <p className="text-2xl font-bold text-slate-900">{inv.number}</p>
            <div className="mt-2 flex justify-end">
              <StatusBadge status={overdue ? "overdue" : status} />
            </div>
            <dl className="mt-4 space-y-1 text-sm">
              <div className="flex justify-end gap-3">
                <dt className="text-slate-500">Invoice date</dt>
                <dd className="font-medium text-slate-900">{formatDate(inv.invoice_date)}</dd>
              </div>
              <div className="flex justify-end gap-3">
                <dt className="text-slate-500">Due date</dt>
                <dd className={`font-medium ${overdue ? "text-red-600" : "text-slate-900"}`}>{formatDate(inv.due_date)}</dd>
              </div>
              {inv.period_start && (
                <div className="flex justify-end gap-3">
                  <dt className="text-slate-500">Period</dt>
                  <dd className="font-medium text-slate-900">
                    {formatDate(inv.period_start)} – {formatDate(inv.period_end)}
                  </dd>
                </div>
              )}
              {inv.subscription_id && (
                <div className="no-print flex justify-end gap-3">
                  <dt className="text-slate-500">Subscription</dt>
                  <dd>
                    <Link to={`/subscriptions/${inv.subscription_id}`} className="font-medium text-indigo-600 hover:text-indigo-700">
                      View
                    </Link>
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>

        <table className="mt-8 w-full text-sm">
          <thead className="border-y border-slate-200 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="py-3">Description</th>
              <th className="py-3 text-right">Qty</th>
              <th className="py-3 text-right">Unit price</th>
              <th className="py-3 text-right">Tax</th>
              <th className="py-3 text-right">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(inv.lines ?? []).map((l, i) => (
              <tr key={i}>
                <td className="py-3 font-medium text-slate-900">{l.description}</td>
                <td className="py-3 text-right text-slate-700">{l.quantity}</td>
                <td className="py-3 text-right text-slate-700">{formatINR(l.unit_price)}</td>
                <td className="py-3 text-right text-slate-500">{formatINR(l.tax_amount)}</td>
                <td className="py-3 text-right font-semibold text-slate-900">{formatINR(l.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="ml-auto mt-6 max-w-xs space-y-2 text-sm">
          <div className="flex justify-between text-slate-600">
            <span>Subtotal</span>
            <span>{formatINR(inv.subtotal)}</span>
          </div>
          {!!inv.discount_total && (
            <div className="flex justify-between text-emerald-600">
              <span>Discount</span>
              <span>−{formatINR(inv.discount_total)}</span>
            </div>
          )}
          <div className="flex justify-between text-slate-600">
            <span>Tax (GST)</span>
            <span>{formatINR(inv.tax_total)}</span>
          </div>
          <div className="flex justify-between border-t border-slate-200 pt-2 text-base font-bold text-slate-900">
            <span>Total</span>
            <span>{formatINR(inv.total)}</span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>Paid</span>
            <span>{formatINR(inv.amount_paid ?? 0)}</span>
          </div>
          <div className={`flex justify-between rounded-lg px-3 py-2 font-bold ${amountDue > 0 ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-700"}`}>
            <span>Amount due</span>
            <span>{formatINR(amountDue)}</span>
          </div>
        </div>
      </div>

      <div className="no-print rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="flex items-center gap-2 font-bold text-slate-900">
          <Wallet className="h-4 w-4 text-slate-400" /> Payments
        </h3>
        {payments.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">No payments recorded yet.</p>
        ) : (
          <div className="mt-3 divide-y divide-slate-100">
            {payments.map((p) => (
              <div key={p.id} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-semibold capitalize text-slate-900">{p.method.replace(/_/g, " ")}</p>
                  <p className="text-xs text-slate-500">
                    {formatDate(p.payment_date)}
                    {p.note ? ` · ${p.note}` : ""}
                  </p>
                </div>
                <span className="font-semibold text-emerald-600">+{formatINR(p.amount)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal open={payOpen} title={`Record payment · ${inv.number}`} onClose={() => setPayOpen(false)}>
        <form onSubmit={savePayment} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Method</label>
              <select value={pay.method} onChange={(e) => setPay({ ...pay, method: e.target.value })} className={inputCls}>
                {METHODS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>Amount (₹)</label>
              <input required type="number" min="0.01" step="0.01" value={pay.amount} onChange={(e) => setPay({ ...pay, amount: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Date</label>
              <input required type="date" value={pay.date} onChange={(e) => setPay({ ...pay, date: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Note</label>
              <input value={pay.note} onChange={(e) => setPay({ ...pay, note: e.target.value })} placeholder="Optional" className={inputCls} />
            </div>
          </div>
          <p className="text-xs text-slate-500">Amount due: {formatINR(amountDue)}. Partial payments are allowed.</p>
          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => setPayOpen(false)} className={btnSecondary}>
              Cancel
            </button>
            <button type="submit" disabled={paying} className={`${btnPrimary.replace("w-full", "")}`}>
              {paying && <LoaderCircle className="h-4 w-4 animate-spin" />}
              Save payment
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}