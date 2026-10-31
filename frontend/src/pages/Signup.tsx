import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { LoaderCircle } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import { useAuth, homeFor } from "../context/AuthContext";
import AuthShell from "../components/AuthShell";
import PasswordChecklist, { isStrongPassword } from "../components/PasswordChecklist";
import { inputCls, labelCls, btnPrimary } from "../components/ui";

export default function Signup() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const mismatch = confirm.length > 0 && confirm !== password;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!isStrongPassword(password)) {
      toast.error("Password does not meet all the rules");
      return;
    }
    if (password !== confirm) {
      toast.error("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/signup", { name, email, password });
      const { data } = await api.post("/auth/login", { email, password });
      login(data.access_token, data.user);
      toast.success("Account created. Welcome!");
      navigate(homeFor(data.user.role), { replace: true });
    } catch (err) {
      toast.error(errorMessage(err, "Signup failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Create your account" subtitle="Start managing your subscriptions in minutes.">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className={labelCls}>Full name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" className={inputCls} />
        </div>

        <div>
          <label className={labelCls}>Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            className={inputCls}
          />
        </div>

        <div>
          <label className={labelCls}>Password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Create a strong password"
            className={inputCls}
          />
          <PasswordChecklist password={password} />
        </div>

        <div>
          <label className={labelCls}>Confirm password</label>
          <input
            type="password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Type it again"
            className={inputCls}
          />
          {mismatch && <p className="mt-1.5 text-xs text-red-600">Passwords do not match</p>}
        </div>

        <button type="submit" disabled={loading} className={btnPrimary}>
          {loading && <LoaderCircle className="h-4 w-4 animate-spin" />}
          Create account
        </button>
      </form>

      <p className="mt-8 text-center text-sm text-slate-500">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-indigo-600 hover:text-indigo-700">
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}