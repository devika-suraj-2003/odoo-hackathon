import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Users, Repeat, FileText, CreditCard, Package, CalendarClock,
  FileStack, Percent, BadgePercent, UserCog, UserRound, LogOut, Search,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuth, type Role } from "../context/AuthContext";
import CommandPalette from "./CommandPalette";
import TimeMachineBar from "./TimeMachineBar";

type Item = { to: string; label: string; icon: LucideIcon; roles: Role[] };

const items: Item[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "staff"] },
  { to: "/customers", label: "Customers", icon: Users, roles: ["admin", "staff"] },
  { to: "/subscriptions", label: "Subscriptions", icon: Repeat, roles: ["admin", "staff"] },
  { to: "/invoices", label: "Invoices", icon: FileText, roles: ["admin", "staff"] },
  { to: "/payments", label: "Payments", icon: CreditCard, roles: ["admin", "staff"] },
  { to: "/products", label: "Products", icon: Package, roles: ["admin"] },
  { to: "/plans", label: "Plans", icon: CalendarClock, roles: ["admin"] },
  { to: "/templates", label: "Quotation templates", icon: FileStack, roles: ["admin"] },
  { to: "/taxes", label: "Taxes", icon: Percent, roles: ["admin"] },
  { to: "/discounts", label: "Discounts", icon: BadgePercent, roles: ["admin"] },
  { to: "/staff", label: "Staff", icon: UserCog, roles: ["admin"] },
  { to: "/portal/subscriptions", label: "My subscriptions", icon: Repeat, roles: ["customer"] },
  { to: "/portal/invoices", label: "My invoices", icon: FileText, roles: ["customer"] },
  { to: "/portal/profile", label: "Profile", icon: UserRound, roles: ["customer"] },
];

const roleBadge: Record<Role, string> = {
  admin: "bg-violet-100 text-violet-700",
  staff: "bg-sky-100 text-sky-700",
  customer: "bg-emerald-100 text-emerald-700",
};

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);
  if (!user) return null;

  const menu = items.filter((i) => i.roles.includes(user.role));
  const current = menu.find((i) => location.pathname.startsWith(i.to));
  const initials = user.name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 flex w-64 flex-col bg-slate-950 text-slate-300">
        <div className="flex h-16 items-center gap-3 px-6">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-linear-to-br from-indigo-500 to-violet-500 font-extrabold text-white">B</div>
          <div>
            <p className="text-sm font-bold text-white">Brightloop</p>
            <p className="text-xs text-slate-500">Subscriptions</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {menu.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? "bg-indigo-600 text-white shadow-lg shadow-indigo-900/40" : "text-slate-400 hover:bg-slate-800/70 hover:text-white"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-800 p-3">
          <button onClick={handleLogout} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-400 transition hover:bg-slate-800/70 hover:text-white">
            <LogOut className="h-4 w-4" />
            Log out
          </button>
        </div>
      </aside>

      <div className="pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between gap-4 border-b border-slate-200 bg-white/80 px-8 backdrop-blur">
          <h1 className="text-lg font-bold text-slate-900">{current?.label ?? "Brightloop"}</h1>
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.dispatchEvent(new Event("open-palette"))}
              className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-400 transition hover:border-slate-300 hover:text-slate-600 md:flex"
            >
              <Search className="h-4 w-4" />
              <span className="w-40 text-left">Search...</span>
              <kbd className="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-xs">Ctrl K</kbd>
            </button>
            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${roleBadge[user.role]}`}>{user.role}</span>
            <div className="text-right">
              <p className="text-sm font-semibold text-slate-900">{user.name}</p>
              <p className="text-xs text-slate-500">{user.email}</p>
            </div>
            <div className="grid h-9 w-9 place-items-center rounded-full bg-linear-to-br from-indigo-500 to-violet-500 text-sm font-bold text-white">{initials}</div>
          </div>
        </header>

        {user.role !== "customer" && <TimeMachineBar onChanged={() => setRefreshKey((k) => k + 1)} />}

        <main key={refreshKey} className="p-8">
          <Outlet />
        </main>
      </div>

      <CommandPalette items={menu} onLogout={handleLogout} searchData={user.role !== "customer"} />
    </div>
  );
}