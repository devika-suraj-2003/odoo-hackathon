import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Clock, FastForward, RotateCcw, LoaderCircle } from "lucide-react";
import api from "../api/client";
import { errorMessage } from "../api/errors";

type Clock = { today: string; simulated?: boolean };

const STEPS = [
  { days: 1, label: "+1 day" },
  { days: 7, label: "+1 week" },
  { days: 30, label: "+1 month" },
];

function nice(d: string) {
  return new Date(d).toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
}

export default function TimeMachineBar({ onChanged }: { onChanged: () => void }) {
  const [clock, setClock] = useState<Clock | null>(null);
  const [available, setAvailable] = useState(true);
  const [busy, setBusy] = useState<number | "reset" | null>(null);

  useEffect(() => {
    api
      .get("/settings/clock")
      .then(({ data }) => {
        if (data && data.today) setClock(data);
        else setAvailable(false);
      })
      .catch(() => setAvailable(false));
  }, []);

  async function advance(days: number) {
    setBusy(days);
    try {
      const { data } = await api.post("/settings/clock/advance", { days });
      setClock({ today: data.today, simulated: true });
      const n = data.invoices_created ?? 0;
      toast.success(`Jumped to ${nice(data.today)} · ${n} invoice${n === 1 ? "" : "s"} created`, { duration: 4000 });
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
      const { data } = await api.post("/settings/clock/reset");
      setClock({ today: data.today, simulated: false });
      toast.success("Back to the real date");
      onChanged();
    } catch (err) {
      toast.error(errorMessage(err, "Could not reset time"));
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

  return (
    <div className="no-print flex flex-wrap items-center justify-between gap-3 border-b border-indigo-100 bg-linear-to-r from-indigo-50 to-violet-50 px-8 py-2.5">
      <div className="flex items-center gap-2 text-sm">
        <Clock className="h-4 w-4 text-indigo-600" />
        <span className="font-semibold text-indigo-900">Time machine</span>
        <span className="text-slate-500">·</span>
        <span className="text-slate-700">Today is</span>
        <span className="font-bold text-slate-900">{clock ? nice(clock.today) : "…"}</span>
        {clock?.simulated && <span className="rounded-full bg-violet-600 px-2 py-0.5 text-xs font-semibold text-white">simulated</span>}
      </div>
      <div className="flex items-center gap-2">
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
        <button
          onClick={reset}
          disabled={busy !== null}
          title="Back to real date"
          className="rounded-lg p-1.5 text-slate-400 transition hover:bg-white hover:text-slate-700 disabled:opacity-60"
        >
          {busy === "reset" ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}