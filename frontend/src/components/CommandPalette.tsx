import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, CornerDownLeft, FileText, Repeat, User, LogOut } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import api from "../api/client";

type NavItem = { to: string; label: string; icon: LucideIcon };
type Result = { key: string; label: string; sub?: string; icon: LucideIcon; group: string; run: () => void };

const asList = (r: PromiseSettledResult<any>) => (r.status === "fulfilled" && Array.isArray(r.value.data) ? r.value.data : []);

export default function CommandPalette({ items, onLogout, searchData }: { items: NavItem[]; onLogout: () => void; searchData: boolean }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [data, setData] = useState<{ subs: any[]; invoices: any[]; customers: any[] } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    }
    function onOpen() {
      setOpen(true);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("open-palette", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("open-palette", onOpen);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActive(0);
    setTimeout(() => inputRef.current?.focus(), 10);
    if (searchData) {
      Promise.allSettled([api.get("/subscriptions"), api.get("/invoices"), api.get("/users", { params: { role: "customer" } })]).then(([s, i, c]) =>
        setData({ subs: asList(s), invoices: asList(i), customers: asList(c) })
      );
    }
  }, [open, searchData]);

  const results = useMemo<Result[]>(() => {
    const q = query.trim().toLowerCase();
    const go = (to: string) => () => {
      navigate(to);
      setOpen(false);
    };
    const out: Result[] = [];

    items
      .filter((i) => !q || i.label.toLowerCase().includes(q))
      .forEach((i) => out.push({ key: `nav-${i.to}`, label: i.label, icon: i.icon, group: "Pages", run: go(i.to) }));

    if (q && data) {
      data.subs
        .filter((s) => s.number?.toLowerCase().includes(q) || s.customer?.name?.toLowerCase().includes(q))
        .slice(0, 5)
        .forEach((s) => out.push({ key: `s-${s.id}`, label: s.number, sub: s.customer?.name, icon: Repeat, group: "Subscriptions", run: go(`/subscriptions/${s.id}`) }));
      data.invoices
        .filter((i) => i.number?.toLowerCase().includes(q) || i.customer?.name?.toLowerCase().includes(q))
        .slice(0, 5)
        .forEach((i) => out.push({ key: `i-${i.id}`, label: i.number, sub: i.customer?.name, icon: FileText, group: "Invoices", run: go(`/invoices/${i.id}`) }));
      data.customers
        .filter((c) => c.name?.toLowerCase().includes(q) || c.email?.toLowerCase().includes(q))
        .slice(0, 5)
        .forEach((c) => out.push({ key: `c-${c.id}`, label: c.name, sub: c.email, icon: User, group: "Customers", run: go("/customers") }));
    }

    if (!q || "log out".includes(q)) {
      out.push({
        key: "logout",
        label: "Log out",
        icon: LogOut,
        group: "Actions",
        run: () => {
          setOpen(false);
          onLogout();
        },
      });
    }
    return out;
  }, [query, items, data, navigate, onLogout]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  if (!open) return null;

  function onInputKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      results[active]?.run();
    }
  }

  let lastGroup = "";

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-slate-950/50 p-4 pt-[15vh] backdrop-blur-sm" onMouseDown={() => setOpen(false)}>
      <div className="w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-slate-200 px-4">
          <Search className="h-5 w-5 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onInputKey}
            placeholder="Search pages, subscriptions, invoices, customers..."
            className="w-full py-4 text-sm outline-none placeholder:text-slate-400"
          />
          <kbd className="rounded-md border border-slate-200 px-1.5 py-0.5 text-xs text-slate-400">Esc</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-2">
          {results.length === 0 && <p className="px-3 py-8 text-center text-sm text-slate-500">No results for "{query}"</p>}
          {results.map((r, idx) => {
            const showGroup = r.group !== lastGroup;
            lastGroup = r.group;
            const Icon = r.icon;
            return (
              <div key={r.key}>
                {showGroup && <p className="px-3 pb-1 pt-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{r.group}</p>}
                <button
                  onMouseEnter={() => setActive(idx)}
                  onClick={r.run}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition ${idx === active ? "bg-indigo-50 text-indigo-700" : "text-slate-700"}`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="font-medium">{r.label}</span>
                  {r.sub && <span className="truncate text-xs text-slate-400">{r.sub}</span>}
                  {idx === active && <CornerDownLeft className="ml-auto h-4 w-4 shrink-0" />}
                </button>
              </div>
            );
          })}
        </div>
        <div className="flex gap-4 border-t border-slate-100 bg-slate-50 px-4 py-2 text-xs text-slate-400">
          <span>↑↓ to move</span>
          <span>Enter to open</span>
          <span>Ctrl+K to toggle</span>
        </div>
      </div>
    </div>
  );
}