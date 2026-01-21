export function numClass(v: number | null | undefined) {
  if (v == null) return "text-slate-900";
  if (v > 0) return "text-emerald-700";
  if (v < 0) return "text-red-600";
  return "text-slate-900";
}

export function fmtMoney(v: number | null | undefined) {
  if (v == null) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(v);
}

export function fmtPct(v: number | null | undefined) {
  if (v == null) return "-";
  return `${(v * 100).toFixed(2)}%`;
}

export function fmtNum(v: number | null | undefined, decimals = 2) {
  if (v == null) return "-";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(v);
}

export function fmtTimeEST(iso: string | null | undefined) {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true
  }).format(d);
}

