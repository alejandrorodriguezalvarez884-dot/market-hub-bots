// The board, as the landing and the board page draw it: the members' bots ranked over a period,
// with the house bots and the index between them as lines of reference, never ranked.
import { add, h } from "./dom";
import { sparkline } from "./chart";
import { indexFace, robot } from "./robot";
import { plural, signedPct, tone } from "./format";
import { botUrl } from "./site";
import { digits, type Board, type Line, type Period } from "./types";

export type Entry = { kind: "bot"; line: Line; value: number | null } | { kind: "index"; value: number | null };

export function ordered(b: Board, period: Period): Entry[] {
  const bots: Entry[] = [...b.rows, ...b.house].map((line) => ({ kind: "bot" as const, line, value: line.returns[period] }));
  const bench = period === "all" ? null : b.benchmark.returns?.[period] ?? null;
  const entries: Entry[] = bench == null ? bots : [...bots, { kind: "index", value: bench }];
  return entries.sort((x, y) => (x.value == null ? 1 : 0) - (y.value == null ? 1 : 0) || (y.value ?? 0) - (x.value ?? 0));
}

// One line: rank, who, a sparkline since it started, the return over the period.
export function row(e: Entry, period: Period, ticker: string): HTMLElement {
  if (e.kind === "index") {
    return add(h("div", "board-row ref"), h("span", "num text-[12px] text-faint", "—"),
      add(h("span", "flex min-w-0 items-center gap-2.5"), indexFace(28), add(h("span", "min-w-0 truncate"), h("span", "text-muted", "S&P 500"), h("span", "tag ml-2", ticker))),
      h("span", ""), h("span", `num text-right font-semibold opacity-80 ${tone(e.value)}`, signedPct(e.value, digits(period))));
  }
  const r = e.line;
  const rank = r.ranks[period];
  const el = h("a", `board-row ${r.house ? "ref" : ""} ${r.you ? "you" : ""}`);
  el.href = botUrl(r.slug);
  add(el, h("span", "num text-[12px] text-muted", rank ? String(rank) : r.house ? "·" : ""),
    add(h("span", "flex min-w-0 items-center gap-2.5"), robot(r.slug, 28), add(h("span", "min-w-0"),
      add(h("span", "flex min-w-0 items-center gap-2"), h("span", `truncate font-semibold ${r.house ? "text-ink" : "text-ink-strong"}`, r.name),
        r.house ? h("span", "tag shrink-0", "house") : null, r.you ? h("span", "tag tag-you shrink-0", "you") : null),
      h("span", "block truncate text-[12px] text-muted", r.house ? "Bot League · from the kit" : `by ${r.handle}`))),
    add(h("span", "flex justify-end"), sparkline(r.spark)),
    h("span", `num text-right font-semibold ${tone(e.value)}`, e.value == null ? (r.since ? "—" : "next close") : signedPct(e.value, digits(period))));
  return el;
}

// Where the members' bots would be, for a visitor who cannot see them.
export function locked(b: Board, signin: string | null): HTMLElement {
  const text = add(h("span", "col-span-3 min-w-0"),
    h("span", "font-semibold text-ink-strong", b.entrants ? `${plural(b.entrants, "member's bot", "members' bots")} in the race` : "Members' bots"),
    h("span", "block text-[12.5px] text-muted", b.entrants ? "Sign in with your account on The Market Hub to see who leads. " : "None yet: yours can be the first."));
  if (signin && b.entrants) {
    const a = h("a", "text-[12.5px] text-signal hover:text-signal-strong", "Sign in →");
    a.href = signin;
    text.lastElementChild!.append(a);
  }
  return add(h("div", "board-row you"), h("span", "text-signal", "◆"), text);
}

export function periodTabs(current: Period, periods: { key: Period; label: string }[], pick: (p: Period) => void): HTMLElement {
  const nav = h("div", "tabs");
  for (const p of periods) {
    const t = h("button", "tab-btn", p.label);
    t.type = "button";
    t.setAttribute("aria-selected", String(p.key === current));
    t.addEventListener("click", () => pick(p.key));
    nav.append(t);
  }
  return nav;
}
