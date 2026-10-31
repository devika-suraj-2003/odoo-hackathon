import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Plus, Search, Repeat, LoaderCircle, X, List, LayoutGrid, ArrowRight, Pencil, Trash2 } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Modal from "../components/Modal";
import StatusBadge from "../components/StatusBadge";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { formatINR, toPaise, toRupees } from "../lib/money";
import { useAuth } from "../context/AuthContext";

type Status = "draft" | "quotation" | "confirmed" | "active" | "paused" | "closed";
type Subscription = {
  id: number;
  number: string;
  customer?: { id: number; name: string; email?: string } | null;
  plan?: { id: number; name: string; billing_period: string } | null;
  status: Status;
  start_date?: string | null;
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
type FormState = { customer_id: string; plan_id: string; template_id: string; start_date: string; payment_terms: string; lines: LineForm[] };

const today = () => new Date().toISOString().slice(0, 10);
const EMPTY_LINE: LineForm = { product_id: "", variant_id: "", quantity: "1", unit_price: "" };
const emptyForm = (): FormState => ({ customer_id: "", plan_id: "", template_id: "", start_date: today(), payment_terms: "immediate", lines: [{ ...EMPTY_LINE }] });

const STATUSES: Status[] = ["draft", "quotation", "confirmed", "active", "paused", "closed"];
const TABS: ("all" | Status)[] = ["all", ...STATUSES];
const TERMS = [
  { value: "immediate", label: "Immediate payment" },
  { value: "15_days", label: "15 days" },
  { value: "30_days", label: "30 days" },
  { value: "end_of_month", label: "End of month" },
];
const DOT: Record<Status, string> = {
  draft: "bg-slate-400", quotation: "bg-amber-500", confirmed: "bg-sky-500", active: "bg-emerald-500", paused: "bg-violet-500", closed: "bg-slate-300",
};
const NEXT: Partial<Record<Status, { key: string; label: string }>> = {
  draft: { key: "send-quotation", label: "Send quotation" },
  quotation: { key: "confirm", label: "Confirm" },
  confirmed: { key: "activate", label: "Activate" },
  paused: { key: "resume", label: "Resume" },
};

const list = (r: PromiseSettledResult<any>) => (r.status === "fulfilled" && Array.isArray(r.value.data) ? r.value.data : []);
function formatDate(d?: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export default function Subscriptions() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [items, setItems] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"all" | Status>("all");
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"list" | "board">(() => {
    try {
      return (localStorage.getItem("subs-view") as "list" | "board") || "list";
    } catch {
      return "list";
    }
  });
  const [moving, setMoving] = useState<number | null>(null);

  const [open, setOpen] = useState(false);
  const [editingSub, setEditingSub] = useState<Subscription | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/subscriptions/");
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

  function changeView(v: "list" | "board") {
    setView(v);
    try {
      localStorage.setItem("subs-view", v);
    } catch {}
  }

  async function loadLookups() {
    const [c, p, pl, t] = await Promise.allSettled([api.get("/users", { params: { role: "customer" } }), api.get("/products"), api.get("/plans"), api.get("/templates/")]);
    setCustomers(list(c));
    setProducts(list(p));
    setPlans(list(pl));
    setTemplates(list(t));
  }

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    for (const s of items) c[s.status] = (c[s.status] ?? 0) + 1;
    return c;
  }, [items]);

  const searched = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((s) => s.number?.toLowerCase().includes(q) || s.customer?.name?.toLowerCase().includes(q) || s.plan?.name?.toLowerCase().includes(q));
  }, [items, query]);

  const filtered = tab === "all" ? searched : searched.filter((s) => s.status === tab);

  async function moveNext(s: Subscription) {
    const next = NEXT[s.status];
    if (!next) return;
    setMoving(s.id);
    try {
      await api.post(`/subscriptions/${s.id}/${next.key}`);
      toast.success(`${s.number}: ${next.label} done`);
      await load();
    } catch (err) {
      toast.error(errorMessage(err, `${next.label} failed`));
    } finally {
      setMoving(null);
    }
  }

  function openNew() {
    setEditingSub(null);
    setForm(emptyForm());
    setOpen(true);
    loadLookups();
  }

  async function openEditSub(s: Subscription, e?: React.MouseEvent) {
    if (e) e.stopPropagation();
    setEditingSub(s);
    loadLookups();
    setOpen(true);
    try {
      const { data } = await api.get(`/subscriptions/${s.id}`);
      if (data) {
        setForm({
          customer_id: String(data.customer?.id ?? ""),
          plan_id: String(data.plan?.id ?? ""),
          template_id: "",
          start_date: data.start_date || today(),
          payment_terms: String(data.payment_terms || "immediate"),
          lines:
            data.lines && data.lines.length > 0
              ? data.lines.map((l: any) => ({
                  product_id: String(l.product_id),
                  variant_id: l.variant_id ? String(l.variant_id) : "",
                  quantity: String(l.quantity || 1),
                  unit_price: toRupees(l.unit_price) || "0",
                }))
              : [{ ...EMPTY_LINE }],
        });
      }
    } catch (err) {
      toast.error(errorMessage(err, "Could not load subscription details"));
    }
  }

  async function handleDeleteSub(s: Subscription, e?: React.MouseEvent) {
    if (e) e.stopPropagation();
    if (!confirm(`Are you sure you want to delete subscription "${s.number}"? All invoices for this subscription will also be removed.`)) {
      return;
    }
    try {
      await api.delete(`/subscriptions/${s.id}`);
      toast.success(`Subscription ${s.number} deleted`);
      setItems((list) => list.filter((item) => item.id !== s.id));
    } catch (err) {
      toast.error(errorMessage(err, "Could not delete subscription"));
    }
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

  function applyTemplate(id: string) {
    const t = templates.find((x) => String(x.id) === id);
    if (!t) return setForm((f) => ({ ...f, template_id: "" }));
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
              unit_price: l.unit_price != null ? toRupees(l.unit_price) || "0" : priceFor(String(l.product_id), l.variant_id ? String(l.variant_id) : ""),
            }))
          : f.lines,
    }));
  }

  const lineAmount = (l: LineForm) => toPaise(l.unit_price) * Math.max(0, parseInt(l.quantity) || 0);
  const subtotal = form.lines.reduce((sum, l) => sum + lineAmount(l), 0);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    const lines = form.lines.filter((l) => l.product_id);
    if (!form.customer_id) return toast.error("Please choose a customer");
    if (!form.plan_id) return toast.error("Please choose a plan");
    if (lines.length === 0) return toast.error("Add at least one product line");
    let taxId: number | null = null;
    try {
      const { data: tx } = await api.get("/taxes");
      const all: any[] = Array.isArray(tx) ? tx : [];
      const pick = all.find((t) => t.is_default) ?? all.find((t) => Number(t.rate) === 18) ?? null;
      taxId = pick?.id ?? null;
    } catch {}
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
        tax_id: taxId,
      })),
    };
    setSaving(true);
    try {
      if (editingSub) {
        const { data } = await api.put(`/subscriptions/${editingSub.id}`, body);
        toast.success(`Subscription ${data?.number ?? editingSub.number} updated`);
        setOpen(false);
        load();
      } else {
        const { data } = await api.post("/subscriptions/", body);
        toast.success(`Subscription ${data?.number ?? ""} created`);
        setOpen(false);
        if (data?.id) navigate(`/subscriptions/${data.id}`);
        else load();
      }
    } catch (err) {
      toast.error(errorMessage(err, editingSub ? "Could not update subscription" : "Could not create subscription"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {view === "list" ? (
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
        ) : (
          <p className="text-sm text-slate-500">Click the arrow on a card to move it to the next stage.</p>
        )}
        <div className="flex rounded-xl bg-white p-1 ring-1 ring-slate-200">
          {(["list", "board"] as const).map((v) => {
            const Icon = v === "list" ? List : LayoutGrid;
            return (
              <button
                key={v}
                onClick={() => changeView(v)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold capitalize transition ${view === v ? "bg-indigo-600 text-white" : "text-slate-500 hover:text-slate-800"}`}
              >
                <Icon className="h-4 w-4" /> {v}
              </button>
            );
          })}
        </div>
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

      {view === "board" ? (
        <div className="flex gap-4 overflow-x-auto pb-2">
          {STATUSES.map((st) => {
            const cards = searched.filter((s) => s.status === st);
            return (
              <div key={st} className="w-72 shrink-0 rounded-2xl bg-slate-100/70 p-3">
                <div className="mb-3 flex items-center justify-between px-1">
                  <span className="flex items-center gap-2 text-sm font-bold capitalize text-slate-700">
                    <span className={`h-2.5 w-2.5 rounded-full ${DOT[st]}`} /> {st}
                  </span>
                  <span className="rounded-md bg-white px-2 py-0.5 text-xs font-semibold text-slate-500">{cards.length}</span>
                </div>
                <div className="space-y-2">
                  {cards.length === 0 && <p className="rounded-xl border border-dashed border-slate-300 p-4 text-center text-xs text-slate-400">Empty</p>}
                  {cards.map((s) => {
                    const next = NEXT[s.status];
                    return (
                      <div
                        key={s.id}
                        onClick={() => navigate(`/subscriptions/${s.id}`)}
                        className="cursor-pointer rounded-xl bg-white p-3 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-md"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-indigo-600">{s.number}</span>
                          <div className="flex items-center gap-1.5">
                            <span className="text-sm font-bold text-slate-900">{formatINR(s.total)}</span>
                            {isAdmin && (
                              <div className="flex items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
                                <button
                                  onClick={(e) => openEditSub(s, e)}
                                  title="Edit subscription"
                                  className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-indigo-600"
                                >
                                  <Pencil className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  onClick={(e) => handleDeleteSub(s, e)}
                                  title="Delete subscription"
                                  className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                        <p className="mt-1.5 font-semibold text-slate-900">{s.customer?.name ?? "—"}</p>
                        <p className="text-xs text-slate-500">{s.plan?.name ?? "—"}</p>
                        {next && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              moveNext(s);
                            }}
                            disabled={moving !== null}
                            className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-indigo-50 py-1.5 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-100 disabled:opacity-60"
                          >
                            {moving === s.id ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <ArrowRight className="h-3.5 w-3.5" />}
                            {next.label}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
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
                {isAdmin && <th className="px-5 py-3 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading &&
                [1, 2, 3, 4].map((i) => (
                  <tr key={i}>
                    <td colSpan={isAdmin ? 8 : 7} className="px-5 py-4">
                      <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
                    </td>
                  </tr>
                ))}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 8 : 7} className="px-5 py-16 text-center">
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
                    {isAdmin && (
                      <td className="px-5 py-4" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={(e) => openEditSub(s, e)}
                            title="Edit subscription"
                            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-indigo-600"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            onClick={(e) => handleDeleteSub(s, e)}
                            title="Delete subscription"
                            className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={open} title={editingSub ? `Edit subscription ${editingSub.number}` : "New subscription"} onClose={() => setOpen(false)} wide>
        <form onSubmit={handleSave} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Customer</label>
              {customers.length > 0 ? (
                <select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} className={inputCls}>
                  <option value="">Select customer</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                      {c.email ? ` (${c.email})` : ""}
                    </option>
                  ))}
                </select>
              ) : (
                <input type="number" min="1" value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} placeholder="Customer ID (e.g. 3)" className={inputCls} />
              )}
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
              <input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} className={inputCls} />
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
            <div className="flex items-center justify-between">
              <label className={labelCls}>Order lines</label>
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, lines: [...f.lines, { ...EMPTY_LINE }] }))}
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
              >
                + Add line
              </button>
            </div>

            <div className="mt-2 space-y-2">
              {form.lines.map((l, i) => {
                const product = products.find((p) => String(p.id) === l.product_id);
                const variants = product?.variants ?? [];
                return (
                  <div key={i} className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-50 p-2 sm:flex-nowrap">
                    <select value={l.product_id} onChange={(e) => setLine(i, "product_id", e.target.value)} className={`${inputCls} min-w-[140px] flex-1`}>
                      <option value="">Select product</option>
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>

                    {variants.length > 0 && (
                      <select value={l.variant_id} onChange={(e) => setLine(i, "variant_id", e.target.value)} className={`${inputCls} min-w-[120px]`}>
                        <option value="">Base</option>
                        {variants.map((v) => (
                          <option key={v.id} value={v.id}>
                            {v.attribute}: {v.value} {v.extra_price ? `(+${formatINR(v.extra_price)})` : ""}
                          </option>
                        ))}
                      </select>
                    )}

                    <input
                      type="number"
                      min="1"
                      value={l.quantity}
                      onChange={(e) => setLine(i, "quantity", e.target.value)}
                      placeholder="Qty"
                      className={`${inputCls} w-20 text-right`}
                    />
                    <input
                      type="number"
                      step="0.01"
                      value={l.unit_price}
                      onChange={(e) => setLine(i, "unit_price", e.target.value)}
                      placeholder="Price"
                      className={`${inputCls} w-28 text-right`}
                    />
                    <span className="w-24 text-right text-xs font-semibold text-slate-700">{formatINR(lineAmount(l))}</span>
                    <button
                      type="button"
                      disabled={form.lines.length === 1}
                      onClick={() => setForm((f) => ({ ...f, lines: f.lines.filter((_, idx) => idx !== i) }))}
                      className="rounded-lg p-2 text-slate-400 hover:text-red-600 disabled:opacity-30"
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
            <button type="submit" disabled={saving} className={btnPrimary.replace("w-full", "")}>
              {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}
              {editingSub ? "Update subscription" : "Create subscription"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
