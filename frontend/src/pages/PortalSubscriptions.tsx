import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Repeat, CalendarClock } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import StatusBadge from "../components/StatusBadge";
import { formatINR } from "../lib/money";

type Sub = {
  id: number;
  number: string;
  status: string;
  plan?: { id: number; name: string; billing_period: string } | null;
  start_date?: string | null;
  next_billing_date?: string | null;
  lines?: { id: number; product_name: string; quantity: number; amount: number }[];
  total?: number;
};

const fmt = (d?: string | null) => (d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—");

export default function PortalSubscriptions() {
  const [items, setItems] = useState<Sub[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/subscriptions");
        setItems(Array.isArray(data) ? data : []);
      } catch (err) {
        toast.error(errorMessage(err, "Could not load your subscriptions"), { id: "portal-subs" });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[1, 2].map((i) => (
          <div key={i} className="h-56 animate-pulse rounded-2xl bg-slate-100" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-16 text-center">
        <Repeat className="mx-auto h-10 w-10 text-slate-300" />
        <p className="mt-3 font-semibold text-slate-700">You have no subscriptions yet</p>
        <p className="text-sm text-slate-500">When Brightloop sends you a quotation, it will appear here.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-5 md:grid-cols-2">
      {items.map((s) => (
        <div key={s.id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{s.number}</p>
              <h3 className="mt-1 text-lg font-bold text-slate-900">{s.plan?.name ?? "Subscription"}</h3>
            </div>
            <StatusBadge status={s.status} />
          </div>
          <p className="mt-4 text-3xl font-extrabold text-slate-900">
            {formatINR(s.total)}
            <span className="text-sm font-medium text-slate-500"> / {s.plan?.billing_period ?? "period"}</span>
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3 rounded-xl bg-slate-50 p-3 text-sm">
            <div>
              <p className="text-xs text-slate-500">Started</p>
              <p className="font-semibold text-slate-800">{fmt(s.start_date)}</p>
            </div>
            <div>
              <p className="flex items-center gap-1 text-xs text-slate-500">
                <CalendarClock className="h-3 w-3" /> Next bill
              </p>
              <p className="font-semibold text-indigo-600">{fmt(s.next_billing_date)}</p>
            </div>
          </div>
          {(s.lines ?? []).length > 0 && (
            <ul className="mt-4 space-y-1.5 text-sm">
              {(s.lines ?? []).map((l) => (
                <li key={l.id} className="flex justify-between text-slate-600">
                  <span>
                    {l.product_name} × {l.quantity}
                  </span>
                  <span className="font-medium text-slate-800">{formatINR(l.amount)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}