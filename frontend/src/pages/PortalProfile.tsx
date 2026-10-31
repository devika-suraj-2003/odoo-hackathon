import { Mail, ShieldCheck, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function PortalProfile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;
  const initials = user.name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="max-w-xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <div className="flex items-center gap-4">
        <div className="grid h-16 w-16 place-items-center rounded-full bg-linear-to-br from-indigo-500 to-violet-500 text-xl font-bold text-white">{initials}</div>
        <div>
          <h2 className="text-xl font-bold text-slate-900">{user.name}</h2>
          <p className="flex items-center gap-1.5 text-sm text-slate-500">
            <Mail className="h-4 w-4" /> {user.email}
          </p>
        </div>
      </div>
      <div className="mt-6 flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
        <ShieldCheck className="h-4 w-4" /> Your account is active. You only see your own subscriptions and invoices.
      </div>
      <div className="mt-6 flex gap-2">
        <button onClick={() => navigate("/forgot-password")} className="rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50">
          Change password
        </button>
        <button
          onClick={() => {
            logout();
            navigate("/login");
          }}
          className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-red-600 ring-1 ring-red-200 hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" /> Log out
        </button>
      </div>
    </div>
  );
}