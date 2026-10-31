import { useEffect, useState, type FormEvent } from "react";
import toast from "react-hot-toast";
import { Plus, Pencil, Trash2, BadgePercent, LoaderCircle } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Modal from "../components/Modal";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { formatINR, toPaise, toRupees } from "../lib/money";

type Discount = {
  id: number;
  name: string;
  discount_type: "percent" | "fixed";
  value: number;
  min_purchase?: number | null;
  min_qty?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  usage_limit?: number | null;
  used_count?: number;
  applies_to: "subscription" | "products";
  product_ids?: number[];
  active?: boolean;
};
type Product = { id: number; name: string };

const today = () => new Date().toISOString().slice(0, 10);
const EMPTY = {
  name: "",
  discount_type: "percent" as "percent" | "fixed",
  value: "10",
  min_purchase: "",
  min_qty: "",
  start_date: today(),
  end_date: "",
  usage_limit: "",
  applies_to: "subscription" as "subscription" | "products",
  product_ids: [] as number[],
  active: true,
};

function statusOf(d: Discount) {
  const t = today();
  if (d.active === false) return { label: "Inactive", cls: "bg-slate-100 text-slate-500" };
  if (d.start_date && d.start_date > t) return { label: "Scheduled", cls: "bg-sky-50 text-sky-700" };
  if (d.end_date && d.end_date < t) return { label: "Expired", cls: "bg-slate-100 text-slate-500" };
  if (d.usage_limit && (d.used_count ?? 0) >= d.usage_limit) return { label: "Used up", cls: "bg-amber-50 text-amber-700" };
  return { label: "Active", cls: "bg-emerald-50 text-emerald-700" };
}

const fmt = (d?: string | null) => (d ? new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }) : "—");

export default function Discounts() {
  const [items, setItems] = useState<Discount[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Discount | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    const [d, p] = await Promise.allSettled([api.get("/discounts"), api.get("/products")]);
    setItems(d.status === "fulfilled" && Array.isArray(d.value.data) ? d.value.data : []);
    setProducts(p.status === "fulfilled" && Array.isArray(p.value.data) ? p.value.data : []);
    if (d.status === "rejected") toast.error(errorMessage(d.reason, "Could not load discounts"), { id: "disc-load" });
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  function openNew() {
    setEditing(null);
    setForm({ ...EMPTY, start_date: today() });
    setOpen(true);
  }

  function openEdit(d: Discount) {
    setEditing(d);
    setForm({
      name: d.name,
      discount_type: d.discount_type,
      value: d.discount_type === "fixed" ? toRupees(d.value) : String(d.value),
      min_purchase: d.min_purchase ? toRupees(d.min_purchase) : "",
      min_qty: d.min_qty ? String(d.min_qty) : "",
      start_date: d.start_date ?? "",
      end_date: d.end_date ?? "",
      usage_limit: d.usage_limit ? String(d.usage_limit) : "",
      applies_to: d.applies_to,
      product_ids: d.product_ids ?? [],
      active: d.active !== false,
    });
    setOpen(true);
  }

  function toggleProduct(id: number) {
    setForm((f) => ({ ...f, product_ids: f.product_ids.includes(id) ? f.product_ids.filter((x) => x !== id) : [...f.product_ids, id] }));
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    const num = parseFloat(form.value);
    if (!Number.isFinite(num) || num <= 0) return toast.error("Enter a discount value");
    if (form.discount_type === "percent" && num > 100) return toast.error("Percentage cannot be more than 100");
    if (form.end_date && form.start_date && form.end_date < form.start_date) return toast.error("End date must be after start date");
    if (form.applies_to === "products" && form.product_ids.length === 0) return toast.error("Pick at least one product");

    const body = {
      name: form.name.trim(),
      discount_type: form.discount_type,
      value: form.discount_type === "fixed" ? toPaise(num) : num,
      min_purchase: form.min_purchase ? toPaise(form.min_purchase) : null,
      min_qty: form.min_qty ? parseInt(form.min_qty) : null,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      usage_limit: form.usage_limit ? parseInt(form.usage_limit) : null,
      applies_to: form.applies_to,
      product_ids: form.applies_to === "products" ? form.product_ids : [],
      active: form.active,
    };
    setSaving(true);
    try {
      if (editing) await api.put(`/discounts/${editing.id}`, body);
      else await api.post("/discounts", body);
      toast.success(editing ? "Discount updated" : "Discount created");
      setOpen(false);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save discount"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(d: Discount) {
    if (!confirm(`Delete discount "${d.name}"?`)) return;
    try {
      await api.delete(`/discounts/${d.id}`);
      toast.success("Discount deleted");
      setItems((list) => list.filter((x) => x.id !== d.id));
    } catch (err) {
      toast.error(errorMessage(err, "Could not delete discount"));
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Discounts apply automatically and stop when expired or used up. Only admins can manage them.</p>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700">
          <Plus className="h-4 w-4" /> New discount
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3">Discount</th>
              <th className="px-5 py-3">Value</th>
              <th className="px-5 py-3">Conditions</th>
              <th className="px-5 py-3">Valid</th>
              <th className="px-5 py-3">Usage</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-14 text-center">
                  <BadgePercent className="mx-auto h-10 w-10 text-slate-300" />
                  <p className="mt-3 font-semibold text-slate-700">No discounts yet</p>
                  <p className="text-sm text-slate-500">Example: 10% off for orders above ₹5,000.</p>
                </td>
              </tr>
            )}
            {items.map((d) => {
              const st = statusOf(d);
              const used = d.used_count ?? 0;
              const pct = d.usage_limit ? Math.min(100, Math.round((used / d.usage_limit) * 100)) : 0;
              return (
                <tr key={d.id} className="transition hover:bg-slate-50/70">
                  <td className="px-5 py-4">
                    <p className="font-semibold text-slate-900">{d.name}</p>
                    <p className="text-xs text-slate-500">{d.applies_to === "products" ? `${d.product_ids?.length ?? 0} products` : "Whole subscription"}</p>
                  </td>
                  <td className="px-5 py-4 font-bold text-indigo-600">{d.discount_type === "percent" ? `${d.value}%` : formatINR(d.value)}</td>
                  <td className="px-5 py-4 text-xs text-slate-600">
                    {d.min_purchase ? <p>Min ₹ {formatINR(d.min_purchase).replace("₹", "")}</p> : null}
                    {d.min_qty ? <p>Min qty {d.min_qty}</p> : null}
                    {!d.min_purchase && !d.min_qty && "—"}
                  </td>
                  <td className="px-5 py-4 text-xs text-slate-600">
                    {fmt(d.start_date)} → {fmt(d.end_date)}
                  </td>
                  <td className="px-5 py-4">
                    <p className="text-xs text-slate-600">
                      {used} / {d.usage_limit ?? "∞"}
                    </p>
                    {d.usage_limit ? (
                      <div className="mt-1 h-1.5 w-24 overflow-hidden rounded-full bg-slate-100">
                        <div className={`h-full rounded-full ${pct >= 100 ? "bg-amber-500" : "bg-indigo-500"}`} style={{ width: `${pct}%` }} />
                      </div>
                    ) : null}
                  </td>
                  <td className="px-5 py-4">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${st.cls}`}>{st.label}</span>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex justify-end gap-1">
                      <button onClick={() => openEdit(d)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-indigo-600">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => handleDelete(d)} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Modal open={open} title={editing ? "Edit discount" : "New discount"} onClose={() => setOpen(false)} wide>
        <form onSubmit={handleSave} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="sm:col-span-3">
              <label className={labelCls}>Name</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Festive 10% off" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Type</label>
              <select value={form.discount_type} onChange={(e) => setForm({ ...form, discount_type: e.target.value as "percent" | "fixed" })} className={inputCls}>
                <option value="percent">Percentage (%)</option>
                <option value="fixed">Fixed amount (₹)</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>{form.discount_type === "percent" ? "Percent off" : "Amount off (₹)"}</label>
              <input required type="number" min="0" step="0.01" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Usage limit</label>
              <input type="number" min="1" value={form.usage_limit} onChange={(e) => setForm({ ...form, usage_limit: e.target.value })} placeholder="Unlimited" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Min purchase (₹)</label>
              <input type="number" min="0" step="0.01" value={form.min_purchase} onChange={(e) => setForm({ ...form, min_purchase: e.target.value })} placeholder="None" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Start date</label>
              <input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>End date</label>
              <input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Min quantity</label>
              <input type="number" min="1" value={form.min_qty} onChange={(e) => setForm({ ...form, min_qty: e.target.value })} placeholder="None" className={inputCls} />
            </div>
          </div>

          <div>
            <label className={labelCls}>Applies to</label>
            <div className="grid grid-cols-2 gap-2">
              {(["subscription", "products"] as const).map((a) => (
                <button
                  type="button"
                  key={a}
                  onClick={() => setForm({ ...form, applies_to: a })}
                  className={`rounded-xl border p-3 text-left text-sm font-semibold transition ${
                    form.applies_to === a ? "border-indigo-400 bg-indigo-50 text-indigo-700" : "border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {a === "subscription" ? "Whole subscription" : "Specific products"}
                </button>
              ))}
            </div>
            {form.applies_to === "products" && (
              <div className="mt-3 flex flex-wrap gap-2">
                {products.length === 0 && <p className="text-xs text-slate-500">No products yet.</p>}
                {products.map((p) => (
                  <button
                    type="button"
                    key={p.id}
                    onClick={() => toggleProduct(p.id)}
                    className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 transition ${
                      form.product_ids.includes(p.id) ? "bg-indigo-600 text-white ring-indigo-600" : "bg-white text-slate-600 ring-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} className="h-4 w-4 accent-indigo-600" />
            Active
          </label>

          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => setOpen(false)} className={btnSecondary}>
              Cancel
            </button>
            <button type="submit" disabled={saving} className={`${btnPrimary.replace("w-full", "")}`}>
              {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}
              Save
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}