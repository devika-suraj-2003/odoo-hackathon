const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });

export function formatINR(paise: number | null | undefined) {
  return inr.format((paise ?? 0) / 100);
}

export function toPaise(rupees: string | number) {
  const n = typeof rupees === "number" ? rupees : parseFloat(rupees);
  return Number.isFinite(n) ? Math.round(n * 100) : 0;
}

export function toRupees(paise: number | null | undefined) {
  return paise ? String(paise / 100) : "";
}