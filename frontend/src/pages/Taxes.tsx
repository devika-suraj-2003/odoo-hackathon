import { useEffect, useState, type FormEvent } from "react";
import toast from "react-hot-toast";
import { Plus, Pencil, Trash2, Percent, LoaderCircle } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Modal from "../components/Modal";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { formatINR } from "../lib/money";

type Tax = {
  id: number;
  name: string;
  rate: number;
  tax_type: "gst" | "vat" | "sales_tax" | "exempt" | "other";
  is_active: boolean;
  description?: string | null;
};
type TaxCalculation = {
  tax_amount_paise: number;
  total_paise: number;
  gst_breakdown: {
    is_intra_state: boolean;
    company_state: string;
    customer_state: string;
    cgst_rate: number;
    cgst_amount_paise: number;
    sgst_rate: number;
    sgst_amount_paise: number;
    igst_rate: number;
    igst_amount_paise: number;
  } | null;
};

const EMPTY = { name: "", rate: "18", tax_type: "gst" as Tax["tax_type"], description: "", is_active: true };

export default function Taxes() {
  const [items, setItems] = useState<Tax[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Tax | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState({ amount: "1000", rate: "18" });
  const [previewState, setPreviewState] = useState("Kerala");
  const [calculation, setCalculation] = useState<TaxCalculation | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/taxes");
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load taxes"), { id: "taxes-load" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const amount = Number(preview.amount);
    const rate = Number(preview.rate);
    if (!Number.isFinite(amount) || amount < 0 || !Number.isFinite(rate) || rate < 0 || rate > 100) {
      setCalculation(null);
      setPreviewLoading(false);
      setPreviewError("Enter a non-negative amount and a tax rate between 0 and 100.");
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setPreviewLoading(true);
      setPreviewError("");
      api
        .post("/taxes/calculate", {
          subtotal_paise: Math.round(amount * 100),
          tax_rate: rate,
          customer_state: previewState,
        })
        .then(({ data }) => {
          if (!cancelled) setCalculation(data);
        })
        .catch((err) => {
          if (!cancelled) {
            setCalculation(null);
            setPreviewError(errorMessage(err, "Could not calculate GST."));
          }
        })
        .finally(() => {
          if (!cancelled) setPreviewLoading(false);
        });
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [preview.amount, preview.rate, previewState]);

  function openNew() {
    setEditing(null);
    setForm(EMPTY);
    setOpen(true);
  }

  function openEdit(t: Tax) {
    setEditing(t);
    setForm({ name: t.name, rate: String(t.rate), tax_type: t.tax_type, description: t.description ?? "", is_active: t.is_active });
    setOpen(true);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    const rate = parseFloat(form.rate);
    if (!Number.isFinite(rate) || rate < 0 || rate > 100) return toast.error("Rate must be between 0 and 100");
    const body = {
      name: form.name.trim(),
      rate,
      tax_type: form.tax_type,
      description: form.description.trim() || null,
      is_active: form.is_active,
    };
    setSaving(true);
    try {
      if (editing) await api.put(`/taxes/${editing.id}`, body);
      else await api.post("/taxes", body);
      toast.success(editing ? "Tax updated" : "Tax created");
      setOpen(false);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save tax"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(t: Tax) {
    if (!confirm(`Delete tax "${t.name}"?`)) return;
    try {
      await api.delete(`/taxes/${t.id}`);
      toast.success("Tax deleted");
      setItems((list) => list.map((x) => (x.id === t.id ? { ...x, is_active: false } : x)));
    } catch (err) {
      toast.error(errorMessage(err, "Could not delete tax"));
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">Manage tax rules and preview server-calculated GST.</p>
            <button onClick={openNew} className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700">
              <Plus className="h-4 w-4" /> New tax
            </button>
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3">Tax</th>
                  <th className="px-5 py-3 text-right">Rate</th>
                  <th className="px-5 py-3">Kerala</th>
                  <th className="px-5 py-3">Other states</th>
                  <th className="px-5 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {!loading && items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-5 py-14 text-center">
                      <Percent className="mx-auto h-10 w-10 text-slate-300" />
                      <p className="mt-3 font-semibold text-slate-700">No tax rules yet</p>
                      <p className="text-sm text-slate-500">Add GST 18% to start.</p>
                    </td>
                  </tr>
                )}
                {items.map((t) => (
                  <tr key={t.id} className="transition hover:bg-slate-50/70">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-slate-900">{t.name}</p>
                        {!t.is_active && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">Inactive</span>}
                      </div>
                      {t.description && <p className="text-xs text-slate-500">{t.description}</p>}
                    </td>
                    <td className="px-5 py-4 text-right font-bold text-slate-900">{t.rate}%</td>
                    <td className="px-5 py-4 text-xs text-emerald-700">
                      CGST {t.rate / 2}% + SGST {t.rate / 2}%
                    </td>
                    <td className="px-5 py-4 text-xs text-sky-700">IGST {t.rate}%</td>
                    <td className="px-5 py-4">
                      <div className="flex justify-end gap-1">
                        <button onClick={() => openEdit(t)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-indigo-600">
                          <Pencil className="h-4 w-4" />
                        </button>
                        {t.is_active && (
                          <button onClick={() => handleDelete(t)} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-bold text-slate-900">GST split preview</h3>
          <p className="mt-1 text-xs text-slate-500">GST jurisdiction follows the configured company state.</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Amount (₹)</label>
              <input type="number" value={preview.amount} onChange={(e) => setPreview({ ...preview, amount: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>GST %</label>
              <input type="number" value={preview.rate} onChange={(e) => setPreview({ ...preview, rate: e.target.value })} className={inputCls} />
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Customer state</label>
              <select value={previewState} onChange={(e) => setPreviewState(e.target.value)} className={inputCls}>
                <option value="Kerala">Kerala</option>
                <option value="Maharashtra">Maharashtra</option>
              </select>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {previewError && <p role="alert" className="text-sm text-red-600">{previewError}</p>}
            {previewLoading && <p className="text-sm text-slate-500">Calculating GST…</p>}
            {calculation?.gst_breakdown && (
              <div className={`rounded-xl p-4 ${calculation.gst_breakdown.is_intra_state ? "bg-emerald-50" : "bg-sky-50"}`}>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-700">
                  {calculation.gst_breakdown.is_intra_state ? "CGST + SGST" : "IGST"} · Company: {calculation.gst_breakdown.company_state}
                </p>
                <div className="mt-2 space-y-1 text-sm text-slate-700">
                  {calculation.gst_breakdown.is_intra_state ? (
                    <>
                      <div className="flex justify-between"><span>CGST {calculation.gst_breakdown.cgst_rate}%</span><span>{formatINR(calculation.gst_breakdown.cgst_amount_paise)}</span></div>
                      <div className="flex justify-between"><span>SGST {calculation.gst_breakdown.sgst_rate}%</span><span>{formatINR(calculation.gst_breakdown.sgst_amount_paise)}</span></div>
                    </>
                  ) : (
                    <div className="flex justify-between"><span>IGST {calculation.gst_breakdown.igst_rate}%</span><span>{formatINR(calculation.gst_breakdown.igst_amount_paise)}</span></div>
                  )}
                  <div className="flex justify-between border-t border-slate-200 pt-1 font-bold text-slate-900">
                    <span>Total including tax</span><span>{formatINR(calculation.total_paise)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <Modal open={open} title={editing ? "Edit tax" : "New tax"} onClose={() => setOpen(false)}>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Name</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="GST 18%" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Rate (%)</label>
              <input required type="number" min="0" max="100" step="0.01" value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} className={inputCls} />
            </div>
          </div>
          <div>
            <label className={labelCls}>Tax type</label>
            <select value={form.tax_type} onChange={(e) => setForm({ ...form, tax_type: e.target.value as Tax["tax_type"] })} className={inputCls}>
              <option value="gst">GST</option>
              <option value="vat">VAT</option>
              <option value="sales_tax">Sales tax</option>
              <option value="exempt">Exempt</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className={labelCls}>Description</label>
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional" className={inputCls} />
          </div>
          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="h-4 w-4 accent-indigo-600" />
              Active
            </label>
          </div>
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