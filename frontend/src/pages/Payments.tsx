import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Search, Wallet, CircleCheck, Clock, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import api from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { formatINR } from "../lib/money";

type Payment = {
  id: number;
  invoice_id: number;
  invoice_number?: string;
  customer?: { id: number; name: string } | null;
  method: string;
  amount: number;
  payment_date?: string | null;
  note?: string | null;
};
type Invoice = {
  id: number;
  number: string;
  customer?: { id: number; name: string } | null;
  status: string;
  due_date?: string | null;
  total: number;
  amount_due?: number;
};

const TABS = ["received", "outstanding", "overdue"] as const;
type Tab = (typeof TABS)[number];

const todayStr = () => new Date().toISOString().slice(0, 10);

function formatDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function daysLate(d?: string | null) {
  if (!d) return 0;
  return Math.max(0, Math.floor((Date.now() - new Date(d).getTime()) / 86400000));
}

function Stat({ label, value, sub, icon: Icon, tone }: { label: string; value: string; sub: string; icon: LucideIcon; tone: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <div className={`grid h-9 w-9 place-items-center rounded-xl ${tone}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-3 text-2xl font-bold text-slate-900">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{sub}</p>
    </div>
  );
}

export default function Payments() {
  const navigate = useNavigate();
  const [payments, setPayments] = useState<Payment[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("received");
  const [query, setQuery] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      const [p, i] = await Promise.allSettled([api.get("/payments"), api.get("/invoices")]);
      setPayments(p.status === "fulfilled" && Array.isArray(p.value.data) ? p.value.data : []);
      setInvoices(i.status === "fulfilled" && Array.isArray(i.value.data) ? i.value.data : []);
      if (p.status === "rejected" && i.status === "rejected") toast.error("Could not load payments", { id: "pay-load" });
      setLoading(false);
    })();
  }, []);

  const outstanding = useMemo(
    () => invoices.filter((inv) => inv.status === "confirmed" && (inv.amount_due ?? inv.total) > 0),
    [invoices]
  );
  const overdue = useMemo(() => outstanding.filter((inv) => !!inv.due_date && inv.due_date < todayStr()), [outstanding]);

  const sum = (list: { amount_due?: number; total: number }[]) => list.reduce((s, x) => s + (x.amount_due ?? x.total ?? 0), 0);
  const received = payments.reduce((s, p) => s + (p.amount ?? 0), 0);

  const q = query.trim().toLowerCase();
  const shownPayments = payments.filter(
    (p) => !q || p.invoice_number?.toLowerCase().includes(q) || p.customer?.name?.toLowerCase().includes(q) || p.method?.includes(q)
  );
  const shownInvoices = (tab === "overdue" ? overdue : outstanding).filter(
    (inv) => !q || inv.number?.toLowerCase().includes(q) || inv.customer?.name?.toLowerCase().includes(q)
  );

  const counts: Record<Tab, number> = { received: payments.length, outstanding: outstanding.length, overdue: overdue.length };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Received" value={formatINR(received)} sub={`${payments.length} payments`} icon={CircleCheck} tone="bg-emerald-50 text-emerald-600" />
        <Stat label="Outstanding" value={formatINR(sum(outstanding))} sub={`${outstanding.length} unpaid invoices`} icon={Clock} tone="bg-amber-50 text-amber-600" />
        <Stat label="Overdue" value={formatINR(sum(overdue))} sub={`${overdue.length} past due date`} icon={TriangleAlert} tone="bg-red-50 text-red-600" />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold capitalize transition ${
                tab === t ? "bg-indigo-600 text-white shadow-sm" : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
              }`}
            >
              {t === "received" ? "Payments received" : t}
              <span className={`rounded-md px-1.5 text-xs ${tab === t ? "bg-white/20" : "bg-slate-100 text-slate-500"}`}>{counts[t]}</span>
            </button>
          ))}
        </div>
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search..."
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {tab === "received" ? (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Invoice</th>
                <th className="px-5 py-3">Customer</th>
                <th className="px-5 py-3">Method</th>
                <th className="px-5 py-3">Note</th>
                <th className="px-5 py-3 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && (
                <tr>
                  <td colSpan={6} className="px-5 py-4">
                    <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
                  </td>
                </tr>
              )}
              {!loading && shownPayments.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-16 text-center">
                    <Wallet className="mx-auto h-10 w-10 text-slate-300" />
                    <p className="mt-3 font-semibold text-slate-700">No payments yet</p>
                    <p className="text-sm text-slate-500">Record a payment from an invoice page.</p>
                  </td>
                </tr>
              )}
              {!loading &&
                shownPayments.map((p) => (
                  <tr key={p.id} onClick={() => navigate(`/invoices/${p.invoice_id}`)} className="cursor-pointer transition hover:bg-slate-50/70">
                    <td className="px-5 py-4 text-slate-600">{formatDate(p.payment_date)}</td>
                    <td className="px-5 py-4 font-semibold text-indigo-600">{p.invoice_number ?? `#${p.invoice_id}`}</td>
                    <td className="px-5 py-4 font-medium text-slate-900">{p.customer?.name ?? "—"}</td>
                    <td className="px-5 py-4">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium capitalize text-slate-700">{p.method?.replace(/_/g, " ")}</span>
                    </td>
                    <td className="max-w-xs truncate px-5 py-4 text-slate-500">{p.note ?? "—"}</td>
                    <td className="px-5 py-4 text-right font-semibold text-emerald-600">+{formatINR(p.amount)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3">Invoice</th>
                <th className="px-5 py-3">Customer</th>
                <th className="px-5 py-3">Due date</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 text-right">Total</th>
                <th className="px-5 py-3 text-right">Amount due</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {!loading && shownInvoices.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-16 text-center">
                    <CircleCheck className="mx-auto h-10 w-10 text-emerald-300" />
                    <p className="mt-3 font-semibold text-slate-700">{tab === "overdue" ? "Nothing overdue" : "Nothing outstanding"}</p>
                    <p className="text-sm text-slate-500">All caught up.</p>
                  </td>
                </tr>
              )}
              {shownInvoices.map((inv) => {
                const late = tab === "overdue" ? daysLate(inv.due_date) : 0;
                return (
                  <tr key={inv.id} onClick={() => navigate(`/invoices/${inv.id}`)} className="cursor-pointer transition hover:bg-slate-50/70">
                    <td className="px-5 py-4 font-semibold text-indigo-600">{inv.number}</td>
                    <td className="px-5 py-4 font-medium text-slate-900">{inv.customer?.name ?? "—"}</td>
                    <td className={`px-5 py-4 ${late ? "font-semibold text-red-600" : "text-slate-600"}`}>
                      {formatDate(inv.due_date)}
                      {late > 0 && <span className="ml-2 text-xs">({late} days late)</span>}
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={late ? "overdue" : "outstanding"} />
                    </td>
                    <td className="px-5 py-4 text-right text-slate-700">{formatINR(inv.total)}</td>
                    <td className="px-5 py-4 text-right font-semibold text-slate-900">{formatINR(inv.amount_due ?? inv.total)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}