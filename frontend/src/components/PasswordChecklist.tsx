import { Check, X } from "lucide-react";

export const PASSWORD_RULES: { label: string; test: (p: string) => boolean }[] = [
  { label: "More than 8 characters", test: (p) => p.length > 8 },
  { label: "One uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { label: "One lowercase letter", test: (p) => /[a-z]/.test(p) },
  { label: "One special character", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

export function isStrongPassword(p: string) {
  return PASSWORD_RULES.every((r) => r.test(p));
}

export default function PasswordChecklist({ password }: { password: string }) {
  return (
    <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1.5">
      {PASSWORD_RULES.map((r) => {
        const ok = r.test(password);
        return (
          <li
            key={r.label}
            className={`flex items-center gap-1.5 text-xs ${ok ? "text-emerald-600" : "text-slate-400"}`}
          >
            {ok ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
            {r.label}
          </li>
        );
      })}
    </ul>
  );
}