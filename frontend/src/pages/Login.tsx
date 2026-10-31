import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { LoaderCircle, Eye, EyeOff } from "lucide-react";
import { errorMessage } from "../api/errors";
import { loginRequest } from "../api/auth";
import { useAuth, homeFor, type Role, type User } from "../context/AuthContext";
import AuthShell from "../components/AuthShell";
import { inputCls, labelCls, btnPrimary } from "../components/ui";

const DEMO_LOGINS: Record<Role, { email: string; password: string }> = {
  admin: { email: "admin@brightloop.com", password: "Admin@1234" },
  staff: { email: "staff@brightloop.com", password: "Staff@1234" },
  customer: { email: "customer@brightloop.com", password: "Customer@1234" },
};

const OFFLINE_USERS: Record<Role, User> = {
  admin: { id: 1, name: "Demo Admin", email: "admin@demo.com", role: "admin" },
  staff: { id: 2, name: "Demo Staff", email: "staff@demo.com", role: "staff" },
  customer: { id: 3, name: "Demo Customer", email: "customer@demo.com", role: "customer" },
};

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  async function doLogin(em: string, pw: string) {
    const { token, user } = await loginRequest(em, pw);
    login(token, user);
    toast.success(`Welcome back, ${user.name}`);
    navigate(homeFor(user.role), { replace: true });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await doLogin(email, password);
    } catch (err) {
      toast.error(errorMessage(err, "Login failed"));
    } finally {
      setLoading(false);
    }
  }

  async function demo(role: Role) {
    setLoading(true);
    try {
      await doLogin(DEMO_LOGINS[role].email, DEMO_LOGINS[role].password);
    } catch (err: any) {
      if (!err?.response) {
        login("demo", OFFLINE_USERS[role]);
        toast("Backend offline, using demo mode", { icon: "⚠️" });
        navigate(homeFor(role), { replace: true });
      } else {
        toast.error(errorMessage(err, "Demo login failed"));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Welcome back" subtitle="Log in to manage your subscriptions.">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className={labelCls}>Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" className={inputCls} />
        </div>

        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label className="text-sm font-medium text-slate-700">Password</label>
            <Link to="/forgot-password" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <input
              type={show ? "text" : "password"}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••"
              className={inputCls}
            />
            <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <button type="submit" disabled={loading} className={btnPrimary}>
          {loading && <LoaderCircle className="h-4 w-4 animate-spin" />}
          Log in
        </button>
      </form>

      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-slate-200" />
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400">Quick demo</span>
        <div className="h-px flex-1 bg-slate-200" />
      </div>

      <div className="grid grid-cols-3 gap-2">
        {(["admin", "staff", "customer"] as Role[]).map((r) => (
          <button
            key={r}
            onClick={() => demo(r)}
            disabled={loading}
            className="rounded-xl border border-slate-200 bg-white py-2 text-xs font-semibold capitalize text-slate-600 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 disabled:opacity-60"
          >
            {r}
          </button>
        ))}
      </div>

      <p className="mt-8 text-center text-sm text-slate-500">
        New here?{" "}
        <Link to="/signup" className="font-semibold text-indigo-600 hover:text-indigo-700">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}