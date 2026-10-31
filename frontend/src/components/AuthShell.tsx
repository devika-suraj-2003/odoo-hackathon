import type { ReactNode } from "react";
import { CircleCheck } from "lucide-react";

const points = [
  "Plans, products and quotation templates",
  "Automatic invoices with GST, never billed twice",
  "Payments, overdue tracking and live revenue",
];

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
    <div className="min-h-screen lg:grid lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-linear-to-br from-indigo-600 via-indigo-700 to-violet-700 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-20 h-96 w-96 rounded-full bg-violet-400/20 blur-3xl" />

        <div className="relative flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-white text-lg font-extrabold text-indigo-700">
            B
          </div>
          <span className="text-lg font-bold">Brightloop</span>
        </div>

        <div className="relative max-w-md">
          <h1 className="text-4xl font-extrabold leading-tight">
            Run plans, subscriptions and billing in one place.
          </h1>
          <ul className="mt-8 space-y-4">
            {points.map((p) => (
              <li key={p} className="flex items-center gap-3 text-indigo-50">
                <CircleCheck className="h-5 w-5 shrink-0 text-emerald-300" />
                {p}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-sm text-indigo-200">© 2026 Brightloop Software</p>
      </div>

      <div className="flex min-h-screen items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-linear-to-br from-indigo-600 to-violet-600 text-lg font-extrabold text-white">
              B
            </div>
            <span className="text-lg font-bold text-slate-900">Brightloop</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  );
}