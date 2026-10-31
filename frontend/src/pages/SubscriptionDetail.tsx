import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { ArrowLeft, Send, CircleCheck, Play, Pause, RotateCcw, CircleX, LoaderCircle, Check, History, FileText } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import StatusBadge from "../components/StatusBadge";
import { formatINR } from "../lib/money";

type Line = { id: number; product_name: string; quantity: number; unit_price: number; tax_amount?: number; amount: number };
type HistoryItem = { at: string; from_status?: string | null; to_status: string; note?: string | null };
type Sub = {
  id: number;
  number: string;
  status: string;
  customer?: { id: number; name: string; email?: string } | null;
  plan?: { id: number; name: string; billing_period: string } | null;
  start_date?: string | null;
  expiry_date?: string | null;
  next_billing_date?: string | null;
  payment_terms?: number | string | null;
  lines?: Line[];
  subtotal?: number;
  tax_total?: number;
  total?: number;
  history?: HistoryItem[];
};
type Invoice = { id: number; number: string; status: string; invoice_date?: string; total: number; amount_due?: number; subscription_id?: number };
type Action = { key: string; label: string; icon: LucideIcon; style: "primary" | "secondary" | "danger" };

const STEPS = ["draft", "quotation", "confirmed", "active", "closed"];

const ACTIONS: Record<string, Action[]> = {
  draft: [
    { key: "send-quotation", label: "Send quotation", icon: Send, style: "primary" },
    { key: "close", label: "Close", icon: CircleX, style: "danger" },
  ],
  quotation: [
    { key: "confirm", label: "Confirm", icon: CircleCheck, style: "primary" },
    { key: "close", label: "Close", icon: CircleX, style: "danger" },
  ],
  confirmed: [{ key: "activate", label: "Activate", icon: Play, style: "primary" }],
  active: [
    { key: "pause", label: "Pause", icon: Pause, style: "secondary" },
    { key: "close", label: "Close", icon: CircleX, style: "danger" },
  ],
  paused: [
    { key: "resume", label: "Resume", icon: Play, style: "primary" },
    { key: "close", label: "Close", icon: CircleX, style: "danger" },
  ],
  closed: [{ key: "renew", label: "Renew", icon: RotateCcw, style: "secondary" }],
};

const BTN: Record<Action["style"], string> = {
  primary: "bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm",
  secondary: "bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50",
  danger: "bg-white text-red-600 ring-1 ring-red-200 hover:bg-red-50",
};

function formatDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function formatDateTime(d?: string | null) {
  if (!d) return "";
  return new Date(d).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function formatTerms(t?: number | string | null) {
  if (t === null || t === undefined || t === "") return "—";
  const n = Number(t);
  if (Number.isNaN(n)) return String(t).replace(/_/g, " ");
  return n === 0 ? "Immediate" : `${n} days`;
}

export default function SubscriptionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [sub, setSub] = useState<Sub | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get(`/subscriptions/${id}`);
      setSub(data && data.id ? data : null);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load subscription"), { id: "sub-load" });
    } finally {
      setLoading(false);
    }
    try {
      const { data } = await api.get("/invoices/", { params: { subscription_id: id } });
      const all: Invoice[] = Array.isArray(data) ? data : [];
      setInvoices(all.filter((inv) => inv.subscription_id === undefined || String(inv.subscription_id) === String(id)));
    } catch {
      setInvoices([]);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  async function runAction(a: Action) {
    if (a.key === "close" && !confirm("Close this subscription? It will stop billing.")) return;
    setBusy(a.key);
    try {
      const { data } = await api.post(`/subscriptions/${id}/${a.key}`);
      if (data && data.id) setSub(data);
      else await load();
      toast.success(`${a.label} done`);
    } catch (err) {
      toast.error(errorMessage(err, `${a.label} failed`));
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-slate-200" />
        <div className="h-40 animate-pulse rounded-2xl bg-slate-100" />
        <div className="h-64 animate-pulse rounded-2xl bg-slate-100" />
      </div>
    );
  }

  if (!sub) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
        <p className="font-semibold text-slate-800">Subscription not found</p>
        <button onClick={() => navigate("/subscriptions")} className="mt-4 text-sm font-semibold text-indigo-600 hover:text-indigo-700">
          Back to subscriptions
        </button>
      </div>
    );
  }

  const status = sub.status?.toLowerCase() ?? "draft";
  const stepIndex = STEPS.indexOf(status === "paused" ? "active" : status);
  const actions = ACTIONS[status] ?? [];
  const history = [...(sub.history ?? [])].reverse();

  return (
    <div className="space-y-6">
      <Link to="/subscriptions" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> All subscriptions
      </Link>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-slate-900">{sub.number}</h2>
              <StatusBadge status={status} />
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {sub.customer?.name ?? "—"}
              {sub.customer?.email ? ` · ${sub.customer.email}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {actions.map((a) => {
              const Icon = a.icon;
              return (
                <button
                  key={a.key}
                  onClick={() => runAction(a)}
                  disabled={busy !== null}
                  className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:opacity-60 ${BTN[a.style]}`}
                >
                  {busy === a.key ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                  {a.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-8 flex items-center">
          {STEPS.map((s, i) => {
            const done = i < stepIndex || (status === "closed" && i === stepIndex);
            const current = i === stepIndex && status !== "closed";
            return (
              <div key={s} className="flex flex-1 items-center last:flex-none">
                <div className="flex flex-col items-center gap-2">
                  <div
                    className={`grid h-9 w-9 place-items-center rounded-full text-sm font-bold transition ${
                      done ? "bg-indigo-600 text-white" : current ? "bg-indigo-50 text-indigo-700 ring-2 ring-indigo-600" : "bg-slate-100 text-slate-400"
                    }`}
                  >
                    {done ? <Check className="h-4 w-4" /> : i + 1}
                  </div>
                  <span className={`text-xs font-semibold capitalize ${done || current ? "text-slate-800" : "text-slate-400"}`}>{s === "active" && status === "paused" ? "paused" : s}</span>
                </div>
                {i < STEPS.length - 1 && <div className={`mx-2 mb-6 h-0.5 flex-1 rounded ${i < stepIndex ? "bg-indigo-600" : "bg-slate-200"}`} />}
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="font-bold text-slate-900">Details</h3>
            <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-4 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-slate-500">Plan</dt>
                <dd className="font-semibold text-slate-900">{sub.plan?.name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Billing period</dt>
                <dd className="font-semibold capitalize text-slate-900">{sub.plan?.billing_period ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Payment terms</dt>
                <dd className="font-semibold text-slate-900">{formatTerms(sub.payment_terms)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Start date</dt>
                <dd className="font-semibold text-slate-900">{formatDate(sub.start_date)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Expiry date</dt>
                <dd className="font-semibold text-slate-900">{formatDate(sub.expiry_date)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Next billing</dt>
                <dd className="font-semibold text-indigo-600">{formatDate(sub.next_billing_date)}</dd>
              </div>
            </dl>
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="px-6 pt-5">
              <h3 className="font-bold text-slate-900">Order lines</h3>
            </div>
            <table className="mt-4 w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-6 py-3">Product</th>
                  <th className="px-6 py-3 text-right">Qty</th>
                  <th className="px-6 py-3 text-right">Unit price</th>
                  <th className="px-6 py-3 text-right">Tax</th>
                  <th className="px-6 py-3 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(sub.lines ?? []).length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                      No lines
                    </td>
                  </tr>
                )}
                {(sub.lines ?? []).map((l) => (
                  <tr key={l.id}>
                    <td className="px-6 py-3 font-medium text-slate-900">{l.product_name}</td>
                    <td className="px-6 py-3 text-right text-slate-700">{l.quantity}</td>
                    <td className="px-6 py-3 text-right text-slate-700">{formatINR(l.unit_price)}</td>
                    <td className="px-6 py-3 text-right text-slate-500">{formatINR(l.tax_amount)}</td>
                    <td className="px-6 py-3 text-right font-semibold text-slate-900">{formatINR(l.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="ml-auto max-w-xs space-y-2 border-t border-slate-200 px-6 py-4 text-sm">
              <div className="flex justify-between text-slate-600">
                <span>Subtotal</span>
                <span>{formatINR(sub.subtotal)}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Tax</span>
                <span>{formatINR(sub.tax_total)}</span>
              </div>
              <div className="flex justify-between border-t border-slate-200 pt-2 text-base font-bold text-slate-900">
                <span>Total</span>
                <span>{formatINR(sub.total)}</span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="flex items-center gap-2 font-bold text-slate-900">
              <FileText className="h-4 w-4 text-slate-400" /> Invoices
            </h3>
            {invoices.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No invoices yet. They are created automatically once the subscription is active.</p>
            ) : (
              <div className="mt-3 divide-y divide-slate-100">
                {invoices.map((inv) => (
                  <Link key={inv.id} to={`/invoices/${inv.id}`} className="flex items-center justify-between py-3 text-sm hover:bg-slate-50/70">
                    <div>
                      <p className="font-semibold text-indigo-600">{inv.number}</p>
                      <p className="text-xs text-slate-500">{formatDate(inv.invoice_date)}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-slate-900">{formatINR(inv.total)}</span>
                      <StatusBadge status={inv.status} />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="flex items-center gap-2 font-bold text-slate-900">
            <History className="h-4 w-4 text-slate-400" /> History
          </h3>
          {history.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">No changes yet.</p>
          ) : (
            <ol className="relative mt-5 space-y-6 border-l-2 border-slate-100 pl-6">
              {history.map((h, i) => (
                <li key={i} className="relative">
                  <span className={`absolute -left-[31px] top-0.5 h-4 w-4 rounded-full ring-4 ring-white ${i === 0 ? "bg-indigo-600" : "bg-slate-300"}`} />
                  <p className="text-sm font-semibold capitalize text-slate-900">{h.from_status ? `${h.from_status} → ${h.to_status}` : `Created as ${h.to_status}`}</p>
                  {h.note && <p className="mt-0.5 text-xs text-slate-600">{h.note}</p>}
                  <p className="mt-0.5 text-xs text-slate-400">{formatDateTime(h.at)}</p>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}
