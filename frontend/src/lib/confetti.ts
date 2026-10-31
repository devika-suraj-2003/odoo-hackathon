import { paletteColors } from "./theme";

/** Small confetti burst drawn on a temporary canvas. No library needed. */
export function fireConfetti() {
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

  const canvas = document.createElement("canvas");
  canvas.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:9999";
  const dpr = window.devicePixelRatio || 1;
  canvas.width = window.innerWidth * dpr;
  canvas.height = window.innerHeight * dpr;
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.scale(dpr, dpr);

  const colors = [...paletteColors(), "#facc15", "#22c55e"];
  const W = window.innerWidth;
  const H = window.innerHeight;
  const pieces = Array.from({ length: 160 }, (_, i) => {
    const fromLeft = i % 2 === 0;
    return {
      x: fromLeft ? 0 : W,
      y: H * 0.7,
      vx: (fromLeft ? 1 : -1) * (6 + Math.random() * 9),
      vy: -(10 + Math.random() * 12),
      size: 6 + Math.random() * 6,
      rot: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.3,
      color: colors[i % colors.length],
      round: Math.random() > 0.6,
    };
  });

  const start = performance.now();
  const frame = (t: number) => {
    const elapsed = t - start;
    ctx.clearRect(0, 0, W, H);
    for (const p of pieces) {
      p.vy += 0.35;
      p.vx *= 0.985;
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vr;
      ctx.save();
      ctx.globalAlpha = Math.max(0, 1 - elapsed / 2600);
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      if (p.round) {
        ctx.beginPath();
        ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
      }
      ctx.restore();
    }
    if (elapsed < 2600) requestAnimationFrame(frame);
    else canvas.remove();
  };
  requestAnimationFrame(frame);
}
