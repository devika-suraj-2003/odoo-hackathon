import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import toast from "react-hot-toast";
import {
  IndianRupee,
  Repeat,
  ShieldAlert,
  TrendingUp,
  TriangleAlert,
  Wallet,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import { useAuth } from "../context/AuthContext";
import StatusBadge from "../components/StatusBadge";
import { formatINR } from "../lib/money";

type Sub = {
  id: number;
  number: string;
  status: string;
  total?: number;
  customer?: { name: string } | null;
  plan?: { name: string; billing_period: string } | null;
  next_billing_date?: string | null;
};
type Invoice = {
  id: number;
  number: string;
  status: string;
  due_date?: string | null;
  total: number;
  amount_due?: number;
  customer?: { name: string } | null;
};
type Summary = {
  active_subscriptions: number;
  mrr: number;
  arr: number;
  revenue: number;
  payments_total: number;
  outstanding: number;
  overdue_amount: number;
  overdue_count: number;
};
type MonthRevenue = { month: string; revenue: number };

function asArray<T>(result: PromiseSettledResult<{ data: unknown }>): T[] {
  return result.status === "fulfilled" && Array.isArray(result.value.data)
    ? (result.value.data as T[])
    : [];
}
const MONTHLY: Record<string, number> = {
  daily: 30,
  weekly: 4.33,
  monthly: 1,
  yearly: 1 / 12,
};
const STATUS_COLORS: Record<string, string> = {
  draft: "#94a3b8",
  quotation: "#f59e0b",
  confirmed: "#0ea5e9",
  active: "#10b981",
  paused: "#8b5cf6",
  closed: "#cbd5e1",
};
const rupeeTick = (value: number) =>
  `₹${value >= 1000 ? `${Math.round(value / 1000)}k` : value}`;
const monthlyOf = (subscription: Sub) =>
  (subscription.total ?? 0) *
  (MONTHLY[subscription.plan?.billing_period ?? "monthly"] ?? 1);

function Card({
  label,
  value,
  sub,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: LucideIcon;
  tone: string;
}) {
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
  const [summary, setSummary] = useState<Summary | null>(null);
  const [revenueByMonth, setRevenueByMonth] = useState<
    { key: string; label: string; revenue: number }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [ms, setMs] = useState<number | null>(null);
  const [effectiveToday, setEffectiveToday] = useState(
    new Date().toISOString().slice(0, 10),
  );

  useEffect(() => {
    let active = true;
    void (async () => {
      const started = performance.now();
      const [subscriptions, invoiceRows, report, monthly, settings] =
        await Promise.allSettled([
          api.get("/subscriptions"),
          api.get("/invoices"),
          api.get("/reports/summary"),
          api.get("/reports/monthly-revenue", { params: { months: 6 } }),
          api.get("/settings"),
        ]);
      if (!active) return;

      const subscriptionData = asArray<Sub>(subscriptions);
      const invoiceData = asArray<Invoice>(invoiceRows);
      setSubs(subscriptionData);
      setInvoices(invoiceData);
      if (settings.status === "fulfilled") {
        const simulatedDate = settings.value.data?.simulated_today;
        const realDate = settings.value.data?.real_today;
        setEffectiveToday(simulatedDate || realDate || new Date().toISOString().slice(0, 10));
      }

      if (
        report.status === "fulfilled" &&
        report.value.data &&
        typeof report.value.data === "object" &&
        !Array.isArray(report.value.data)
      ) {
        setSummary(report.value.data as Summary);
      } else {
        toast.error(
          errorMessage(
            report.status === "rejected" ? report.reason : null,
            "Could not load report summary",
          ),
          { id: "dashboard-report" },
        );
      }

      if (monthly.status === "fulfilled" && Array.isArray(monthly.value.data)) {
        setRevenueByMonth(
          (monthly.value.data as MonthRevenue[]).map((item) => ({
            key: item.month,
            label: new Date(`${item.month}-01T00:00:00`).toLocaleDateString(
              "en-IN",
              { month: "short" },
            ),
            revenue: item.revenue / 100,
          })),
        );
      } else {
        toast.error(
          errorMessage(
            monthly.status === "rejected" ? monthly.reason : null,
            "Could not load monthly revenue",
          ),
          { id: "dashboard-monthly" },
        );
      }

      setMs(Math.round(performance.now() - started));
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, []);

  const activeSubs = subs.filter((subscription) => subscription.status === "active");
  const unpaid = invoices.filter(
    (invoice) =>
      invoice.status === "confirmed" && (invoice.amount_due ?? invoice.total) > 0,
  );
  const overdueList = unpaid.filter(
    (invoice) => !!invoice.due_date && invoice.due_date < effectiveToday,
  );

  const forecast = useMemo(() => {
    const pipeline =
      subs
        .filter((subscription) => subscription.status === "confirmed")
        .reduce((sum, subscription) => sum + monthlyOf(subscription), 0) +
      0.5 *
        subs
          .filter((subscription) => subscription.status === "quotation")
          .reduce((sum, subscription) => sum + monthlyOf(subscription), 0);
    const closed = subs.filter((subscription) => subscription.status === "closed").length;
    const churn = subs.length ? Math.min(0.05, closed / subs.length / 6) : 0.02;
    const currentMrr = summary?.mrr ?? 0;
    const now = new Date();
    const points = [];
    for (let month = 0; month <= 6; month++) {
      const forecastDate = new Date(now.getFullYear(), now.getMonth() + month, 1);
      const value =
        month === 0
          ? currentMrr
          : (currentMrr + pipeline) * Math.pow(1 - churn, month);
      points.push({
        label: forecastDate.toLocaleDateString("en-IN", { month: "short" }),
        mrr: Math.round(value) / 100,
      });
    }
    return { points, pipeline: Math.round(pipeline), churn };
  }, [subs, summary?.mrr]);

  const atRisk = useMemo(() => {
    const customers = new Map<
      string,
      { name: string; count: number; amount: number; maxDays: number }
    >();
    for (const invoice of overdueList) {
      const name = invoice.customer?.name ?? "Unknown";
      const daysLate = invoice.due_date
        ? Math.floor(
            (new Date(`${effectiveToday}T00:00:00`).getTime() -
              new Date(`${invoice.due_date}T00:00:00`).getTime()) /
              86400000,
          )
        : 0;
      const customer = customers.get(name) ?? {
        name,
        count: 0,
        amount: 0,
        maxDays: 0,
      };
      customer.count += 1;
      customer.amount += invoice.amount_due ?? invoice.total;
      customer.maxDays = Math.max(customer.maxDays, daysLate);
      customers.set(name, customer);
    }
    return [...customers.values()]
      .map((customer) => ({
        ...customer,
        level: customer.count >= 2 || customer.maxDays > 30 ? "high" : "medium",
      }))
      .sort((left, right) => right.amount - left.amount)
      .slice(0, 5);
  }, [overdueList, effectiveToday]);

  const byStatus = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const subscription of subs) {
      counts[subscription.status] = (counts[subscription.status] ?? 0) + 1;
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [subs]);
  const upcoming = [...activeSubs]
    .filter((subscription) => subscription.next_billing_date)
    .sort((left, right) =>
      left.next_billing_date! < right.next_billing_date! ? -1 : 1,
    )
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">
            Welcome back, {user?.name?.split(" ")[0]} 👋
          </h2>
          <p className="text-sm text-slate-500">
            Here&apos;s how Brightloop is doing today.
          </p>
        </div>
        {ms !== null && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <Zap className="h-3.5 w-3.5" /> Loaded in {ms} ms
          </span>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Card label="Monthly recurring revenue" value={summary ? formatINR(summary.mrr) : "—"} sub="MRR from active subscriptions" icon={TrendingUp} tone="bg-indigo-50 text-indigo-600" />
        <Card label="Annual recurring revenue" value={summary ? formatINR(summary.arr) : "—"} sub="ARR = MRR × 12" icon={IndianRupee} tone="bg-violet-50 text-violet-600" />
        <Card label="Active subscriptions" value={summary ? String(summary.active_subscriptions) : "—"} sub={`${subs.length} total`} icon={Repeat} tone="bg-sky-50 text-sky-600" />
        <Card label="Revenue collected" value={summary ? formatINR(summary.revenue) : "—"} sub={summary ? `Payments total ${formatINR(summary.payments_total)}` : "From recorded payments"} icon={Wallet} tone="bg-emerald-50 text-emerald-600" />
        <Card label="Outstanding" value={summary ? formatINR(summary.outstanding) : "—"} sub={`${unpaid.length} unpaid invoices`} icon={TrendingUp} tone="bg-amber-50 text-amber-600" />
        <Card label="Overdue" value={summary ? formatINR(summary.overdue_amount) : "—"} sub={`${summary?.overdue_count ?? overdueList.length} invoices past due`} icon={TriangleAlert} tone="bg-red-50 text-red-600" />
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
                <Tooltip formatter={(value: number) => [`₹${Number(value).toLocaleString("en-IN")}`, "Revenue"]} />
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
                      {byStatus.map((item) => (
                        <Cell key={item.name} fill={STATUS_COLORS[item.name] ?? "#94a3b8"} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                {byStatus.map((item) => (
                  <span key={item.name} className="flex items-center gap-1.5 text-xs capitalize text-slate-600">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: STATUS_COLORS[item.name] ?? "#94a3b8" }} />
                    {item.name} ({item.value})
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
                <Tooltip formatter={(value: number) => [`₹${Number(value).toLocaleString("en-IN")}`, "MRR"]} />
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
              {atRisk.map((customer) => (
                <div key={customer.name} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <p className="font-semibold text-slate-900">{customer.name}</p>
                    <p className="text-xs text-slate-500">{customer.count} overdue · {customer.maxDays} days late</p>
                  </div>
                  <div className="text-right">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${customer.level === "high" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>
                      {customer.level === "high" ? "🔴 High" : "🟡 Medium"}
                    </span>
                    <p className="mt-1 text-xs font-semibold text-slate-700">{formatINR(customer.amount)}</p>
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
              {upcoming.map((subscription) => (
                <button key={subscription.id} onClick={() => navigate(`/subscriptions/${subscription.id}`)} className="flex w-full items-center justify-between py-3 text-left text-sm hover:bg-slate-50/70">
                  <div>
                    <p className="font-semibold text-slate-900">{subscription.customer?.name ?? subscription.number}</p>
                    <p className="text-xs text-slate-500">{subscription.plan?.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-slate-900">{formatINR(subscription.total)}</p>
                    <p className="text-xs text-indigo-600">{new Date(subscription.next_billing_date!).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}</p>
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
              {overdueList.slice(0, 5).map((invoice) => (
                <button key={invoice.id} onClick={() => navigate(`/invoices/${invoice.id}`)} className="flex w-full items-center justify-between py-3 text-left text-sm hover:bg-slate-50/70">
                  <div>
                    <p className="font-semibold text-slate-900">{invoice.customer?.name ?? invoice.number}</p>
                    <p className="text-xs text-slate-500">{invoice.number}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-red-600">{formatINR(invoice.amount_due ?? invoice.total)}</span>
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
