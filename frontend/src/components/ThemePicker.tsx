import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Palette } from "lucide-react";
import { PALETTES, applyPalette, getPalette } from "../lib/theme";

export default function ThemePicker() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState(getPalette());
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  function pick(id: string) {
    applyPalette(id);
    setCurrent(id);
  }

  return (
    <div ref={ref} className="relative">
      <motion.button
        whileTap={{ scale: 0.9 }}
        onClick={() => setOpen((o) => !o)}
        title="Colour theme"
        className="bl-palette-btn grid h-10 w-10 place-items-center rounded-xl border border-slate-200 bg-white shadow-sm transition"
      >
        <Palette className="h-4 w-4 text-white" />
      </motion.button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.96 }}
            transition={{ duration: 0.16 }}
            className="absolute right-0 top-12 z-50 w-56 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl"
          >
            <p className="px-2 pb-2 pt-1 text-xs font-semibold uppercase tracking-wider text-slate-400">Colour theme</p>
            {PALETTES.map((p) => (
              <button
                key={p.id}
                onClick={() => pick(p.id)}
                className={`flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left text-sm font-medium transition hover:bg-slate-50 ${
                  current === p.id ? "text-slate-900" : "text-slate-600"
                }`}
              >
                <span
                  className="h-7 w-7 shrink-0 rounded-lg shadow-sm ring-2 ring-white"
                  style={{ background: `linear-gradient(135deg, ${p.colors[0]}, ${p.colors[1]}, ${p.colors[2]})` }}
                />
                <span className="flex-1">{p.name}</span>
                {current === p.id && <Check className="h-4 w-4 text-emerald-500" />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
