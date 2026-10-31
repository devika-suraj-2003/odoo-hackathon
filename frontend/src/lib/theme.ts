export type Palette = { id: string; name: string; colors: [string, string, string] };

// Forest Finance design system. "forest" is the default.
export const PALETTES: Palette[] = [
  { id: "forest", name: "Forest", colors: ["#14532d", "#16a34a", "#ffffff"] },
  { id: "slate", name: "Slate", colors: ["#1e293b", "#16a34a", "#ffffff"] },
];

export function getPalette(): string {
  try {
    const saved = localStorage.getItem("palette");
    return PALETTES.some((p) => p.id === saved) ? (saved as string) : "forest";
  } catch {
    return "forest";
  }
}

export function applyPalette(id: string) {
  document.documentElement.dataset.palette = id;
  try {
    localStorage.setItem("palette", id);
  } catch {}
}

export function paletteColors(): string[] {
  return ["#166534", "#16a34a", "#22c55e", "#dcfce7", "#0d9488", "#facc15"];
}
