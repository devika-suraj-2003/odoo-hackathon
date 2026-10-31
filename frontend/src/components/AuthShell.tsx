import type { ReactNode } from "react";
import { motion } from "framer-motion";
import BrandMark, { Wordmark } from "./BrandMark";
import { CircleCheck, Sparkles, Receipt, CalendarClock, ShieldCheck } from "lucide-react";

const points = [
  "Plans, products and quotation templates",
  "Automatic invoices with GST, never billed twice",
  "Payments, overdue tracking and live revenue",
];

const ease = [0.22, 1, 0.36, 1] as const;

function Logo({ light }: { light?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <BrandMark size="lg" />
      <Wordmark light={light} className="text-xl" />
    </div>
  );
}

export default function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#f5f6fb] lg:grid lg:grid-cols-[1.1fr_1fr]">
      {/* ---------- Left: brand panel ---------- */}
      <div className="bl-auth-panel relative hidden overflow-hidden p-12 text-white lg:flex lg:flex-col lg:justify-between">
        {/* aurora */}
        <motion.div
          className="bl-glow-a pointer-events-none absolute -left-40 -top-40 h-[34rem] w-[34rem] rounded-full blur-[120px]"
          animate={{ x: [0, 60, 0], y: [0, 40, 0] }}
          transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="bl-glow-c pointer-events-none absolute -bottom-48 right-[-10rem] h-[36rem] w-[36rem] rounded-full blur-[130px]"
          animate={{ x: [0, -50, 0], y: [0, -30, 0] }}
          transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="pointer-events-none absolute left-1/3 top-1/2 h-72 w-72 rounded-full bg-sky-500/25 blur-[100px]"
          animate={{ scale: [1, 1.25, 1] }}
          transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* grid texture */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.12]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.35) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.35) 1px, transparent 1px)",
            backgroundSize: "44px 44px",
            maskImage: "radial-gradient(ellipse at 40% 40%, black 30%, transparent 75%)",
            WebkitMaskImage: "radial-gradient(ellipse at 40% 40%, black 30%, transparent 75%)",
          }}
        />

        <motion.div className="relative" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease }}>
          <Logo light />
        </motion.div>

        <div className="relative max-w-xl">
          <motion.span
            className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold text-indigo-100 backdrop-blur"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.6, ease }}
          >
            <Sparkles className="h-3.5 w-3.5 text-amber-300" /> Subscription billing, on autopilot
          </motion.span>
          <motion.h1
            className="mt-6 text-5xl font-extrabold leading-[1.05] tracking-tight"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18, duration: 0.7, ease }}
          >
            Run plans, subscriptions and{" "}
            <span className="bl-gradient-text">billing in one place.</span>
          </motion.h1>
          <ul className="mt-10 space-y-4">
            {points.map((p, i) => (
              <motion.li
                key={p}
                className="flex items-center gap-3 text-indigo-100/90"
                initial={{ opacity: 0, x: -14 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.35 + i * 0.1, duration: 0.5, ease }}
              >
                <span className="grid h-7 w-7 place-items-center rounded-full bg-emerald-400/15 ring-1 ring-emerald-300/30">
                  <CircleCheck className="h-4 w-4 text-emerald-300" />
                </span>
                {p}
              </motion.li>
            ))}
          </ul>

          {/* floating product illustration cards */}
          <div className="relative mt-12 h-40">
            <motion.div
              className="absolute left-0 top-0 w-64 rounded-2xl border border-white/15 bg-white/10 p-4 shadow-2xl backdrop-blur-xl"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: [0, -8, 0] }}
              transition={{ opacity: { delay: 0.6, duration: 0.6 }, y: { delay: 0.6, duration: 6, repeat: Infinity, ease: "easeInOut" } }}
            >
              <div className="flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-emerald-400/20">
                  <Receipt className="h-4 w-4 text-emerald-300" />
                </span>
                <div>
                  <p className="text-sm font-semibold">Invoice paid</p>
                  <p className="text-xs text-indigo-200/80">GST split applied automatically</p>
                </div>
              </div>
            </motion.div>
            <motion.div
              className="absolute left-56 top-16 w-60 rounded-2xl border border-white/15 bg-white/10 p-4 shadow-2xl backdrop-blur-xl"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: [0, 8, 0] }}
              transition={{ opacity: { delay: 0.8, duration: 0.6 }, y: { delay: 0.8, duration: 7, repeat: Infinity, ease: "easeInOut" } }}
            >
              <div className="flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-400/25">
                  <CalendarClock className="h-4 w-4 text-indigo-200" />
                </span>
                <div>
                  <p className="text-sm font-semibold">Renewal scheduled</p>
                  <p className="text-xs text-indigo-200/80">Billed once per period</p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>

        <div className="relative flex items-center justify-between text-sm text-indigo-200/70">
          <p>© 2026 Brightloop Software</p>
          <p className="inline-flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4" /> Role-based secure access
          </p>
        </div>
      </div>

      {/* ---------- Right: form ---------- */}
      <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-5 py-12">
        <div className="bl-glow-a pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full opacity-40 blur-[100px]" />
        <div className="bl-glow-c pointer-events-none absolute -bottom-40 -left-24 h-96 w-96 rounded-full opacity-30 blur-[110px]" />
        <motion.div
          className="relative w-full max-w-md rounded-3xl border border-white/70 bg-white/75 p-8 shadow-[0_30px_80px_-30px_rgba(49,46,129,0.35)] backdrop-blur-xl sm:p-10"
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.6, ease }}
        >
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight text-slate-900">{title}</h2>
          {subtitle && <p className="mt-2 text-sm text-slate-500">{subtitle}</p>}
          <div className="mt-8">{children}</div>
        </motion.div>
      </div>
    </div>
  );
}
