import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Clock, FastForward, RotateCcw, LoaderCircle, Zap, ShieldCheck } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";

const STEPS = [
  { days: 1, label: "+1 day" },
  { days: 7, label: "+1 week" },
  { days: 30, label: "+1 month" },
];

function pickToday(d: any): { today: string; simulated: boolean } | null {
  if (!d || typeof d !== "object") return null;
  const src = d.settings && typeof d.settings === "object" ? { ...d, ...d.settings } : d;
  const today = src.simulated_today || src.today || src.current_date || src.real_today;
  if (!today) return { today: new Date().toISOString().slice(0, 10), simulated: false };
  return { today, simulated: !!src.simulated_today && src.simulated_today !== src.real_today };
}

function nice(d: string) {
  return new Date(d).toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
}

function createdCount(data: any): number | null {
  if (!data || typeof data !== "object") return null;
  const n = data.created ?? data.invoices_created ?? data.count;
  return typeof n === "number" ? n : null;
}

export default function TimeMachineBar({ onChanged }: { onChanged: () => void }) {
  const [clock, setClock] = useState<{ today: string; simulated: boolean } | null>(null);
  const [available, setAvailable] = useState(true);
  const [busy, setBusy] = useState<number | "reset" | "bill" | null>(null);
  const [runs, setRuns] = useState<number[]>([]);

  useEffect(() => {
    api
      .get("/settings")
      .then(({ data }) => {
        const c = pickToday(data);
        if (c) setClock(c);
        else setAvailable(false);
      })
      .catch(() => setAvailable(false));
  }, []);

  async function advance(days: number) {
    setBusy(days);
    try {
      const { data } = await api.post("/settings/time-travel", { days });
      setClock({ today: data.simulated_today, simulated: true });
      setRuns([]);
      const n = createdCount(data);
      toast.success(`Jumped to ${nice(data.simulated_today)}${n !== null ? ` · ${n} invoice${n === 1 ? "" : "s"} created` : ""}`, { duration: 4000 });
      onChanged();
    } catch (err) {
      toast.error(errorMessage(err, "Could not move time"));
    } finally {
      setBusy(null);
    }
  }

  async function reset() {
    setBusy("reset");
    try {
      const { data } = await api.post("/settings/time-travel/reset");
      setClock({ today: data.simulated_today || data.real_today, simulated: false });
      setRuns([]);
      toast.success("Back to the real date");
      onChanged();
    } catch (err) {
      toast.error(errorMessage(err, "Could not reset time"));
    } finally {
      setBusy(null);
    }
  }

  async function runBilling() {
    setBusy("bill");
    try {
      const { data } = await api.post("/billing/run");
      const n = createdCount(data) ?? 0;
      const isRepeat = runs.length > 0;
      setRuns((r) => [...r, n]);
      if (isRepeat && n === 0) {
        toast.success("Ran billing again: 0 new invoices. No double billing ✓", { duration: 5000 });
      } else {
        toast.success(`Billing run complete · ${n} invoice${n === 1 ? "" : "s"} created`, { duration: 4000 });
      }
      onChanged();
    } catch (err: any) {
      if (err?.response?.status === 404) toast.error("Billing run is not available on the backend yet");
      else toast.error(errorMessage(err, "Billing run failed"));
    } finally {
      setBusy(null);
    }
  }

  if (!available) {
    return (
      <div className="no-print flex items-center gap-2 border-b border-slate-200 bg-slate-50 px-8 py-2 text-xs text-slate-400">
        <Clock className="h-3.5 w-3.5" /> Time machine will appear here when billing is connected.
      </div>
    );
  }

  const lastRun = runs.length > 0 ? runs[runs.length - 1] : null;
  const provenNoDuplicates = runs.length > 1 && lastRun === 0;

  return (
    <div className="no-print flex flex-wrap items-center justify-between gap-3 border-b border-indigo-100 bg-linear-to-r from-indigo-50 to-violet-50 px-8 py-2.5">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Clock className="h-4 w-4 text-indigo-600" />
        <span className="font-semibold text-indigo-900">Time machine</span>
        <span className="text-slate-500">·</span>
        <span className="text-slate-700">Today is</span>
        <span className="font-bold text-slate-900">{clock ? nice(clock.today) : "…"}</span>
        {clock?.simulated && <span className="rounded-full bg-violet-600 px-2 py-0.5 text-xs font-semibold text-white">simulated</span>}
        {provenNoDuplicates && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
            <ShieldCheck className="h-3.5 w-3.5" /> No double billing
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={runBilling}
          disabled={busy !== null}
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-60"
        >
          {busy === "bill" ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
          Run billing
        </button>
        {STEPS.map((s) => (
          <button
            key={s.days}
            onClick={() => advance(s.days)}
            disabled={busy !== null}
            className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-indigo-700 shadow-sm ring-1 ring-indigo-200 transition hover:bg-indigo-600 hover:text-white disabled:opacity-60"
          >
            {busy === s.days ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <FastForward className="h-3.5 w-3.5" />}
            {s.label}
          </button>
        ))}
        <button onClick={reset} disabled={busy !== null} title="Back to real date" className="rounded-lg p-1.5 text-slate-400 transition hover:bg-white hover:text-slate-700 disabled:opacity-60">
          {busy === "reset" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}