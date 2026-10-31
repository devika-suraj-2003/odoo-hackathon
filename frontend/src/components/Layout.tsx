import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth, type Role } from "../context/AuthContext";

const MENUS: Record<Role, { label: string; to: string }[]> = {
  admin: [
    { label: "Dashboard", to: "/dashboard" },
    { label: "Customers", to: "/customers" },
    { label: "Products", to: "/products" },
    { label: "Plans", to: "/plans" },
    { label: "Templates", to: "/templates" },
    { label: "Subscriptions", to: "/subscriptions" },
    { label: "Invoices", to: "/invoices" },
    { label: "Payments", to: "/payments" },
    { label: "Taxes", to: "/taxes" },
    { label: "Discounts", to: "/discounts" },
    { label: "Staff", to: "/staff" },
  ],
  staff: [
    { label: "Dashboard", to: "/dashboard" },
    { label: "Customers", to: "/customers" },
    { label: "Subscriptions", to: "/subscriptions" },
    { label: "Invoices", to: "/invoices" },
    { label: "Payments", to: "/payments" },
  ],
  customer: [
    { label: "My Subscriptions", to: "/portal/subscriptions" },
    { label: "My Invoices", to: "/portal/invoices" },
    { label: "Profile", to: "/portal/profile" },
  ],
};

const ROLE_BADGE: Record<Role, string> = {
  admin: "bg-indigo-100 text-indigo-700",
  staff: "bg-emerald-100 text-emerald-700",
  customer: "bg-amber-100 text-amber-700",
};

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800">
      <aside className="w-60 shrink-0 bg-slate-900 text-slate-300 flex flex-col">
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="text-white text-lg font-semibold">Brightloop</div>
          <div className="text-xs text-slate-500">Subscription Manager</div>
        </div>
        <nav className="flex-1 overflow-y-auto py-3">
          {MENUS[user.role].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block mx-3 my-0.5 px-3 py-2 rounded-lg text-sm transition ${
                  isActive ? "bg-indigo-600 text-white" : "hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={() => { logout(); navigate("/login"); }}
          className="m-3 px-3 py-2 rounded-lg text-sm text-left hover:bg-slate-800 hover:text-white"
        >
          Log out
        </button>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-end gap-3 px-6">
          <span className="text-sm font-medium">{user.name}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${ROLE_BADGE[user.role]}`}>
            {user.role}
          </span>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}