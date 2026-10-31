/**
 * Brightloop logo mark: a loop (recurring billing) with a spark (bright) in its gap.
 * Drawn in currentColor so it works on the red tile, on black, or on white.
 */
export function LoopMark({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden>
      {/* the loop: a ring with an opening at the top right */}
      <circle
        className="bl-mark-ring"
        cx="16"
        cy="16"
        r="9.5"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray="43.94 15.75"
        transform="rotate(2.5 16 16)"
      />
      {/* the spark sitting in the opening */}
      <path className="bl-mark-spark" d="M22.72 4.68 Q23.02 8.98 27.32 9.28 Q23.02 9.58 22.72 13.88 Q22.42 9.58 18.12 9.28 Q22.42 8.98 22.72 4.68 Z" fill="currentColor" />
    </svg>
  );
}

/** Logo tile: red gradient square with the white mark. */
export default function BrandMark({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const box = size === "lg" ? "h-11 w-11 rounded-2xl" : size === "sm" ? "h-9 w-9 rounded-xl" : "h-10 w-10 rounded-2xl";
  const icon = size === "lg" ? "h-7 w-7" : size === "sm" ? "h-5 w-5" : "h-6 w-6";
  return (
    <div className={`bl-logo bl-mark group relative grid shrink-0 place-items-center text-white ${box}`}>
      <LoopMark className={icon} />
      <span className={`pointer-events-none absolute inset-0 ring-1 ring-inset ring-white/25 ${box}`} />
    </div>
  );
}

/** Word mark: "Bright" + "loop" in the accent colour. */
export function Wordmark({ light, className = "" }: { light?: boolean; className?: string }) {
  return (
    <span className={`font-extrabold tracking-tight ${light ? "text-white" : "text-slate-900"} ${className}`}>
      Bright<span className="bl-wordmark-accent">loop</span>
    </span>
  );
}
