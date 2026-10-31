import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Search, FileText, Wallet, CircleCheck, Clock, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import StatusBadge from "../components/StatusBadge";
import { formatINR } from "../lib/money";

type Invoice = {
  id: number;
  number: string;
  subscription_id?: number;
  customer?: { id: number; name: string } | null;
  status: string;
  invoice_date?: string | null;
  due_date?: string | null;
  total: number;
  amount_paid?: number;
  amount_due?: number;
};

const TABS = ["all", "draft", "confirmed", "overdue", "paid", "cancelled"] as const;
type Tab = (typeof TABS)[number];

const todayStr = () => new Date().toISOString().slice(0, 10);

function isOverdue(inv: Invoice) {
  return inv.status === "confirmed" && !!inv.due_date && inv.due_date < todayStr() && (inv.amount_due ?? inv.total) > 0;
}

function shownStatus(inv: Invoice) {
  return isOverdue(inv) ? "overdue" : inv.status;
}

function formatDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function Stat({ label, value, icon: Icon, tone }: { label: string; value: string; icon: LucideIcon; tone: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <div className={`grid h-9 w-9 place-items-center rounded-xl ${tone}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-3 text-2xl font-bold text-slate-900">{value}</p>
    </div>
  );
}

export default function Invoices() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("all");
  const [query, setQuery] = useState("");

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/invoices");
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load invoices"), { id: "inv-load" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const stats = useMemo(() => {
    let invoiced = 0, paid = 0, outstanding = 0, overdue = 0;
    for (const inv of items) {
      if (inv.status === "cancelled") continue;
      invoiced += inv.total ?? 0;
      paid += inv.amount_paid ?? 0;
      if (inv.status === "confirmed") outstanding += inv.amount_due ?? inv.total ?? 0;
      if (isOverdue(inv)) overdue += inv.amount_due ?? inv.total ?? 0;
    }
    return { invoiced, paid, outstanding, overdue };
  }, [items]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    for (const inv of items) {
      const s = shownStatus(inv);
      c[s] = (c[s] ?? 0) + 1;
    }
    return c;
  }, [items]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((inv) => {
      if (tab !== "all" && shownStatus(inv) !== tab) return false;
      if (!q) return true;
      return inv.number?.toLowerCase().includes(q) || inv.customer?.name?.toLowerCase().includes(q);
    });
  }, [items, tab, query]);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Total invoiced" value={formatINR(stats.invoiced)} icon={FileText} tone="bg-indigo-50 text-indigo-600" />
        <Stat label="Paid" value={formatINR(stats.paid)} icon={CircleCheck} tone="bg-emerald-50 text-emerald-600" />
        <Stat label="Outstanding" value={formatINR(stats.outstanding)} icon={Clock} tone="bg-amber-50 text-amber-600" />
        <Stat label="Overdue" value={formatINR(stats.overdue)} icon={TriangleAlert} tone="bg-red-50 text-red-600" />
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
              {t}
              <span className={`rounded-md px-1.5 text-xs ${tab === t ? "bg-white/20" : "bg-slate-100 text-slate-500"}`}>{counts[t] ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search invoices..."
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3">Invoice</th>
              <th className="px-5 py-3">Customer</th>
              <th className="px-5 py-3">Date</th>
              <th className="px-5 py-3">Due</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3 text-right">Total</th>
              <th className="px-5 py-3 text-right">Amount due</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading &&
              [1, 2, 3, 4].map((i) => (
                <tr key={i}>
                  <td colSpan={7} className="px-5 py-4">
                    <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
                  </td>
                </tr>
              ))}

            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-16 text-center">
                  <Wallet className="mx-auto h-10 w-10 text-slate-300" />
                  <p className="mt-3 font-semibold text-slate-700">No invoices here</p>
                  <p className="text-sm text-slate-500">Invoices are generated automatically from active subscriptions.</p>
                </td>
              </tr>
            )}

            {!loading &&
              filtered.map((inv) => (
                <tr key={inv.id} onClick={() => navigate(`/invoices/${inv.id}`)} className="cursor-pointer transition hover:bg-slate-50/70">
                  <td className="px-5 py-4 font-semibold text-indigo-600">{inv.number}</td>
                  <td className="px-5 py-4 font-medium text-slate-900">{inv.customer?.name ?? "—"}</td>
                  <td className="px-5 py-4 text-slate-600">{formatDate(inv.invoice_date)}</td>
                  <td className={`px-5 py-4 ${isOverdue(inv) ? "font-semibold text-red-600" : "text-slate-600"}`}>{formatDate(inv.due_date)}</td>
                  <td className="px-5 py-4">
                    <StatusBadge status={shownStatus(inv)} />
                  </td>
                  <td className="px-5 py-4 text-right font-semibold text-slate-900">{formatINR(inv.total)}</td>
                  <td className="px-5 py-4 text-right text-slate-700">{formatINR(inv.amount_due ?? 0)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}