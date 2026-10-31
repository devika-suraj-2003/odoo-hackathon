const STYLES: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700 ring-slate-200",
  quotation: "bg-amber-50 text-amber-700 ring-amber-200",
  confirmed: "bg-teal-50 text-teal-700 ring-teal-200",
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  paused: "bg-slate-100 text-slate-600 ring-slate-300",
  closed: "bg-slate-100 text-slate-500 ring-slate-200",
  paid: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  cancelled: "bg-red-50 text-red-700 ring-red-200",
  overdue: "bg-red-50 text-red-700 ring-red-200",
  outstanding: "bg-amber-50 text-amber-700 ring-amber-200",
};

export default function StatusBadge({ status }: { status: string }) {
  const s = (status || "draft").toLowerCase();
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ring-1 ring-inset ${STYLES[s] ?? STYLES.draft}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {s}
    </span>
  );
}