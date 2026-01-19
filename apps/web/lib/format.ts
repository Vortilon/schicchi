export function numClass(v: number | null | undefined) {
  if (v == null) return "text-slate-900";
  if (v > 0) return "text-emerald-700";
  if (v < 0) return "text-red-600";
  return "text-slate-900";
}

export function fmtMoney(v: number | null | undefined) {
  if (v == null) return "-";
  const sign = v < 0 ? "-" : "";
  const abs = Math.abs(v);
  return `${sign}$${abs.toFixed(2)}`;
}

export function fmtPct(v: number | null | undefined) {
  if (v == null) return "-";
  return `${(v * 100).toFixed(2)}%`;
}

