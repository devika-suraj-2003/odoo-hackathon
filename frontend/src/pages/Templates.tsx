import { useEffect, useState, type FormEvent } from "react";
import toast from "react-hot-toast";
import { Plus, Pencil, Trash2, FileStack, LoaderCircle, X } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Modal from "../components/Modal";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { formatINR, toPaise, toRupees } from "../lib/money";

type Variant = { id: number; attribute: string; value: string; extra_price: number };
type Product = { id: number; name: string; sales_price: number; variants?: Variant[] };
type Plan = { id: number; name: string; price: number; billing_period: string };
type TLine = { product_id: number; variant_id?: number | null; quantity: number; unit_price: number; product_name?: string };
type Template = { id: number; name: string; plan_id?: number | null; validity_days: number; lines?: TLine[] };
type LineForm = { product_id: string; variant_id: string; quantity: string; unit_price: string };

const EMPTY_LINE: LineForm = { product_id: "", variant_id: "", quantity: "1", unit_price: "" };
const emptyForm = () => ({ name: "", plan_id: "", validity_days: "30", lines: [{ ...EMPTY_LINE }] });
const list = (r: PromiseSettledResult<any>) => (r.status === "fulfilled" && Array.isArray(r.value.data) ? r.value.data : []);

export default function Templates() {
  const [items, setItems] = useState<Template[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Template | null>(null);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    const [t, p, pl] = await Promise.allSettled([api.get("/templates"), api.get("/products"), api.get("/plans")]);
    setItems(list(t));
    setProducts(list(p));
    setPlans(list(pl));
    if (t.status === "rejected") toast.error(errorMessage(t.reason, "Could not load templates"), { id: "tpl-load" });
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  function priceFor(productId: string, variantId: string) {
    const product = products.find((p) => String(p.id) === productId);
    if (!product) return "";
    const variant = product.variants?.find((v) => String(v.id) === variantId);
    return toRupees(product.sales_price + (variant?.extra_price ?? 0)) || "0";
  }

  function setLine(i: number, key: keyof LineForm, value: string) {
    setForm((f) => ({
      ...f,
      lines: f.lines.map((l, idx) => {
        if (idx !== i) return l;
        if (key === "product_id") return { ...l, product_id: value, variant_id: "", unit_price: priceFor(value, "") };
        if (key === "variant_id") return { ...l, variant_id: value, unit_price: priceFor(l.product_id, value) };
        return { ...l, [key]: value };
      }),
    }));
  }

  function openNew() {
    setEditing(null);
    setForm(emptyForm());
    setOpen(true);
  }

  function openEdit(t: Template) {
    setEditing(t);
    setForm({
      name: t.name,
      plan_id: t.plan_id ? String(t.plan_id) : "",
      validity_days: String(t.validity_days ?? 30),
      lines:
        (t.lines ?? []).length > 0
          ? (t.lines ?? []).map((l) => ({
              product_id: String(l.product_id),
              variant_id: l.variant_id ? String(l.variant_id) : "",
              quantity: String(l.quantity),
              unit_price: toRupees(l.unit_price) || "0",
            }))
          : [{ ...EMPTY_LINE }],
    });
    setOpen(true);
  }

  const lineAmount = (l: LineForm) => toPaise(l.unit_price) * Math.max(0, parseInt(l.quantity) || 0);
  const subtotal = form.lines.reduce((s, l) => s + lineAmount(l), 0);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    const lines = form.lines.filter((l) => l.product_id);
    if (!form.plan_id) return toast.error("Choose a plan");
    if (lines.length === 0) return toast.error("Add at least one product line");
    const days = parseInt(form.validity_days);
    if (!days || days < 1) return toast.error("Validity must be at least 1 day");

    const body = {
      name: form.name.trim(),
      plan_id: Number(form.plan_id),
      validity_days: days,
      lines: lines.map((l) => ({
        product_id: Number(l.product_id),
        variant_id: l.variant_id ? Number(l.variant_id) : null,
        quantity: Math.max(1, parseInt(l.quantity) || 1),
        unit_price: toPaise(l.unit_price),
      })),
    };
    setSaving(true);
    try {
      if (editing) await api.put(`/templates/${editing.id}`, body);
      else await api.post("/templates", body);
      toast.success(editing ? "Template updated" : "Template created");
      setOpen(false);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save template"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(t: Template) {
    if (!confirm(`Delete template "${t.name}"?`)) return;
    try {
      await api.delete(`/templates/${t.id}`);
      toast.success("Template deleted");
      setItems((x) => x.filter((i) => i.id !== t.id));
    } catch (err) {
      toast.error(errorMessage(err, "Could not delete template"));
    }
  }

  const planName = (id?: number | null) => plans.find((p) => p.id === id)?.name ?? "—";
  const productName = (id: number) => products.find((p) => p.id === id)?.name ?? `Product #${id}`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-slate-500">Reusable quotations: pick a template when creating a subscription and the plan and lines fill in automatically.</p>
        <button onClick={openNew} className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700">
          <Plus className="h-4 w-4" /> New template
        </button>
      </div>

      {!loading && items.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-14 text-center">
          <FileStack className="mx-auto h-10 w-10 text-slate-300" />
          <p className="mt-3 font-semibold text-slate-700">No quotation templates yet</p>
          <p className="text-sm text-slate-500">Example: "Starter pack" = Monthly plan + Odoo licence × 5.</p>
        </div>
      )}

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {items.map((t) => {
          const total = (t.lines ?? []).reduce((s, l) => s + l.unit_price * l.quantity, 0);
          return (
            <div key={t.id} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-bold text-slate-900">{t.name}</h3>
                  <p className="text-xs text-slate-500">
                    {planName(t.plan_id)} · valid {t.validity_days} days
                  </p>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(t)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-indigo-600">
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button onClick={() => handleDelete(t)} className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <ul className="mt-4 flex-1 space-y-1.5 text-sm">
                {(t.lines ?? []).map((l, i) => (
                  <li key={i} className="flex justify-between text-slate-600">
                    <span>
                      {l.product_name ?? productName(l.product_id)} × {l.quantity}
                    </span>
                    <span className="font-medium text-slate-800">{formatINR(l.unit_price * l.quantity)}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex justify-between border-t border-slate-100 pt-3 text-sm font-bold text-slate-900">
                <span>Subtotal</span>
                <span>{formatINR(total)}</span>
              </div>
            </div>
          );
        })}
      </div>

      <Modal open={open} title={editing ? "Edit template" : "New quotation template"} onClose={() => setOpen(false)} wide>
        <form onSubmit={handleSave} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="sm:col-span-3">
              <label className={labelCls}>Template name</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Starter pack" className={inputCls} />
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Plan</label>
              <select value={form.plan_id} onChange={(e) => setForm({ ...form, plan_id: e.target.value })} className={inputCls}>
                <option value="">Select plan</option>
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} · {formatINR(p.price)} / {p.billing_period}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>Valid for (days)</label>
              <input type="number" min="1" value={form.validity_days} onChange={(e) => setForm({ ...form, validity_days: e.target.value })} className={inputCls} />
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-sm font-medium text-slate-700">Product lines</label>
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, lines: [...f.lines, { ...EMPTY_LINE }] }))}
                className="inline-flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-700"
              >
                <Plus className="h-4 w-4" /> Add line
              </button>
            </div>
            <div className="grid grid-cols-[2fr_1.5fr_4.5rem_6.5rem_6rem_2rem] gap-2 px-1 pb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <span>Product</span>
              <span>Variant</span>
              <span>Qty</span>
              <span>Unit ₹</span>
              <span className="text-right">Amount</span>
              <span />
            </div>
            <div className="space-y-2">
              {form.lines.map((l, i) => {
                const variants = products.find((p) => String(p.id) === l.product_id)?.variants ?? [];
                return (
                  <div key={i} className="grid grid-cols-[2fr_1.5fr_4.5rem_6.5rem_6rem_2rem] items-center gap-2">
                    <select value={l.product_id} onChange={(e) => setLine(i, "product_id", e.target.value)} className={inputCls}>
                      <option value="">Select</option>
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                    <select
                      value={l.variant_id}
                      onChange={(e) => setLine(i, "variant_id", e.target.value)}
                      disabled={variants.length === 0}
                      className={`${inputCls} disabled:bg-slate-50 disabled:text-slate-400`}
                    >
                      <option value="">{variants.length ? "Standard" : "—"}</option>
                      {variants.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.value} (+{formatINR(v.extra_price)})
                        </option>
                      ))}
                    </select>
                    <input type="number" min="1" value={l.quantity} onChange={(e) => setLine(i, "quantity", e.target.value)} className={inputCls} />
                    <input type="number" min="0" step="0.01" value={l.unit_price} onChange={(e) => setLine(i, "unit_price", e.target.value)} className={inputCls} />
                    <span className="text-right text-sm font-semibold text-slate-800">{formatINR(lineAmount(l))}</span>
                    <button
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }))}
                      disabled={form.lines.length === 1}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 flex justify-end rounded-xl bg-slate-50 px-4 py-3 text-sm">
              <span className="text-slate-500">Subtotal&nbsp;</span>
              <span className="font-bold text-slate-900">{formatINR(subtotal)}</span>
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => setOpen(false)} className={btnSecondary}>
              Cancel
            </button>
            <button type="submit" disabled={saving} className={`${btnPrimary.replace("w-full", "")}`}>
              {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}
              Save template
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}