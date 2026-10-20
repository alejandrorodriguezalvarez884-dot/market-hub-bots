// Number and date formatting. Every formatter takes null and returns an em dash for it.
export type N = number | null | undefined;
const DASH = "—";
const ok = (v: N): v is number => typeof v === "number" && Number.isFinite(v);

export function pct(v: N, digits = 1, signed = false): string {
  if (!ok(v)) return DASH;
  const s = (v * 100).toFixed(digits);
  return `${signed && v > 0 ? "+" : ""}${s.replace("-", "−")}%`;
}
export const signedPct = (v: N, digits = 1) => pct(v, digits, true);
export const tone = (v: N) => (ok(v) ? (v > 0 ? "text-up" : v < 0 ? "text-down" : "text-ink") : "text-faint");

export function day(iso: string | null | undefined): string {
  if (!iso) return DASH;
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
}

export function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
}

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 90) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} minutes ago`;
  if (s < 86400 * 1.5) return `${Math.round(s / 3600)} hours ago`;
  return `${Math.round(s / 86400)} days ago`;
}

export const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
