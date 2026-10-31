import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { LoaderCircle, TriangleAlert } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import AuthShell from "../components/AuthShell";
import PasswordChecklist, { isStrongPassword } from "../components/PasswordChecklist";
import { inputCls, labelCls, btnPrimary } from "../components/ui";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const mismatch = confirm.length > 0 && confirm !== password;

  if (!token) {
    return (
      <AuthShell title="Invalid reset link">
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center">
          <TriangleAlert className="mx-auto h-10 w-10 text-amber-600" />
          <p className="mt-3 text-sm text-slate-700">This link is missing or broken. Please request a new one.</p>
        </div>
        <Link to="/forgot-password" className={`${btnPrimary} mt-6`}>
          Request a new link
        </Link>
      </AuthShell>
    );
  }

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
      await api.post("/auth/reset-password", { token, new_password: password });
      toast.success("Password updated. Please log in.");
      navigate("/login", { replace: true });
    } catch (err) {
      toast.error(errorMessage(err, "Could not reset password"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell title="Set a new password" subtitle="Choose a strong password you haven't used before.">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className={labelCls}>New password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="New password"
            className={inputCls}
          />
          <PasswordChecklist password={password} />
        </div>
        <div>
          <label className={labelCls}>Confirm new password</label>
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
          Update password
        </button>
      </form>
    </AuthShell>
  );
}