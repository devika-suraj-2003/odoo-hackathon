import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Activity, Download, FileDown, IndianRupee, TriangleAlert, Wallet } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import { formatINR } from "../lib/money";

type Summary = {
  active_subscriptions: number;
  mrr: number;
  arr: number;
  revenue: number;
  outstanding: number;
  overdue_amount: number;
  overdue_count: number;
};
type MonthRevenue = { month: string; revenue: number };

const EMPTY: Summary = {
  active_subscriptions: 0,
  mrr: 0,
  arr: 0,
  revenue: 0,
  outstanding: 0,
  overdue_amount: 0,
  overdue_count: 0,
};

const cards = [
  { key: "active_subscriptions", label: "Active subscriptions", money: false, icon: Activity, color: "text-sky-600 bg-sky-50" },
  { key: "mrr", label: "Monthly recurring revenue", money: true, icon: IndianRupee, color: "text-indigo-600 bg-indigo-50" },
  { key: "arr", label: "Annual recurring revenue", money: true, icon: IndianRupee, color: "text-violet-600 bg-violet-50" },
  { key: "revenue", label: "Collected revenue", money: true, icon: Wallet, color: "text-emerald-600 bg-emerald-50" },
  { key: "outstanding", label: "Outstanding payments", money: true, icon: Wallet, color: "text-amber-600 bg-amber-50" },
  { key: "overdue_amount", label: "Overdue invoices", money: true, icon: TriangleAlert, color: "text-red-600 bg-red-50" },
] as const;

export default function Reports() {
  const [summary, setSummary] = useState<Summary>(EMPTY);
  const [months, setMonths] = useState<MonthRevenue[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([api.get("/reports/summary"), api.get("/reports/monthly-revenue", { params: { months: 12 } })])
      .then(([summaryResponse, monthsResponse]) => {
        if (!active) return;
        setSummary({ ...EMPTY, ...summaryResponse.data });
        setMonths(Array.isArray(monthsResponse.data) ? monthsResponse.data : []);
      })
      .catch((err) => {
        if (active) toast.error(errorMessage(err, "Could not load reports"), { id: "reports-load" });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function downloadReport() {
    setDownloading(true);
    try {
      const { data } = await api.get("/reports/pdf", { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "brightloop-report.pdf";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(errorMessage(err, "Could not download report"));
    } finally {
      setDownloading(false);
    }
  }

  const chartData = months.map((item) => ({
    month: new Date(`${item.month}-01T00:00:00`).toLocaleDateString("en-IN", { month: "short", year: "2-digit" }),
    revenue: item.revenue / 100,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Reports & analytics</h2>
          <p className="text-sm text-slate-500">Recurring revenue, collections, and receivables.</p>
        </div>
        <button
          onClick={downloadReport}
          disabled={downloading}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60"
        >
          {downloading ? <FileDown className="h-4 w-4 animate-pulse" /> : <Download className="h-4 w-4" />}
          Download report
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {cards.map(({ key, label, money, icon: Icon, color }) => (
          <div key={key} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-500">{label}</p>
              <div className={`grid h-9 w-9 place-items-center rounded-xl ${color}`}>
                <Icon className="h-4 w-4" />
              </div>
            </div>
            <p className="mt-3 text-2xl font-bold text-slate-900">
              {loading ? "—" : money ? formatINR(summary[key]) : summary[key]}
            </p>
            {key === "overdue_amount" && <p className="mt-1 text-xs text-slate-500">{summary.overdue_count} overdue invoices</p>}
          </div>
        ))}
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5">
          <h3 className="font-bold text-slate-900">Monthly collected revenue</h3>
          <p className="text-xs text-slate-500">Based on recorded payment dates · past 12 months</p>
        </div>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="report-revenue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
              <YAxis
                tick={{ fontSize: 12, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value) => `₹${Number(value).toLocaleString("en-IN")}`}
              />
              <Tooltip formatter={(value) => [formatINR(Number(value) * 100), "Collected"]} />
              <Area type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={2.5} fill="url(#report-revenue)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
