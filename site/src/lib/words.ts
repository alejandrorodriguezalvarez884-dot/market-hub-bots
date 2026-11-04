// A bot's rules in words, written here as the engine writes them (describe() in engine.py), so the
// editor can say what a change does while the member moves a control; and two versions of the
// rules side by side, line by line: what stays, what goes, what comes. In the page's language,
// with the engine's templates (docs/i18n.md).
import { lang, type Lang } from "../i18n";
import type { Bot, Factor } from "./types";

export const PERCENT = new Set(["momentum", "trend", "sma_cross", "volatility", "drawdown"]);

export function figure(name: string, v: number, l: Lang = lang()): string {
  if (PERCENT.has(name)) {
    const s = `${v * 100 >= 0 ? "+" : ""}${(v * 100).toFixed(0)}%`;
    const out = s.replace("+0%", "0%").replace("-0%", "0%").replace("-", "−");
    return l === "es" ? out.replace("%", " %") : out;
  }
  const out = String(+v.toPrecision(6)).replace("-", "−");
  return l === "es" ? out.replace(".", ",") : out;
}

type Words = Record<string, (n: Record<string, number | string | undefined>) => string>;
const WHAT: Record<Lang, Words> = {
  en: {
    momentum: (n) => `its return over ${n.days} sessions` + (n.skip ? `, leaving out the last ${n.skip}` : ""),
    sma_cross: (n) => `its ${n.fast}-session average against its ${n.slow}-session one`,
    trend: (n) => `its close against its ${n.days}-session average`,
    volatility: (n) => `its volatility over ${n.days} sessions`,
    rsi: (n) => `its RSI over ${n.days} sessions`,
    drawdown: (n) => `how far it is under its high of ${n.days} sessions`,
    beta: (n) => `its beta to the S&P 500 over ${n.days} sessions`,
  },
  es: {
    momentum: (n) => `su rentabilidad en ${n.days} sesiones` + (n.skip ? `, sin contar las últimas ${n.skip}` : ""),
    sma_cross: (n) => `su media de ${n.fast} sesiones frente a la de ${n.slow}`,
    trend: (n) => `su cierre frente a su media de ${n.days} sesiones`,
    volatility: (n) => `su volatilidad en ${n.days} sesiones`,
    rsi: (n) => `su RSI en ${n.days} sesiones`,
    drawdown: (n) => `su caída desde su máximo de ${n.days} sesiones`,
    beta: (n) => `su beta al S&P 500 en ${n.days} sesiones`,
  },
};

export function what(f: Factor, l: Lang = lang()): string {
  const said = WHAT[l][f.factor];
  return said ? said(f as Record<string, number | string | undefined>) : f.factor;
}

const RULES = {
  en: {
    between: (a: string, b: string) => `between ${a} and ${b}`, least: (a: string) => `at least ${a}`, most: (b: string) => `at most ${b}`,
    largest: (n: number, out: string[]) => `Looks at the ${n} largest US companies` + (out.length ? `, leaving out ${out.join(", ")}.` : "."),
    tickers: (n: number, names: string) => `Looks at ${n} companies: ${names}.`,
    keeps: (w: string, r: string) => `Keeps those where ${w} is ${r}.`,
    scores: (terms: string[]) => "Scores them on " + terms.join("; ") + ".",
    term: (w: string, higher: boolean, weight: string) => `${w} (${higher ? "higher" : "lower"} is better, weight ${weight})`,
    holds: (n: number, parts: string, cap: string) => `Holds the best ${n}, ${parts}${cap}.`,
    cap: (x: string) => `, none above ${x}%`,
    parts: { equal: "in equal parts", inverse_volatility: "the calmer ones with more", score: "the best scored with more" } as Record<string, string>,
    again: {
      daily: "Looks again at every close.", weekly: "Looks again at the first close of each week.", monthly: "Looks again at the first close of each month.",
    } as Record<string, string>,
    market: (w: string, r: string, x: string) => `When, for the S&P 500, ${w} is not ${r}, holds ${x}% in cash.`,
  },
  es: {
    between: (a: string, b: string) => `entre ${a} y ${b}`, least: (a: string) => `al menos ${a}`, most: (b: string) => `como mucho ${b}`,
    largest: (n: number, out: string[]) => `Mira las ${n} mayores empresas de EE. UU.` + (out.length ? `, sin contar ${out.join(", ")}.` : ""),
    tickers: (n: number, names: string) => `Mira ${n} empresas: ${names}.`,
    keeps: (w: string, r: string) => `Se queda con aquellas en las que ${w} es ${r}.`,
    scores: (terms: string[]) => "Las puntúa por " + terms.join("; ") + ".",
    term: (w: string, higher: boolean, weight: string) => `${w} (mejor cuanto más ${higher ? "alto" : "bajo"}, peso ${weight})`,
    holds: (n: number, parts: string, cap: string) => (n === 1 ? `Mantiene la mejor, ${parts}${cap}.` : `Mantiene las ${n} mejores, ${parts}${cap}.`),
    cap: (x: string) => `, ninguna por encima del ${x} %`,
    parts: { equal: "a partes iguales", inverse_volatility: "con más peso para las más tranquilas", score: "con más peso para las mejor puntuadas" } as Record<string, string>,
    again: {
      daily: "Revisa la cartera en cada cierre.", weekly: "Revisa la cartera en el primer cierre de cada semana.",
      monthly: "Revisa la cartera en el primer cierre de cada mes.",
    } as Record<string, string>,
    market: (w: string, r: string, x: string) => `Cuando, para el S&P 500, ${w} no es ${r}, mantiene el ${x} % en liquidez.`,
  },
};

export function range(f: Factor, l: Lang = lang()): string {
  const { min, max } = f;
  const r = RULES[l];
  if (min != null && max != null) return r.between(figure(f.factor, min, l), figure(f.factor, max, l));
  return min != null ? r.least(figure(f.factor, min, l)) : r.most(figure(f.factor, max ?? 0, l));
}

export function describe(bot: Bot, l: Lang = lang()): string[] {
  const r = RULES[l];
  const u = bot.universe;
  const out: string[] = [];
  if (u.largest != null) out.push(r.largest(u.largest, u.exclude));
  else {
    const names = (u.tickers ?? []).filter((t) => !u.exclude.includes(t));
    out.push(r.tickers(names.length, `${names.slice(0, 12).join(", ")}${names.length > 12 ? "…" : ""}`));
  }
  for (const f of bot.filters) out.push(r.keeps(what(f, l), range(f, l)));
  out.push(r.scores(bot.score.map((s) => r.term(what(s, l), (s.weight ?? 0) > 0, figure("weight", Math.abs(s.weight ?? 0), l)))));
  const cap = bot.max_weight < 1 ? r.cap((bot.max_weight * 100).toFixed(0)) : "";
  out.push(r.holds(bot.hold, r.parts[bot.weighting] ?? bot.weighting, cap));
  out.push(r.again[bot.rebalance] ?? "");
  if (bot.market) out.push(r.market(what(bot.market, l), range(bot.market, l), ((bot.market.cash ?? 1) * 100).toFixed(0)));
  return out;
}

export type Line = { kind: "same" | "gone" | "new"; text: string };

// The two lists line by line, by their longest common run: the lines in both stay, the others go
// or come, each removed line right before the line that takes its place.
export function diff(before: string[], after: string[]): Line[] {
  const n = before.length, m = after.length;
  const L = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = before[i] === after[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out: Line[] = [];
  let gone: Line[] = [], come: Line[] = [];
  // Between two lines that stay, each line that goes is followed by the one that comes in its place.
  const flush = () => {
    for (let k = 0; k < Math.max(gone.length, come.length); k++) out.push(...[gone[k], come[k]].filter(Boolean));
    gone = [];
    come = [];
  };
  let i = 0, j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && before[i] === after[j]) flush(), out.push({ kind: "same", text: before[i++] }), j++;
    else if (i < n && (j >= m || L[i + 1][j] >= L[i][j + 1])) gone.push({ kind: "gone", text: before[i++] });
    else come.push({ kind: "new", text: after[j++] });
  }
  flush();
  return out;
}

export const changed = (lines: Line[]) => lines.some((l) => l.kind !== "same");
