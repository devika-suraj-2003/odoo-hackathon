import { useEffect, useMemo, useState, type FormEvent } from "react";
import toast from "react-hot-toast";
import { Plus, Pencil, Trash2, Search, CalendarClock, LoaderCircle } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Modal from "../components/Modal";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { formatINR, toPaise, toRupees } from "../lib/money";

type Period = "daily" | "weekly" | "monthly" | "yearly";
type Plan = {
  id: number;
  name: string;
  price: number;
  billing_period: Period;
  min_qty: number;
  start_date?: string | null;
  end_date?: string | null;
  auto_close: boolean;
  closable: boolean;
  pausable: boolean;
  renewable: boolean;
};

type FormState = {
  name: string;
  price: string;
  billing_period: Period;
  min_qty: string;
  start_date: string;
  end_date: string;
  auto_close: boolean;
  closable: boolean;
  pausable: boolean;
  renewable: boolean;
};

const EMPTY: FormState = {
  name: "",
  price: "",
  billing_period: "monthly",
  min_qty: "1",
  start_date: "",
  end_date: "",
  auto_close: false,
  closable: true,
  pausable: true,
  renewable: true,
};

const PERIODS: Period[] = ["daily", "weekly", "monthly", "yearly"];
const PERIOD_SHORT: Record<Period, string> = { daily: "day", weekly: "week", monthly: "month", yearly: "year" };

const OPTIONS: { key: "auto_close" | "closable" | "pausable" | "renewable"; label: string; hint: string }[] = [
  { key: "auto_close", label: "Auto-close", hint: "Close automatically at end date" },
  { key: "closable", label: "Closable", hint: "Customer can close it" },
  { key: "pausable", label: "Pausable", hint: "Can be paused and resumed" },
  { key: "renewable", label: "Renewable", hint: "Can be renewed when it ends" },
];

function formatDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export default function Plans() {
  const [items, setItems] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Plan | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/plans");
               setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load plans"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((p) => p.name.toLowerCase().includes(q) || p.billing_period.includes(q));
  }, [items, query]);

  function openNew() {
    setEditing(null);
    setForm(EMPTY);
    setOpen(true);
  }

  function openEdit(p: Plan) {
    setEditing(p);
    setForm({
      name: p.name,
      price: toRupees(p.price),
      billing_period: p.billing_period,
      min_qty: String(p.min_qty ?? 1),
      start_date: p.start_date ?? "",
      end_date: p.end_date ?? "",
      auto_close: p.auto_close,
      closable: p.closable,
      pausable: p.pausable,
      renewable: p.renewable,
    });
    setOpen(true);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      toast.error("End date must be after start date");
      return;
    }
    const body = {
      name: form.name.trim(),
      price: toPaise(form.price),
      billing_period: form.billing_period,
      min_qty: Math.max(1, parseInt(form.min_qty) || 1),
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      auto_close: form.auto_close,
      closable: form.closable,
      pausable: form.pausable,
      renewable: form.renewable,
    };
    setSaving(true);
    try {
      if (editing) await api.put(`/plans/${editing.id}`, body);
      else await api.post("/plans", body);
      toast.success(editing ? "Plan updated" : "Plan created");
      setOpen(false);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save plan"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(p: Plan) {
    if (!confirm(`Delete plan "${p.name}"?`)) return;
    try {
      await api.delete(`/plans/${p.id}`);
      toast.success("Plan deleted");
      setItems((list) => list.filter((x) => x.id !== p.id));
    } catch (err) {
      toast.error(errorMessage(err, "Could not delete plan"));
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search plans..."
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
          />
        </div>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700">
          <Plus className="h-4 w-4" /> New plan
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3">Plan</th>
              <th className="px-5 py-3 text-right">Price</th>
              <th className="px-5 py-3 text-center">Min qty</th>
              <th className="px-5 py-3">Valid</th>
              <th className="px-5 py-3">Options</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading &&
              [1, 2, 3].map((i) => (
                <tr key={i}>
                  <td colSpan={6} className="px-5 py-4">
                    <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
                  </td>
                </tr>
              ))}

            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-16 text-center">
                  <CalendarClock className="mx-auto h-10 w-10 text-slate-300" />
                  <p className="mt-3 font-semibold text-slate-700">No plans yet</p>
                  <p className="text-sm text-slate-500">Create a plan to set prices and billing periods.</p>
                </td>
              </tr>
            )}

            {!loading &&
              filtered.map((p) => (
                <tr key={p.id} className="transition hover:bg-slate-50/70">
                  <td className="px-5 py-4">
                    <p className="font-semibold text-slate-900">{p.name}</p>
                    <span className="mt-1 inline-block rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium capitalize text-indigo-700">
                      {p.billing_period}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <span className="font-semibold text-slate-900">{formatINR(p.price)}</span>
                    <span className="text-xs text-slate-500"> / {PERIOD_SHORT[p.billing_period] ?? p.billing_period}</span>
                  </td>
                  <td className="px-5 py-4 text-center text-slate-700">{p.min_qty}</td>
                  <td className="px-5 py-4 text-xs text-slate-600">
                    {formatDate(p.start_date)} → {formatDate(p.end_date)}
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex flex-wrap gap-1.5">
                      {OPTIONS.map((o) => (
                        <span
                          key={o.key}
                          className={`rounded-lg px-2 py-0.5 text-xs font-medium ${
                            p[o.key] ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-400 line-through"
                          }`}
                        >
                          {o.label}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex justify-end gap-1">
                      <button onClick={() => openEdit(p)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-indigo-600" title="Edit">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => handleDelete(p)} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600" title="Delete">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <Modal open={open} title={editing ? "Edit plan" : "New plan"} onClose={() => setOpen(false)} wide>
        <form onSubmit={handleSave} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className={labelCls}>Plan name</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Monthly Pro" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Price (₹)</label>
              <input required type="number" min="0" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="0.00" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Billing period</label>
              <select value={form.billing_period} onChange={(e) => setForm({ ...form, billing_period: e.target.value as Period })} className={inputCls}>
                {PERIODS.map((p) => (
                  <option key={p} value={p}>
                    {p[0].toUpperCase() + p.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>Minimum quantity</label>
              <input type="number" min="1" value={form.min_qty} onChange={(e) => setForm({ ...form, min_qty: e.target.value })} className={inputCls} />
            </div>
            <div />
            <div>
              <label className={labelCls}>Start date</label>
              <input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>End date</label>
              <input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} className={inputCls} />
            </div>
          </div>

          <div>
            <label className={labelCls}>Options</label>
            <div className="grid gap-2 sm:grid-cols-2">
              {OPTIONS.map((o) => (
                <label
                  key={o.key}
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
                    form[o.key] ? "border-indigo-300 bg-indigo-50/60" : "border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={form[o.key]}
                    onChange={(e) => setForm({ ...form, [o.key]: e.target.checked })}
                    className="mt-0.5 h-4 w-4 accent-indigo-600"
                  />
                  <span>
                    <span className="block text-sm font-semibold text-slate-800">{o.label}</span>
                    <span className="block text-xs text-slate-500">{o.hint}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => setOpen(false)} className={btnSecondary}>
              Cancel
            </button>
            <button type="submit" disabled={saving} className={`${btnPrimary.replace("w-full", "")}`}>
              {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}
              {editing ? "Save changes" : "Create plan"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}