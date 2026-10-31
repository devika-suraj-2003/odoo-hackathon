import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Repeat, TrendingUp, Wallet, Clock, TriangleAlert, IndianRupee, Zap, ShieldAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusBadge from "../components/StatusBadge";
import { formatINR } from "../lib/money";

type Sub = { id: number; number: string; status: string; total?: number; customer?: { id?: number; name: string } | null; plan?: { name: string; billing_period: string } | null; next_billing_date?: string | null };
type Invoice = { id: number; number: string; status: string; due_date?: string | null; total: number; amount_due?: number; customer?: { id?: number; name: string } | null };
type Payment = { id: number; amount: number; payment_date?: string | null };
type Summary = Partial<{ active_subscriptions: number; mrr: number; arr: number; revenue: number; outstanding: number; overdue_amount: number; overdue_count: number }>;

const todayStr = () => new Date().toISOString().slice(0, 10);
const arr = (r: PromiseSettledResult<any>) => (r.status === "fulfilled" && Array.isArray(r.value.data) ? r.value.data : []);
const MONTHLY: Record<string, number> = { daily: 30, weekly: 4.33, monthly: 1, yearly: 1 / 12 };
const STATUS_COLORS: Record<string, string> = { draft: "#94a3b8", quotation: "#f59e0b", confirmed: "#0ea5e9", active: "#10b981", paused: "#8b5cf6", closed: "#cbd5e1" };
const rupeeTick = (v: number) => `₹${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`;
const monthlyOf = (s: Sub) => (s.total ?? 0) * (MONTHLY[s.plan?.billing_period ?? "monthly"] ?? 1);

function Card({ label, value, sub, icon: Icon, tone }: { label: string; value: string; sub?: string; icon: LucideIcon; tone: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <div className={`grid h-9 w-9 place-items-center rounded-xl ${tone}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-3 text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [subs, setSubs] = useState<Sub[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [summary, setSummary] = useState<Summary>({});
  const [loading, setLoading] = useState(true);
  const [ms, setMs] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      const t0 = performance.now();
      const [s, i, p, r] = await Promise.allSettled([api.get("/subscriptions"), api.get("/invoices"), api.get("/payments"), api.get("/reports/summary")]);
      setSubs(arr(s));
      setInvoices(arr(i));
      setPayments(arr(p));
      setSummary(r.status === "fulfilled" && r.value.data && typeof r.value.data === "object" && !Array.isArray(r.value.data) ? r.value.data : {});
      setMs(Math.round(performance.now() - t0));
      setLoading(false);
    })();
  }, []);

  const active = subs.filter((s) => s.status === "active");
  const mrr = typeof summary.mrr === "number" ? summary.mrr : Math.round(active.reduce((sum, s) => sum + monthlyOf(s), 0));
  const arrValue = typeof summary.arr === "number" ? summary.arr : mrr * 12;
  const revenue = typeof summary.revenue === "number" ? summary.revenue : payments.reduce((s, p) => s + (p.amount ?? 0), 0);
  const unpaid = invoices.filter((i) => i.status === "confirmed" && (i.amount_due ?? i.total) > 0);
  const overdueList = unpaid.filter((i) => !!i.due_date && i.due_date < todayStr());
  const outstanding = typeof summary.outstanding === "number" ? summary.outstanding : unpaid.reduce((s, i) => s + (i.amount_due ?? i.total), 0);
  const overdueAmount = typeof summary.overdue_amount === "number" ? summary.overdue_amount : overdueList.reduce((s, i) => s + (i.amount_due ?? i.total), 0);

  const revenueByMonth = useMemo(() => {
    const months: { key: string; label: string; revenue: number }[] = [];
    const now = new Date();
    for (let k = 5; k >= 0; k--) {
      const d = new Date(now.getFullYear(), now.getMonth() - k, 1);
      months.push({ key: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`, label: d.toLocaleDateString("en-IN", { month: "short" }), revenue: 0 });
    }
    for (const p of payments) {
      const m = months.find((x) => x.key === (p.payment_date ?? "").slice(0, 7));
      if (m) m.revenue += (p.amount ?? 0) / 100;
    }
    return months;
  }, [payments]);

  const forecast = useMemo(() => {
    const pipeline = subs.filter((s) => s.status === "confirmed").reduce((a, s) => a + monthlyOf(s), 0) + 0.5 * subs.filter((s) => s.status === "quotation").reduce((a, s) => a + monthlyOf(s), 0);
    const closed = subs.filter((s) => s.status === "closed").length;
    const churn = subs.length ? Math.min(0.05, closed / subs.length / 6) : 0.02;
    const now = new Date();
    const points = [];
    for (let k = 0; k <= 6; k++) {
      const d = new Date(now.getFullYear(), now.getMonth() + k, 1);
      const value = k === 0 ? mrr : (mrr + pipeline) * Math.pow(1 - churn, k);
      points.push({ label: d.toLocaleDateString("en-IN", { month: "short" }), mrr: Math.round(value) / 100 });
    }
    return { points, pipeline: Math.round(pipeline), churn };
  }, [subs, mrr]);

  const atRisk = useMemo(() => {
    const map = new Map<string, { name: string; count: number; amount: number; maxDays: number }>();
    for (const inv of overdueList) {
      const name = inv.customer?.name ?? "Unknown";
      const days = inv.due_date ? Math.floor((Date.now() - new Date(inv.due_date).getTime()) / 86400000) : 0;
      const cur = map.get(name) ?? { name, count: 0, amount: 0, maxDays: 0 };
      cur.count += 1;
      cur.amount += inv.amount_due ?? inv.total;
      cur.maxDays = Math.max(cur.maxDays, days);
      map.set(name, cur);
    }
    return [...map.values()]
      .map((c) => ({ ...c, level: c.count >= 2 || c.maxDays > 30 ? "high" : "medium" }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 5);
  }, [overdueList]);

  const byStatus = useMemo(() => {
    const c: Record<string, number> = {};
    for (const s of subs) c[s.status] = (c[s.status] ?? 0) + 1;
    return Object.entries(c).map(([name, value]) => ({ name, value }));
  }, [subs]);

  const upcoming = [...active].filter((s) => s.next_billing_date).sort((a, b) => (a.next_billing_date! < b.next_billing_date! ? -1 : 1)).slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Welcome back, {user?.name?.split(" ")[0]} 👋</h2>
          <p className="text-sm text-slate-500">Here's how Brightloop is doing today.</p>
        </div>
        {ms !== null && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <Zap className="h-3.5 w-3.5" /> Loaded in {ms} ms
          </span>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Card label="Monthly recurring revenue" value={formatINR(mrr)} sub="MRR from active subscriptions" icon={TrendingUp} tone="bg-indigo-50 text-indigo-600" />
        <Card label="Annual recurring revenue" value={formatINR(arrValue)} sub="ARR = MRR × 12" icon={IndianRupee} tone="bg-violet-50 text-violet-600" />
        <Card label="Active subscriptions" value={String(summary.active_subscriptions ?? active.length)} sub={`${subs.length} total`} icon={Repeat} tone="bg-sky-50 text-sky-600" />
        <Card label="Revenue collected" value={formatINR(revenue)} sub={`${payments.length} payments`} icon={Wallet} tone="bg-emerald-50 text-emerald-600" />
        <Card label="Outstanding" value={formatINR(outstanding)} sub={`${unpaid.length} unpaid invoices`} icon={Clock} tone="bg-amber-50 text-amber-600" />
        <Card label="Overdue" value={formatINR(overdueAmount)} sub={`${summary.overdue_count ?? overdueList.length} invoices past due`} icon={TriangleAlert} tone="bg-red-50 text-red-600" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <h3 className="font-bold text-slate-900">Revenue, last 6 months</h3>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={revenueByMonth}>
                <defs>
                  <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} tickFormatter={rupeeTick} />
                <Tooltip formatter={(v: any) => [`₹${Number(v).toLocaleString("en-IN")}`, "Revenue"]} />
                <Area type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={2.5} fill="url(#rev)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-bold text-slate-900">Subscriptions by status</h3>
          {byStatus.length === 0 ? (
            <p className="mt-10 text-center text-sm text-slate-500">{loading ? "Loading..." : "No subscriptions yet"}</p>
          ) : (
            <>
              <div className="mt-2 h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={byStatus} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={3}>
                      {byStatus.map((d) => (
                        <Cell key={d.name} fill={STATUS_COLORS[d.name] ?? "#94a3b8"} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                {byStatus.map((d) => (
                  <span key={d.name} className="flex items-center gap-1.5 text-xs capitalize text-slate-600">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: STATUS_COLORS[d.name] ?? "#94a3b8" }} />
                    {d.name} ({d.value})
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="font-bold text-slate-900">MRR forecast, next 6 months</h3>
              <p className="text-xs text-slate-500">
                Current MRR + pipeline ({formatINR(forecast.pipeline)} from confirmed and 50% of quotations) − {(forecast.churn * 100).toFixed(1)}% monthly churn
              </p>
            </div>
            <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">Projection</span>
          </div>
          <div className="mt-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={forecast.points}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} tickFormatter={rupeeTick} />
                <Tooltip formatter={(v: any) => [`₹${Number(v).toLocaleString("en-IN")}`, "MRR"]} />
                <Line type="monotone" dataKey="mrr" stroke="#8b5cf6" strokeWidth={2.5} strokeDasharray="6 4" dot={{ r: 4, fill: "#8b5cf6" }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="flex items-center gap-2 font-bold text-slate-900">
            <ShieldAlert className="h-4 w-4 text-red-500" /> Customers at risk
          </h3>
          <p className="text-xs text-slate-500">Based on overdue invoices</p>
          {atRisk.length === 0 ? (
            <p className="mt-6 text-center text-sm text-slate-500">No customers at risk. 🎉</p>
          ) : (
            <div className="mt-3 divide-y divide-slate-100">
              {atRisk.map((c) => (
                <div key={c.name} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <p className="font-semibold text-slate-900">{c.name}</p>
                    <p className="text-xs text-slate-500">
                      {c.count} overdue · {c.maxDays} days late
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${c.level === "high" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>
                      {c.level === "high" ? "🔴 High" : "🟡 Medium"}
                    </span>
                    <p className="mt-1 text-xs font-semibold text-slate-700">{formatINR(c.amount)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-bold text-slate-900">Upcoming renewals</h3>
          {upcoming.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">No upcoming renewals.</p>
          ) : (
            <div className="mt-3 divide-y divide-slate-100">
              {upcoming.map((s) => (
                <button key={s.id} onClick={() => navigate(`/subscriptions/${s.id}`)} className="flex w-full items-center justify-between py-3 text-left text-sm hover:bg-slate-50/70">
                  <div>
                    <p className="font-semibold text-slate-900">{s.customer?.name ?? s.number}</p>
                    <p className="text-xs text-slate-500">{s.plan?.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-slate-900">{formatINR(s.total)}</p>
                    <p className="text-xs text-indigo-600">{new Date(s.next_billing_date!).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-bold text-slate-900">Overdue invoices</h3>
          {overdueList.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">Nothing overdue. 🎉</p>
          ) : (
            <div className="mt-3 divide-y divide-slate-100">
              {overdueList.slice(0, 5).map((inv) => (
                <button key={inv.id} onClick={() => navigate(`/invoices/${inv.id}`)} className="flex w-full items-center justify-between py-3 text-left text-sm hover:bg-slate-50/70">
                  <div>
                    <p className="font-semibold text-slate-900">{inv.customer?.name ?? inv.number}</p>
                    <p className="text-xs text-slate-500">{inv.number}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-red-600">{formatINR(inv.amount_due ?? inv.total)}</span>
                    <StatusBadge status="overdue" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}