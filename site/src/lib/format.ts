// Number and date formatting, in the page's language. Every formatter takes null and returns an
// em dash for it. English "+30.5%", "Nov 4, 2026"; Spanish "+30,5 %", "4 nov 2026".
import { lang, locale } from "../i18n";

export type N = number | null | undefined;
const DASH = "—";
const ok = (v: N): v is number => typeof v === "number" && Number.isFinite(v);

// A plain number with the page's separators: 1,234.5 or 1.234,5.
export function num(v: N, digits = 0): string {
  if (!ok(v)) return DASH;
  return v.toLocaleString(locale(), { minimumFractionDigits: digits, maximumFractionDigits: digits }).replace("-", "−");
}

export function pct(v: N, digits = 1, signed = false): string {
  if (!ok(v)) return DASH;
  const s = (v * 100).toFixed(digits);
  const shown = lang() === "es" ? `${s.replace(".", ",")} %` : `${s}%`;
  return `${signed && v > 0 ? "+" : ""}${shown.replace("-", "−")}`;
}
export const signedPct = (v: N, digits = 1) => pct(v, digits, true);
export const tone = (v: N) => (ok(v) ? (v > 0 ? "text-up" : v < 0 ? "text-down" : "text-ink") : "text-faint");

export function day(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (lang() === "es") {
    // "4 nov 2026": the short month without its full stop.
    return d.toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).replace(".", "");
  }
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
}

export function ordinal(n: number): string {
  if (lang() === "es") return `${n}.º`;
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
}

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  const es = lang() === "es";
  if (s < 90) return es ? "hace un momento" : "just now";
  if (s < 3600) return es ? `hace ${Math.round(s / 60)} minutos` : `${Math.round(s / 60)} minutes ago`;
  if (s < 86400 * 1.5) return es ? `hace ${Math.round(s / 3600)} horas` : `${Math.round(s / 3600)} hours ago`;
  return es ? `hace ${Math.round(s / 86400)} días` : `${Math.round(s / 86400)} days ago`;
}

// "3 stocks" / "3 valores": the count and the right form of the word. The words come from the
// caller, in the page's language.
export const plural = (n: number, one: string, many = `${one}s`) => `${num(n)} ${n === 1 ? one : many}`;
