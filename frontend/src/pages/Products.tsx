import { useEffect, useMemo, useState, type FormEvent } from "react";
import toast from "react-hot-toast";
import { Plus, Pencil, Trash2, Search, Package, LoaderCircle, X } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Modal from "../components/Modal";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { formatINR, toPaise, toRupees } from "../lib/money";

type Variant = { id?: number; attribute: string; value: string; extra_price: number };
type Product = {
  id: number;
  name: string;
  type: string;
  sales_price: number;
  cost_price: number;
  notes?: string | null;
  variants: Variant[];
};

type VariantForm = { attribute: string; value: string; extra: string };
type FormState = { name: string; type: string; sales: string; cost: string; notes: string; variants: VariantForm[] };

const EMPTY: FormState = { name: "", type: "service", sales: "", cost: "", notes: "", variants: [] };
const TYPES = ["service", "goods"];

export default function Products() {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/products");
               setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load products"));
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
    return items.filter((p) => p.name.toLowerCase().includes(q) || p.type.toLowerCase().includes(q));
  }, [items, query]);

  function openNew() {
    setEditing(null);
    setForm(EMPTY);
    setOpen(true);
  }

  function openEdit(p: Product) {
    setEditing(p);
    setForm({
      name: p.name,
      type: p.type,
      sales: toRupees(p.sales_price),
      cost: toRupees(p.cost_price),
      notes: p.notes ?? "",
      variants: (p.variants ?? []).map((v) => ({ attribute: v.attribute, value: v.value, extra: toRupees(v.extra_price) })),
    });
    setOpen(true);
  }

  function setVariant(i: number, key: keyof VariantForm, value: string) {
    setForm((f) => ({ ...f, variants: f.variants.map((v, idx) => (idx === i ? { ...v, [key]: value } : v)) }));
  }

  function addVariant() {
    setForm((f) => ({ ...f, variants: [...f.variants, { attribute: "", value: "", extra: "" }] }));
  }

  function removeVariant(i: number) {
    setForm((f) => ({ ...f, variants: f.variants.filter((_, idx) => idx !== i) }));
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    const body = {
      name: form.name.trim(),
      type: form.type,
      sales_price: toPaise(form.sales),
      cost_price: toPaise(form.cost),
      notes: form.notes.trim() || null,
      variants: form.variants
        .filter((v) => v.attribute.trim() && v.value.trim())
        .map((v) => ({ attribute: v.attribute.trim(), value: v.value.trim(), extra_price: toPaise(v.extra) })),
    };
    setSaving(true);
    try {
      if (editing) await api.put(`/products/${editing.id}`, body);
      else await api.post("/products", body);
      toast.success(editing ? "Product updated" : "Product created");
      setOpen(false);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save product"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(p: Product) {
    if (!confirm(`Delete "${p.name}"?`)) return;
    try {
      await api.delete(`/products/${p.id}`);
      toast.success("Product deleted");
      setItems((list) => list.filter((x) => x.id !== p.id));
    } catch (err) {
      toast.error(errorMessage(err, "Could not delete product"));
    }
  }

  function margin(p: Product) {
    if (!p.sales_price) return 0;
    return Math.round(((p.sales_price - p.cost_price) / p.sales_price) * 100);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search products..."
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
          />
        </div>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700">
          <Plus className="h-4 w-4" /> New product
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3">Product</th>
              <th className="px-5 py-3">Type</th>
              <th className="px-5 py-3 text-right">Sales price</th>
              <th className="px-5 py-3 text-right">Cost price</th>
              <th className="px-5 py-3 text-right">Margin</th>
              <th className="px-5 py-3">Variants</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading &&
              [1, 2, 3].map((i) => (
                <tr key={i}>
                  <td colSpan={7} className="px-5 py-4">
                    <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
                  </td>
                </tr>
              ))}

            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-16 text-center">
                  <Package className="mx-auto h-10 w-10 text-slate-300" />
                  <p className="mt-3 font-semibold text-slate-700">No products yet</p>
                  <p className="text-sm text-slate-500">Create your first product to start building plans.</p>
                </td>
              </tr>
            )}

            {!loading &&
              filtered.map((p) => (
                <tr key={p.id} className="transition hover:bg-slate-50/70">
                  <td className="px-5 py-4">
                    <p className="font-semibold text-slate-900">{p.name}</p>
                    {p.notes && <p className="mt-0.5 max-w-xs truncate text-xs text-slate-500">{p.notes}</p>}
                  </td>
                  <td className="px-5 py-4">
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium capitalize text-slate-700">{p.type}</span>
                  </td>
                  <td className="px-5 py-4 text-right font-semibold text-slate-900">{formatINR(p.sales_price)}</td>
                  <td className="px-5 py-4 text-right text-slate-600">{formatINR(p.cost_price)}</td>
                  <td className="px-5 py-4 text-right">
                    <span className={`font-semibold ${margin(p) >= 0 ? "text-emerald-600" : "text-red-600"}`}>{margin(p)}%</span>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex flex-wrap gap-1.5">
                      {(p.variants ?? []).length === 0 && <span className="text-xs text-slate-400">—</span>}
                      {(p.variants ?? []).map((v, i) => (
                        <span key={v.id ?? i} className="rounded-lg bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                          {v.attribute}: {v.value} +{formatINR(v.extra_price)}
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

      <Modal open={open} title={editing ? "Edit product" : "New product"} onClose={() => setOpen(false)} wide>
        <form onSubmit={handleSave} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className={labelCls}>Name</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Odoo ERP licence" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Type</label>
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className={inputCls}>
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t[0].toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div />
            <div>
              <label className={labelCls}>Sales price (₹)</label>
              <input required type="number" min="0" step="0.01" value={form.sales} onChange={(e) => setForm({ ...form, sales: e.target.value })} placeholder="0.00" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Cost price (₹)</label>
              <input required type="number" min="0" step="0.01" value={form.cost} onChange={(e) => setForm({ ...form, cost: e.target.value })} placeholder="0.00" className={inputCls} />
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Notes</label>
              <textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Optional" className={inputCls} />
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-sm font-medium text-slate-700">Variants</label>
              <button type="button" onClick={addVariant} className="inline-flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-700">
                <Plus className="h-4 w-4" /> Add variant
              </button>
            </div>
            {form.variants.length === 0 && (
              <p className="rounded-xl border border-dashed border-slate-300 p-4 text-center text-xs text-slate-500">
                No variants. Example: Brand = Odoo, extra price ₹560.
              </p>
            )}
            <div className="space-y-2">
              {form.variants.map((v, i) => (
                <div key={i} className="grid grid-cols-[1fr_1fr_8rem_auto] items-center gap-2">
                  <input value={v.attribute} onChange={(e) => setVariant(i, "attribute", e.target.value)} placeholder="Attribute (Brand)" className={inputCls} />
                  <input value={v.value} onChange={(e) => setVariant(i, "value", e.target.value)} placeholder="Value (Odoo)" className={inputCls} />
                  <input type="number" min="0" step="0.01" value={v.extra} onChange={(e) => setVariant(i, "extra", e.target.value)} placeholder="+ ₹" className={inputCls} />
                  <button type="button" onClick={() => removeVariant(i)} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => setOpen(false)} className={btnSecondary}>
              Cancel
            </button>
            <button type="submit" disabled={saving} className={`${btnPrimary} w-auto`}>
              {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}
              {editing ? "Save changes" : "Create product"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}