// A bot's rules in words, written here as the engine writes them (describe() in engine.py), so the
// editor can say what a change does while the member moves a control; and two versions of the
// rules side by side, line by line: what stays, what goes, what comes.
import type { Bot, Factor } from "./types";

export const PERCENT = new Set(["momentum", "trend", "sma_cross", "volatility", "drawdown"]);

export function figure(name: string, v: number): string {
  if (PERCENT.has(name)) {
    const s = `${v * 100 >= 0 ? "+" : ""}${(v * 100).toFixed(0)}%`;
    return s.replace("+0%", "0%").replace("-0%", "0%").replace("-", "−");
  }
  return String(+v.toPrecision(6)).replace("-", "−");
}

export function what(f: Factor): string {
  const n = f as Record<string, number | string | undefined>;
  switch (f.factor) {
    case "momentum":
      return `its return over ${n.days} sessions` + (n.skip ? `, leaving out the last ${n.skip}` : "");
    case "sma_cross":
      return `its ${n.fast}-session average against its ${n.slow}-session one`;
    case "trend":
      return `its close against its ${n.days}-session average`;
    case "volatility":
      return `its volatility over ${n.days} sessions`;
    case "rsi":
      return `its RSI over ${n.days} sessions`;
    case "drawdown":
      return `how far it is under its high of ${n.days} sessions`;
    case "beta":
      return `its beta to the S&P 500 over ${n.days} sessions`;
  }
  return f.factor;
}

export function range(f: Factor): string {
  const { min, max } = f;
  if (min != null && max != null) return `between ${figure(f.factor, min)} and ${figure(f.factor, max)}`;
  return min != null ? `at least ${figure(f.factor, min)}` : `at most ${figure(f.factor, max ?? 0)}`;
}

const PARTS: Record<string, string> = { equal: "in equal parts", inverse_volatility: "the calmer ones with more", score: "the best scored with more" };
const AGAIN: Record<string, string> = {
  daily: "Looks again at every close.", weekly: "Looks again at the first close of each week.", monthly: "Looks again at the first close of each month.",
};

export function describe(bot: Bot): string[] {
  const u = bot.universe;
  const out: string[] = [];
  if (u.largest != null) out.push(`Looks at the ${u.largest} largest US companies` + (u.exclude.length ? `, leaving out ${u.exclude.join(", ")}.` : "."));
  else {
    const names = (u.tickers ?? []).filter((t) => !u.exclude.includes(t));
    out.push(`Looks at ${names.length} companies: ${names.slice(0, 12).join(", ")}${names.length > 12 ? "…" : ""}.`);
  }
  for (const f of bot.filters) out.push(`Keeps those where ${what(f)} is ${range(f)}.`);
  out.push("Scores them on " + bot.score.map((s) => `${what(s)} (${(s.weight ?? 0) > 0 ? "higher" : "lower"} is better, weight ${Math.abs(s.weight ?? 0)})`).join("; ") + ".");
  const cap = bot.max_weight < 1 ? `, none above ${(bot.max_weight * 100).toFixed(0)}%` : "";
  out.push(`Holds the best ${bot.hold}, ${PARTS[bot.weighting] ?? bot.weighting}${cap}.`);
  out.push(AGAIN[bot.rebalance] ?? "");
  if (bot.market) out.push(`When, for the S&P 500, ${what(bot.market)} is not ${range(bot.market)}, holds ${((bot.market.cash ?? 1) * 100).toFixed(0)}% in cash.`);
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
