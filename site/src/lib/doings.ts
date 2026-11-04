// What a bot holds and does, drawn the same on its page and on its owner's: bars of weights, its
// rebalances, its holdings over time and when its rules changed.
import { add, h } from "./dom";
import { day, pct, plural } from "./format";
import { hubQuoteUrl } from "./site";
import type { Move, Version } from "./types";
import { lang } from "../i18n";
import { common } from "../i18n/common";

const w = () => common[lang()];

const share = (w: number) => pct(w, w < 0.1 ? 1 : 0);

// One bar per holding, the largest first, and the cash under them.
export function bars(weights: Record<string, number>, cash?: number | null): HTMLElement {
  const rows = Object.entries(weights).sort((a, b) => b[1] - a[1]);
  const left = cash ?? Math.max(0, 1 - rows.reduce((s, [, w]) => s + w, 0));
  const top = Math.max(...rows.map(([, w]) => w), left, 0.01);
  const bar = (label: Node | string, w: number, muted = false) => add(h("div", "grid grid-cols-[4.5rem_minmax(0,1fr)_3.6rem] items-center gap-3 py-1"),
    typeof label === "string" ? h("span", "num text-[13px] text-muted", label) : label,
    add(h("span", "h-2 rounded-sm bg-line"), Object.assign(h("span", `block h-2 rounded-sm ${muted ? "bg-faint" : "bg-ink"}`), { style: `width:${(w / top) * 100}%` })),
    h("span", "num text-right text-[13px] text-ink", share(w)));
  const out = rows.map(([t, w]) => bar(Object.assign(h("a", "num text-[13px] font-medium text-ink-strong hover:underline", t), { href: hubQuoteUrl(t) }), w));
  if (left > 0.005) out.push(bar(w().cash, left, true));
  return add(h("div", "max-w-2xl"), ...out);
}

// Its rebalances, the latest first: what it bought, sold, raised and cut, and what that cost.
export function moves(log: Move[], shown = 12): HTMLElement {
  const t = w();
  if (!log.length) return h("p", "text-[13px] text-muted", t.noRebalance);
  const chip = (text: string, cls = "") => h("span", `chip ${cls}`, text);
  const list = add(h("ol", "divide-y divide-line border-y border-line"), ...log.slice(0, shown).map((m) => {
    const parts = [
      ...m.bought.map((x) => chip(`+ ${x.ticker} ${share(x.weight)}`, "text-ink-strong")),
      ...m.sold.map((x) => chip(`− ${x.ticker}`, "text-muted")),
      ...m.raised.map((x) => chip(`↑ ${x.ticker} ${share(x.before)} → ${share(x.after)}`)),
      ...m.cut.map((x) => chip(`↓ ${x.ticker} ${share(x.before)} → ${share(x.after)}`)),
    ];
    const cash = !Object.keys(m.after).length;
    return add(h("li", "grid gap-2 py-3 sm:grid-cols-[8.5rem_minmax(0,1fr)_9rem] sm:items-baseline"),
      h("span", "num text-[13px] text-ink-strong", day(m.date)),
      add(h("span", "flex flex-wrap gap-1.5"), ...(parts.length ? parts : [h("span", "text-[13px] text-muted", `${cash ? t.wentToCash : t.weightsBack}.`)])),
      h("span", "num text-[12.5px] text-muted sm:text-right", t.tradedCost(pct(m.turnover, 0), pct(m.cost, 2))));
  }));
  const box = add(h("div"), list);
  if (log.length > shown) {
    const more = h("button", "btn btn-ghost mt-3 py-1.5 text-[13px]", t.showMore(log.length));
    more.type = "button";
    more.addEventListener("click", () => box.replaceWith(moves(log, shown + 24)));
    box.append(more);
  }
  return box;
}

// What it held after each rebalance, oldest on the left: a row per company it held most, darker
// for more.
export function strip(log: Move[], columns = 30, rows = 12): HTMLElement | null {
  const w0 = w();
  const seq = log.slice(0, columns).reverse();
  if (seq.length < 2) return null;
  const total: Record<string, number> = {};
  for (const m of seq) for (const [t, w] of Object.entries(m.after)) total[t] = (total[t] ?? 0) + w;
  const names = Object.keys(total).sort((a, b) => total[b] - total[a]).slice(0, rows);
  const grid = h("div", "grid items-center gap-[2px] text-[12px]");
  grid.style.gridTemplateColumns = `4.5rem repeat(${seq.length}, minmax(6px, 1fr))`;
  for (const t of names) {
    grid.append(h("span", "num truncate text-muted", t));
    for (const m of seq) {
      const w = m.after[t] ?? 0;
      const cell = h("span", "block h-4 rounded-[2px]");
      cell.style.background = w ? `rgb(242 240 234 / ${Math.min(0.9, 0.15 + w * 2.2).toFixed(2)})` : "var(--color-raised)";
      cell.title = `${t}, ${day(m.date)}: ${w ? share(w) : w0.notHeld}`;
      grid.append(cell);
    }
  }
  return add(h("div", "overflow-x-auto"), grid,
    add(h("div", "mt-2 flex justify-between text-[12px] text-faint"), h("span", "num", day(seq[0].date)), h("span", "num", day(seq[seq.length - 1].date))));
}

// The changes the service names ("rules", "paused", "resumed", "excluded NVDA", "included NVDA",
// "renamed from Old name"), in the page's language. Anything else is shown as it comes.
function sayOne(what: string): string {
  const t = w().said;
  if (what === "rules" || what === "paused" || what === "resumed") return t[what];
  const m = /^(excluded|included|renamed from) (.+)$/.exec(what);
  if (!m) return what;
  return m[1] === "excluded" ? t.excluded(m[2]) : m[1] === "included" ? t.included(m[2]) : t.renamed(m[2]);
}
export const said = (what: string[]) => what.map(sayOne).join(" · ");
// A version that only renamed the bot (the service writes "renamed from …").
const renamedOnly = (what: string[]) => what.every((x) => x.startsWith("renamed"));

// When its rules changed, and the switches pressed, from the close each applied.
export function versions(list: Version[]): HTMLElement {
  const t = w();
  if (!list.length) return h("p", "text-[13px] text-muted", t.noChanges);
  return add(h("ul", "space-y-1.5 text-[13px]"), ...list.slice().reverse().map((v) =>
    add(h("li", "flex flex-wrap gap-x-3"), h("span", "num text-ink-strong", renamedOnly(v.what) ? day(v.from) : t.fromClose(day(v.from))),
      h("span", "text-ink", said(v.what)))));
}

export const holdingCount = (weights: Record<string, number>) => plural(Object.keys(weights).length, ...w().stock);
