import { useNavigate } from "react-router-dom";
import { useAuth, homeFor, type Role } from "../context/AuthContext";

const DEMO: { role: Role; name: string; email: string }[] = [
  { role: "admin", name: "Admin User", email: "admin@brightloop.com" },
  { role: "staff", name: "Staff User", email: "staff@brightloop.com" },
  { role: "customer", name: "Acme Traders", email: "customer@acme.com" },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const demoLogin = (d: (typeof DEMO)[number]) => {
    login("demo", { name: d.name, email: d.email, role: d.role });
    navigate(homeFor(d.role));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <h1 className="text-2xl font-semibold">Brightloop</h1>
        <p className="text-sm text-slate-500 mb-6">Sign in to your account</p>
        <p className="text-xs uppercase tracking-wide text-slate-400 mb-2">Demo login (temporary)</p>
        <div className="flex flex-col gap-2">
          {DEMO.map((d) => (
            <button
              key={d.role}
              onClick={() => demoLogin(d)}
              className="w-full py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 capitalize"
            >
              Continue as {d.role}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}