import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Plus, Search, Repeat, LoaderCircle, X } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Modal from "../components/Modal";
import StatusBadge from "../components/StatusBadge";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { formatINR, toPaise, toRupees } from "../lib/money";

type Status = "draft" | "quotation" | "confirmed" | "active" | "paused" | "closed";
type Subscription = {
  id: number;
  number: string;
  customer?: { id: number; name: string; email?: string } | null;
  plan?: { id: number; name: string; billing_period: string } | null;
  status: Status;
  start_date?: string | null;
  expiry_date?: string | null;
  next_billing_date?: string | null;
  total?: number;
};

type Customer = { id: number; name: string; email?: string };
type Variant = { id: number; attribute: string; value: string; extra_price: number };
type Product = { id: number; name: string; sales_price: number; variants?: Variant[] };
type Plan = { id: number; name: string; price: number; billing_period: string };
type TemplateLine = { product_id: number; variant_id?: number | null; quantity: number; unit_price?: number };
type Template = { id: number; name: string; plan_id?: number | null; lines?: TemplateLine[] };

type LineForm = { product_id: string; variant_id: string; quantity: string; unit_price: string };
type FormState = {
  customer_id: string;
  plan_id: string;
  template_id: string;
  start_date: string;
  payment_terms: string;
  lines: LineForm[];
};

const today = () => new Date().toISOString().slice(0, 10);
const EMPTY_LINE: LineForm = { product_id: "", variant_id: "", quantity: "1", unit_price: "" };
const emptyForm = (): FormState => ({
  customer_id: "",
  plan_id: "",
  template_id: "",
  start_date: today(),
  payment_terms: "immediate",
  lines: [{ ...EMPTY_LINE }],
});

const TABS: ("all" | Status)[] = ["all", "draft", "quotation", "confirmed", "active", "paused", "closed"];
const TERMS = [
  { value: "immediate", label: "Immediate payment" },
  { value: "15_days", label: "15 days" },
  { value: "30_days", label: "30 days" },
  { value: "end_of_month", label: "End of month" },
];

function formatDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export default function Subscriptions() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"all" | Status>("all");
  const [query, setQuery] = useState("");

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/subscriptions");
         setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load subscriptions"), { id: "subs-load" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function loadLookups() {
    const [c, p, pl, t] = await Promise.allSettled([
      api.get("/users", { params: { role: "customer" } }),
      api.get("/products"),
      api.get("/plans"),
      api.get("/templates"),
    ]);
    const list = (r: any) => (r.status === "fulfilled" && Array.isArray(r.value.data) ? r.value.data : []);
    setCustomers(list(c));
    setProducts(list(p));
    setPlans(list(pl));
    setTemplates(list(t));
    if ([c, p, pl, t].every((r) => r.status === "rejected")) {
      toast.error("Could not load customers, products or plans", { id: "subs-lookups" });
    }
  }

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    for (const s of items) c[s.status] = (c[s.status] ?? 0) + 1;
    return c;
  }, [items]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((s) => {
      if (tab !== "all" && s.status !== tab) return false;
      if (!q) return true;
      return (
        s.number?.toLowerCase().includes(q) ||
        s.customer?.name?.toLowerCase().includes(q) ||
        s.plan?.name?.toLowerCase().includes(q)
      );
    });
  }, [items, tab, query]);

  function openNew() {
    setForm(emptyForm());
    setOpen(true);
    loadLookups();
  }

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

  function addLine() {
    setForm((f) => ({ ...f, lines: [...f.lines, { ...EMPTY_LINE }] }));
  }

  function removeLine(i: number) {
    setForm((f) => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }));
  }

  function applyTemplate(id: string) {
    const t = templates.find((x) => String(x.id) === id);
    if (!t) {
      setForm((f) => ({ ...f, template_id: "" }));
      return;
    }
    setForm((f) => ({
      ...f,
      template_id: id,
      plan_id: t.plan_id ? String(t.plan_id) : f.plan_id,
      lines:
        t.lines && t.lines.length > 0
          ? t.lines.map((l) => ({
              product_id: String(l.product_id),
              variant_id: l.variant_id ? String(l.variant_id) : "",
              quantity: String(l.quantity ?? 1),
              unit_price:
                l.unit_price != null
                  ? toRupees(l.unit_price) || "0"
                  : priceFor(String(l.product_id), l.variant_id ? String(l.variant_id) : ""),
            }))
          : f.lines,
    }));
  }

  function lineAmount(l: LineForm) {
    return toPaise(l.unit_price) * Math.max(0, parseInt(l.quantity) || 0);
  }

  const subtotal = form.lines.reduce((sum, l) => sum + lineAmount(l), 0);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    const lines = form.lines.filter((l) => l.product_id);
    if (!form.customer_id) return toast.error("Please choose a customer");
    if (!form.plan_id) return toast.error("Please choose a plan");
    if (lines.length === 0) return toast.error("Add at least one product line");

    const body = {
      customer_id: Number(form.customer_id),
      plan_id: Number(form.plan_id),
      template_id: form.template_id ? Number(form.template_id) : null,
      start_date: form.start_date,
      payment_terms: form.payment_terms,
      lines: lines.map((l) => ({
        product_id: Number(l.product_id),
        variant_id: l.variant_id ? Number(l.variant_id) : null,
        quantity: Math.max(1, parseInt(l.quantity) || 1),
        unit_price: toPaise(l.unit_price),
      })),
    };

    setSaving(true);
    try {
      const { data } = await api.post("/subscriptions", body);
      toast.success(`Subscription ${data?.number ?? ""} created`);
      setOpen(false);
      if (data?.id) navigate(`/subscriptions/${data.id}`);
      else load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not create subscription"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
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
            <span className={`rounded-md px-1.5 text-xs ${tab === t ? "bg-white/20" : "bg-slate-100 text-slate-500"}`}>
              {counts[t] ?? 0}
            </span>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by number, customer or plan..."
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
          />
        </div>
        <button onClick={openNew} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700">
          <Plus className="h-4 w-4" /> New subscription
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3">Number</th>
              <th className="px-5 py-3">Customer</th>
              <th className="px-5 py-3">Plan</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Start</th>
              <th className="px-5 py-3">Next billing</th>
              <th className="px-5 py-3 text-right">Total</th>
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
                  <Repeat className="mx-auto h-10 w-10 text-slate-300" />
                  <p className="mt-3 font-semibold text-slate-700">No subscriptions here</p>
                  <p className="text-sm text-slate-500">Create a subscription from a plan or a quotation template.</p>
                </td>
              </tr>
            )}

            {!loading &&
              filtered.map((s) => (
                <tr key={s.id} onClick={() => navigate(`/subscriptions/${s.id}`)} className="cursor-pointer transition hover:bg-slate-50/70">
                  <td className="px-5 py-4 font-semibold text-indigo-600">{s.number}</td>
                  <td className="px-5 py-4">
                    <p className="font-medium text-slate-900">{s.customer?.name ?? "—"}</p>
                    {s.customer?.email && <p className="text-xs text-slate-500">{s.customer.email}</p>}
                  </td>
                  <td className="px-5 py-4">
                    <p className="text-slate-800">{s.plan?.name ?? "—"}</p>
                    {s.plan?.billing_period && <p className="text-xs capitalize text-slate-500">{s.plan.billing_period}</p>}
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={s.status} />
                  </td>
                  <td className="px-5 py-4 text-slate-600">{formatDate(s.start_date)}</td>
                  <td className="px-5 py-4 text-slate-600">{formatDate(s.next_billing_date)}</td>
                  <td className="px-5 py-4 text-right font-semibold text-slate-900">{formatINR(s.total)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <Modal open={open} title="New subscription" onClose={() => setOpen(false)} wide>
        <form onSubmit={handleSave} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Customer</label>
              <select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} className={inputCls}>
                <option value="">Select customer</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                    {c.email ? ` (${c.email})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelCls}>Quotation template (optional)</label>
              <select value={form.template_id} onChange={(e) => applyTemplate(e.target.value)} className={inputCls}>
                <option value="">No template</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
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
              <label className={labelCls}>Start date</label>
              <input required type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Payment terms</label>
              <select value={form.payment_terms} onChange={(e) => setForm({ ...form, payment_terms: e.target.value })} className={inputCls}>
                {TERMS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-sm font-medium text-slate-700">Order lines</label>
              <button type="button" onClick={addLine} className="inline-flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-700">
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
                const product = products.find((p) => String(p.id) === l.product_id);
                const variants = product?.variants ?? [];
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
                      onClick={() => removeLine(i)}
                      disabled={form.lines.length === 1}
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
              <p className="text-xs text-slate-500">Taxes and discounts are applied automatically on the invoice.</p>
              <p className="text-sm">
                <span className="text-slate-500">Subtotal </span>
                <span className="font-bold text-slate-900">{formatINR(subtotal)}</span>
              </p>
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => setOpen(false)} className={btnSecondary}>
              Cancel
            </button>
            <button type="submit" disabled={saving} className={`${btnPrimary.replace("w-full", "")}`}>
              {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}
              Create subscription
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}