import { useEffect, useMemo, useState, type FormEvent } from "react";
import toast from "react-hot-toast";
import { Plus, Search, Users, UserCog, LoaderCircle, MapPin, Phone, Pencil, Trash2 } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import Modal from "../components/Modal";
import PasswordChecklist, { isStrongPassword } from "../components/PasswordChecklist";
import { inputCls, labelCls, btnPrimary, btnSecondary } from "../components/ui";
import { useAuth } from "../context/AuthContext";

type Person = { id: number; name: string; email: string; role: string; phone?: string | null; state?: string | null; created_at?: string | null };

const STATES = [
  "Kerala", "Tamil Nadu", "Karnataka", "Andhra Pradesh", "Telangana", "Maharashtra", "Goa", "Gujarat", "Rajasthan",
  "Delhi", "Uttar Pradesh", "Madhya Pradesh", "West Bengal", "Odisha", "Bihar", "Punjab", "Haryana", "Assam", "Other",
];

const EMPTY = { name: "", email: "", phone: "", state: "Kerala", password: "" };

export default function People({ role }: { role: "customer" | "staff" }) {
  const isCustomer = role === "customer";
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [items, setItems] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  // Edit modal state
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<Person | null>(null);
  const [editForm, setEditForm] = useState(EMPTY);
  const [updating, setUpdating] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/users", { params: { role } });
      setItems(Array.isArray(data) ? data : []);
    } catch {
      // list endpoint not ready yet, keep what we have
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [role]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((p) => p.name.toLowerCase().includes(q) || p.email.toLowerCase().includes(q) || (p.phone ?? "").includes(q));
  }, [items, query]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    if (!isStrongPassword(form.password)) return toast.error("Password does not meet all the rules");
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || null,
        state: isCustomer ? form.state : null,
        password: form.password,
      };
      const { data } = isCustomer ? await api.post("/users", payload) : await api.post("/users/staff", payload);
      toast.success(`${isCustomer ? "Customer" : "Staff member"} added`);
      setOpen(false);
      if (data && data.id) {
        setItems((list) => [{ id: data.id, name: data.name ?? payload.name, email: data.email ?? payload.email, role, phone: data.phone ?? payload.phone, state: data.state ?? payload.state, created_at: data.created_at ?? new Date().toISOString() }, ...list.filter((p) => p.id !== data.id)]);
      }
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save"));
    } finally {
      setSaving(false);
    }
  }

  function openEdit(p: Person) {
    setEditing(p);
    setEditForm({
      name: p.name,
      email: p.email,
      phone: p.phone || "",
      state: p.state || "Kerala",
      password: "",
    });
    setEditOpen(true);
  }

  async function handleUpdate(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    if (editForm.password && !isStrongPassword(editForm.password)) {
      return toast.error("Password does not meet all the rules");
    }
    setUpdating(true);
    try {
      const payload: Record<string, any> = {
        name: editForm.name.trim(),
        email: editForm.email.trim(),
        phone: editForm.phone.trim() || null,
        state: isCustomer ? editForm.state : null,
      };
      if (editForm.password) {
        payload.password = editForm.password;
      }
      await api.put(`/users/${editing.id}`, payload);
      toast.success(`${isCustomer ? "Customer" : "Staff member"} updated`);
      setEditOpen(false);
      setEditing(null);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not update user"));
    } finally {
      setUpdating(false);
    }
  }

  async function handleDelete(p: Person) {
    const roleLabel = isCustomer ? "customer" : "staff member";
    if (!confirm(`Are you sure you want to delete ${roleLabel} "${p.name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await api.delete(`/users/${p.id}`);
      toast.success(`${isCustomer ? "Customer" : "Staff member"} deleted`);
      setItems((list) => list.filter((item) => item.id !== p.id));
    } catch (err) {
      toast.error(errorMessage(err, `Could not delete ${roleLabel}`));
    }
  }

  const Icon = isCustomer ? Users : UserCog;
  const colSpanCount = (isCustomer ? 5 : 4) + (isAdmin ? 1 : 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Search ${isCustomer ? "customers" : "staff"}...`}
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
          />
        </div>
        <button
          onClick={() => {
            setForm(EMPTY);
            setOpen(true);
          }}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" /> {isCustomer ? "New customer" : "Add staff"}
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3">Name</th>
              <th className="px-5 py-3">Phone</th>
              {isCustomer && <th className="px-5 py-3">State</th>}
              {isCustomer && <th className="px-5 py-3">GST type</th>}
              <th className="px-5 py-3">Joined</th>
              {isAdmin && <th className="px-5 py-3 text-right">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading &&
              [1, 2, 3].map((i) => (
                <tr key={i}>
                  <td colSpan={colSpanCount} className="px-5 py-4">
                    <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
                  </td>
                </tr>
              ))}

            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={colSpanCount} className="px-5 py-16 text-center">
                  <Icon className="mx-auto h-10 w-10 text-slate-300" />
                  <p className="mt-3 font-semibold text-slate-700">{isCustomer ? "No customers yet" : "No staff yet"}</p>
                  <p className="text-sm text-slate-500">{isCustomer ? "Customers can sign up themselves, or you can add them here." : "Only admins can add staff members."}</p>
                </td>
              </tr>
            )}

            {!loading &&
              filtered.map((p) => {
                const initials = p.name
                  .split(" ")
                  .map((w) => w[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase();
                return (
                  <tr key={p.id} className="transition hover:bg-slate-50/70">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="grid h-9 w-9 place-items-center rounded-full bg-linear-to-br from-indigo-500 to-violet-500 text-xs font-bold text-white">{initials}</div>
                        <div>
                          <p className="font-semibold text-slate-900">{p.name}</p>
                          <p className="text-xs text-slate-500">{p.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      {p.phone ? (
                        <span className="inline-flex items-center gap-1.5">
                          <Phone className="h-3.5 w-3.5 text-slate-400" />
                          {p.phone}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    {isCustomer && (
                      <td className="px-5 py-4 text-slate-600">
                        {p.state ? (
                          <span className="inline-flex items-center gap-1.5">
                            <MapPin className="h-3.5 w-3.5 text-slate-400" />
                            {p.state}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    )}
                    {isCustomer && (
                      <td className="px-5 py-4">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${p.state === "Kerala" ? "bg-emerald-50 text-emerald-700" : "bg-sky-50 text-sky-700"}`}>
                          {p.state === "Kerala" ? "CGST + SGST" : "IGST"}
                        </span>
                      </td>
                    )}
                    <td className="px-5 py-4 text-slate-600">
                      {p.created_at ? new Date(p.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—"}
                    </td>
                    {isAdmin && (
                      <td className="px-5 py-4">
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={() => openEdit(p)}
                            title={`Edit ${isCustomer ? "customer" : "staff"}`}
                            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-indigo-600"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(p)}
                            title={`Delete ${isCustomer ? "customer" : "staff"}`}
                            className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      <Modal open={open} title={isCustomer ? "New customer" : "Add staff member"} onClose={() => setOpen(false)}>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className={labelCls}>Full name</label>
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Email</label>
            <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={inputCls} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Phone</label>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Optional" className={inputCls} />
            </div>
            {isCustomer && (
              <div>
                <label className={labelCls}>State (for GST)</label>
                <select value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} className={inputCls}>
                  {STATES.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
          <div>
            <label className={labelCls}>Temporary password</label>
            <input required type="text" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className={inputCls} />
            <PasswordChecklist password={form.password} />
          </div>
          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => setOpen(false)} className={btnSecondary}>
              Cancel
            </button>
            <button type="submit" disabled={saving} className={btnPrimary.replace("w-full", "")}>
              {saving && <LoaderCircle className="h-4 w-4 animate-spin" />}
              Save
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Modal (Admin only) */}
      <Modal open={editOpen} title={isCustomer ? "Edit customer" : "Edit staff member"} onClose={() => setEditOpen(false)}>
        <form onSubmit={handleUpdate} className="space-y-4">
          <div>
            <label className={labelCls}>Full name</label>
            <input required value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Email</label>
            <input required type="email" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} className={inputCls} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelCls}>Phone</label>
              <input value={editForm.phone} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} placeholder="Optional" className={inputCls} />
            </div>
            {isCustomer && (
              <div>
                <label className={labelCls}>State (for GST)</label>
                <select value={editForm.state} onChange={(e) => setEditForm({ ...editForm, state: e.target.value })} className={inputCls}>
                  {STATES.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
          <div>
            <label className={labelCls}>New password (optional)</label>
            <input
              type="text"
              value={editForm.password}
              onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
              placeholder="Leave blank to keep current password"
              className={inputCls}
            />
            {editForm.password && <PasswordChecklist password={editForm.password} />}
          </div>
          <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => setEditOpen(false)} className={btnSecondary}>
              Cancel
            </button>
            <button type="submit" disabled={updating} className={btnPrimary.replace("w-full", "")}>
              {updating && <LoaderCircle className="h-4 w-4 animate-spin" />}
              Update
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
