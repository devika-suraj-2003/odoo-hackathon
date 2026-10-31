import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { LoaderCircle, MailCheck, ArrowLeft } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";
import AuthShell from "../components/AuthShell";
import { inputCls, labelCls, btnPrimary } from "../components/ui";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
    } catch (err) {
      toast.error(errorMessage(err, "Could not send reset link"));
    } finally {
      setLoading(false);
    }
  }

  if (sent) {
    return (
      <AuthShell title="Check your email">
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-center">
          <MailCheck className="mx-auto h-10 w-10 text-emerald-600" />
          <p className="mt-3 text-sm text-slate-700">
            If an account exists for <span className="font-semibold">{email}</span>, we've sent a link to reset your password.
          </p>
        </div>
        <button onClick={() => setSent(false)} className="mt-6 w-full text-sm font-medium text-indigo-600 hover:text-indigo-700">
          Use a different email
        </button>
        <Link to="/login" className="mt-4 flex items-center justify-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
          <ArrowLeft className="h-4 w-4" /> Back to login
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Forgot your password?" subtitle="Enter your email and we'll send you a reset link.">
      <form onSubmit={handleSubmit} className="space-y-5">
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
        <button type="submit" disabled={loading} className={btnPrimary}>
          {loading && <LoaderCircle className="h-4 w-4 animate-spin" />}
          Send reset link
        </button>
      </form>
      <Link to="/login" className="mt-8 flex items-center justify-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft className="h-4 w-4" /> Back to login
      </Link>
    </AuthShell>
  );
}