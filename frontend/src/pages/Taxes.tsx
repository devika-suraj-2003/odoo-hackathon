import { useEffect, useState, type FormEvent } from "react";
import toast from "react-hot-toast";
import { Plus, Pencil, Trash2, Percent, LoaderCircle } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Modal from "../components/Modal";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { formatINR } from "../lib/money";

type Tax = { id: number; name: string; rate: number; is_default?: boolean; active?: boolean; description?: string | null };

const EMPTY = { name: "", rate: "18", description: "", is_default: false, active: true };

export default function Taxes() {
  const [items, setItems] = useState<Tax[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Tax | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState({ amount: "1000", rate: "18" });

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

  function openNew() {
    setEditing(null);
    setForm(EMPTY);
    setOpen(true);
  }

  function openEdit(t: Tax) {
    setEditing(t);
    setForm({ name: t.name, rate: String(t.rate), description: t.description ?? "", is_default: !!t.is_default, active: t.active !== false });
    setOpen(true);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    const rate = parseFloat(form.rate);
    if (!Number.isFinite(rate) || rate < 0 || rate > 100) return toast.error("Rate must be between 0 and 100");
    const body = { name: form.name.trim(), rate, description: form.description.trim() || null, is_default: form.is_default, active: form.active };
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
      setItems((list) => list.filter((x) => x.id !== t.id));
    } catch (err) {
      toast.error(errorMessage(err, "Could not delete tax"));
    }
  }

  const base = Math.round((parseFloat(preview.amount) || 0) * 100);
  const pRate = parseFloat(preview.rate) || 0;
  const taxTotal = Math.round((base * pRate) / 100);
  const half = Math.round(taxTotal / 2);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">Taxes are applied automatically to every invoice line.</p>
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
                        {t.is_default && <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">Default</span>}
                        {t.active === false && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">Inactive</span>}
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
                        <button onClick={() => handleDelete(t)} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600">
                          <Trash2 className="h-4 w-4" />
                        </button>
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
          <p className="mt-1 text-xs text-slate-500">Brightloop is registered in Kerala.</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Amount (₹)</label>
              <input type="number" value={preview.amount} onChange={(e) => setPreview({ ...preview, amount: e.target.value })} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>GST %</label>
              <input type="number" value={preview.rate} onChange={(e) => setPreview({ ...preview, rate: e.target.value })} className={inputCls} />
            </div>
          </div>
          <div className="mt-5 space-y-3">
            <div className="rounded-xl bg-emerald-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Customer in Kerala</p>
              <div className="mt-2 space-y-1 text-sm text-slate-700">
                <div className="flex justify-between"><span>CGST {pRate / 2}%</span><span>{formatINR(half)}</span></div>
                <div className="flex justify-between"><span>SGST {pRate / 2}%</span><span>{formatINR(taxTotal - half)}</span></div>
                <div className="flex justify-between border-t border-emerald-200 pt-1 font-bold text-slate-900"><span>Total</span><span>{formatINR(base + taxTotal)}</span></div>
              </div>
            </div>
            <div className="rounded-xl bg-sky-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">Customer in another state</p>
              <div className="mt-2 space-y-1 text-sm text-slate-700">
                <div className="flex justify-between"><span>IGST {pRate}%</span><span>{formatINR(taxTotal)}</span></div>
                <div className="flex justify-between border-t border-sky-200 pt-1 font-bold text-slate-900"><span>Total</span><span>{formatINR(base + taxTotal)}</span></div>
              </div>
            </div>
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
            <label className={labelCls}>Description</label>
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Optional" className={inputCls} />
          </div>
          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} className="h-4 w-4 accent-indigo-600" />
              Default tax for new lines
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} className="h-4 w-4 accent-indigo-600" />
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