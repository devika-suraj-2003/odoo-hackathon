import { useEffect, useRef, useState } from "react";

/**
 * Counts a displayed value up to its new number, keeping its prefix and suffix
 * ("₹5,000.00", "18%", "12"). Text without a number is shown as is.
 */
const NUMBER = /^([^\d-]*)(-?[\d,]+(?:\.\d+)?)(.*)$/;

function parts(value: string) {
  const m = value.match(NUMBER);
  if (!m) return null;
  const [, pre, num, post] = m;
  return { pre, post, target: parseFloat(num.replace(/,/g, "")), decimals: (num.split(".")[1] ?? "").length };
}

export default function AnimatedValue({ value, duration = 900 }: { value: string; duration?: number }) {
  const first = parts(value);
  const fmt = (n: number, decimals: number) => n.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  const [shown, setShown] = useState(first ? first.pre + fmt(0, first.decimals) + first.post : value);
  const previous = useRef(0);

  useEffect(() => {
    const p = parts(value);
    if (!p) {
      setShown(value);
      return;
    }
    const from = previous.current;
    previous.current = p.target;
    const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce || from === p.target) {
      setShown(value);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - k, 3);
      setShown(p.pre + fmt(from + (p.target - from) * eased, p.decimals) + p.post);
      if (k < 1) raf = requestAnimationFrame(tick);
      else setShown(value);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);

  return <span className="tabular-nums">{shown}</span>;
}
