import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  LayoutDashboard, Users, Repeat, FileText, CreditCard, Package, CalendarClock,
  FileStack, Percent, BadgePercent, UserCog, UserRound, LogOut, Search, Moon, Sun, Menu, X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuth, type Role } from "../context/AuthContext";
import CommandPalette from "./CommandPalette";
import TimeMachineBar from "./TimeMachineBar";
import ThemePicker from "./ThemePicker";
import BrandMark, { Wordmark } from "./BrandMark";

type Item = { to: string; label: string; icon: LucideIcon; roles: Role[]; group: string };

const items: Item[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "staff"], group: "Overview" },
  { to: "/customers", label: "Customers", icon: Users, roles: ["admin", "staff"], group: "Overview" },
  { to: "/subscriptions", label: "Subscriptions", icon: Repeat, roles: ["admin", "staff"], group: "Overview" },
  { to: "/invoices", label: "Invoices", icon: FileText, roles: ["admin", "staff"], group: "Billing" },
  { to: "/payments", label: "Payments", icon: CreditCard, roles: ["admin", "staff"], group: "Billing" },
  { to: "/products", label: "Products", icon: Package, roles: ["admin"], group: "Catalog" },
  { to: "/plans", label: "Plans", icon: CalendarClock, roles: ["admin"], group: "Catalog" },
  { to: "/templates", label: "Quotation templates", icon: FileStack, roles: ["admin"], group: "Catalog" },
  { to: "/taxes", label: "Taxes", icon: Percent, roles: ["admin"], group: "Settings" },
  { to: "/discounts", label: "Discounts", icon: BadgePercent, roles: ["admin"], group: "Settings" },
  { to: "/staff", label: "Staff", icon: UserCog, roles: ["admin"], group: "Settings" },
  { to: "/portal/subscriptions", label: "My subscriptions", icon: Repeat, roles: ["customer"], group: "My account" },
  { to: "/portal/invoices", label: "My invoices", icon: FileText, roles: ["customer"], group: "My account" },
  { to: "/portal/profile", label: "Profile", icon: UserRound, roles: ["customer"], group: "My account" },
];

const roleBadge: Record<Role, string> = {
  admin: "bg-violet-100 text-violet-700 ring-violet-200",
  staff: "bg-sky-100 text-sky-700 ring-sky-200",
  customer: "bg-emerald-100 text-emerald-700 ring-emerald-200",
};

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <BrandMark />
      <div>
        <Wordmark light className="block text-[16px] leading-tight" />
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-white/50">Subscriptions</p>
      </div>
    </div>
  );
}

function SidebarContent({
  menu,
  pathname,
  initials,
  name,
  email,
  onLogout,
  onNavigate,
  layoutPrefix,
}: {
  menu: Item[];
  pathname: string;
  initials: string;
  name: string;
  email: string;
  onLogout: () => void;
  onNavigate?: () => void;
  layoutPrefix: string;
}) {
  const groups = menu.reduce<Record<string, Item[]>>((acc, item) => {
    (acc[item.group] ??= []).push(item);
    return acc;
  }, {});

  return (
    <div className="relative flex h-full flex-col overflow-hidden">
      {/* glow decorations */}
      <div className="bl-glow-a pointer-events-none absolute -left-24 -top-24 h-64 w-64 rounded-full blur-3xl" />
      <div className="bl-glow-c pointer-events-none absolute -bottom-24 -right-20 h-64 w-64 rounded-full blur-3xl" />

      <div className="relative flex h-20 items-center px-6">
        <Brand />
      </div>

      <nav className="relative flex-1 space-y-6 overflow-y-auto px-4 py-4">
        {Object.entries(groups).map(([group, list]) => (
          <div key={group}>
            <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{group}</p>
            <div className="space-y-1">
              {list.map(({ to, label, icon: Icon }) => {
                const active = pathname === to || pathname.startsWith(to + "/");
                return (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={onNavigate}
                    className={`group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                      active ? "text-white" : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId={`${layoutPrefix}-active`}
                        className="bl-pill absolute inset-0 rounded-xl ring-1 ring-inset ring-white/15"
                        transition={{ type: "spring", stiffness: 420, damping: 34 }}
                      />
                    )}
                    {!active && <span className="absolute inset-0 rounded-xl bg-white/0 transition-colors group-hover:bg-white/5" />}
                    <Icon className={`relative h-4 w-4 transition-transform duration-200 ${active ? "" : "group-hover:scale-110"}`} />
                    <span className="relative">{label}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="relative m-4 rounded-2xl border border-white/10 bg-white/5 p-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="bl-logo grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-bold text-white">{initials}</div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-white">{name}</p>
            <p className="truncate text-xs text-slate-400">{email}</p>
          </div>
          <button
            onClick={onLogout}
            title="Log out"
            className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-red-500/15 hover:text-red-300"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // Spotlight: a soft glow that follows the mouse across every card.
  useEffect(() => {
    const move = (e: PointerEvent) => {
      const card = (e.target as HTMLElement | null)?.closest?.("main .rounded-2xl.bg-white") as HTMLElement | null;
      if (!card) return;
      const r = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${e.clientX - r.left}px`);
      card.style.setProperty("--my", `${e.clientY - r.top}px`);
    };
    document.addEventListener("pointermove", move);
    return () => document.removeEventListener("pointermove", move);
  }, []);

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

  function toggleDark() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {}
  }

  const sidebarProps = {
    menu,
    pathname: location.pathname,
    initials,
    name: user.name,
    email: user.email,
    onLogout: handleLogout,
  };

  return (
    <div className="bl-app relative min-h-screen">
      {/* ambient background */}
      <div className="bl-aurora pointer-events-none fixed inset-0 -z-10" aria-hidden />

      {/* desktop sidebar */}
      <aside className="bl-sidebar fixed inset-y-0 left-0 z-30 hidden w-72 text-slate-300 lg:block">
        <SidebarContent {...sidebarProps} layoutPrefix="desk" />
      </aside>

      {/* mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm lg:hidden"
              onClick={() => setMobileOpen(false)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.aside
              className="bl-sidebar fixed inset-y-0 left-0 z-50 w-72 text-slate-300 shadow-2xl lg:hidden"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 380, damping: 36 }}
            >
              <button
                onClick={() => setMobileOpen(false)}
                className="absolute right-3 top-6 z-10 grid h-8 w-8 place-items-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
              <SidebarContent {...sidebarProps} layoutPrefix="mobile" onNavigate={() => setMobileOpen(false)} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div className="bl-shell lg:pl-72">
        <header className="bl-header sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-white/60 bg-white/70 px-4 backdrop-blur-xl sm:px-6 lg:h-20 lg:px-10">
          <div className="flex min-w-0 items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:text-slate-900 lg:hidden"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="min-w-0">
              <p className="hidden text-xs font-medium text-slate-400 sm:block">
                Brightloop <span className="mx-1 text-slate-300">/</span> {current?.group ?? "Workspace"}
              </p>
              <AnimatePresence mode="wait">
                <motion.h1
                  key={current?.label ?? "Brightloop"}
                  className="bl-title truncate text-lg font-extrabold tracking-tight lg:text-xl"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2 }}
                >
                  {current?.label ?? "Brightloop"}
                </motion.h1>
              </AnimatePresence>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <button
              onClick={() => window.dispatchEvent(new Event("open-palette"))}
              className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-sm text-slate-400 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:text-slate-600 hover:shadow-md md:flex"
            >
              <Search className="h-4 w-4" />
              <span className="w-32 text-left xl:w-44">Search...</span>
              <kbd className="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-xs">Ctrl K</kbd>
            </button>
            <button
              onClick={() => window.dispatchEvent(new Event("open-palette"))}
              className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 md:hidden"
              aria-label="Search"
            >
              <Search className="h-4 w-4" />
            </button>
            <ThemePicker />
            <motion.button
              onClick={toggleDark}
              title={dark ? "Light mode" : "Dark mode"}
              whileTap={{ scale: 0.9 }}
              className="grid h-10 w-10 place-items-center overflow-hidden rounded-xl border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:text-indigo-600"
            >
              <AnimatePresence mode="wait" initial={false}>
                <motion.span
                  key={dark ? "sun" : "moon"}
                  initial={{ rotate: -90, opacity: 0 }}
                  animate={{ rotate: 0, opacity: 1 }}
                  exit={{ rotate: 90, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </motion.span>
              </AnimatePresence>
            </motion.button>
            <span className={`hidden rounded-full px-2.5 py-1 text-xs font-semibold capitalize ring-1 ring-inset sm:inline ${roleBadge[user.role]}`}>{user.role}</span>
            <div className="hidden text-right xl:block">
              <p className="text-sm font-semibold text-slate-900">{user.name}</p>
              <p className="text-xs text-slate-500">{user.email}</p>
            </div>
            <div className="bl-logo relative grid h-10 w-10 place-items-center rounded-full text-sm font-bold text-white">
              {initials}
              <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-400" />
            </div>
          </div>
        </header>

        {user.role !== "customer" && <TimeMachineBar onChanged={() => setRefreshKey((k) => k + 1)} />}

        <main className="mx-auto w-full max-w-[1500px] p-4 sm:p-6 lg:p-10">
          <AnimatePresence mode="wait">
            <motion.div
              key={`${location.pathname}-${refreshKey}`}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0, transitionEnd: { transform: "none" } }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      <CommandPalette items={menu} onLogout={handleLogout} searchData={user.role !== "customer"} />
    </div>
  );
}
