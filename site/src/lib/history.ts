// A bot's portfolio close by close, the same on its owner's page and on its public page. One date
// at a time, picked with a slider: what it held then (a treemap, what it had just bought marked)
// and, in words, what changed that day. Under it every move as a list, the latest first; a tap on
// one takes the slider there. Changes of its rules sit among the moves, on their date.
import { add, h } from "./dom";
import { day, pct, plural } from "./format";
import { said } from "./doings";
import { treemap } from "./mybot";
import type { Move, Version } from "./types";
import { lang, locale } from "../i18n";
import { common } from "../i18n/common";
import { history as words } from "../i18n/history";

type Step = { date: string; weights: Record<string, number>; cash: number | null; move: Move | null; now: boolean };

const share = (w: number) => pct(w, w < 0.1 ? 1 : 0);
const list = (items: string[]) => new Intl.ListFormat(locale(), { type: "conjunction" }).format(items);
const LISTED = 8; // moves shown before "Show all"

// The dates to step through, oldest first: each rebalance, then today if it has run since.
function stepsOf(log: Move[], now: { weights: Record<string, number>; cash: number | null; as_of: string | null }): Step[] {
  const steps: Step[] = log.slice().reverse().map((m) => ({ date: m.date, weights: m.after, cash: null, move: m, now: false }));
  const last = steps[steps.length - 1];
  if (now.as_of && (!last || now.as_of > last.date)) steps.push({ date: now.as_of, weights: now.weights, cash: now.cash, move: null, now: true });
  else if (last && now.as_of === last.date) last.now = true;
  return steps;
}

// What one rebalance did, in words: bought, sold, more and less weight, and what it traded. Under
// each stock, why its rules moved it (and, for the owner, the figures they read); above, why the move.
function moveParts(m: Move): HTMLElement[] {
  const t = words[lang()];
  const why = m.reasons;
  const reason = (ticker: string): HTMLElement | null => {
    const r = why?.names[ticker];
    if (!r) return null;
    const box = add(h("div", "history-why"), r.why ? h("p", "text-[12.5px] text-muted", r.why) : null);
    if (r.figures?.length) {
      const more = add(h("details", "history-figures"), h("summary", "text-[12px] text-faint", t.figures),
        add(h("ul", "mt-1 space-y-0.5"), ...r.figures.map((f) => h("li", "num text-[12px] text-ink", f))));
      box.append(more);
    }
    return box;
  };
  const group = (title: string, rows: [string, string][]) => rows.length
    ? add(h("div"), h("p", "text-[12.5px] text-muted", title),
      add(h("ul", "mt-1 space-y-0.5"), ...rows.map(([ticker, note]) => add(h("li", "border-b border-line py-1"),
        add(h("div", "flex items-baseline justify-between gap-4"),
          h("span", "num font-medium text-ink-strong", ticker), h("span", "num text-[12.5px] text-ink", note)),
        reason(ticker)))))
    : null;
  const parts: HTMLElement[] = [];
  if (why?.lines.length) parts.push(add(h("div", "space-y-1"), h("p", "text-[12.5px] text-muted", t.why), ...why.lines.map((l) => h("p", "text-ink", l))));
  parts.push(...[
    group(t.bought, m.bought.map((x) => [x.ticker, share(x.weight)])),
    group(t.sold, m.sold.map((x) => [x.ticker, share(x.weight)])),
    group(t.more, m.raised.map((x) => [x.ticker, `${share(x.before)} → ${share(x.after)}`])),
    group(t.less, m.cut.map((x) => [x.ticker, `${share(x.before)} → ${share(x.after)}`])),
  ].filter((x): x is HTMLDivElement => !!x));
  if (!m.bought.length && !m.sold.length && !m.raised.length && !m.cut.length) {
    parts.push(h("p", "text-ink", Object.keys(m.after).length ? common[lang()].weightsBack : common[lang()].wentToCash));
  }
  parts.push(h("p", "text-[12.5px] text-muted", t.traded(pct(m.turnover, 0), pct(m.cost, 2))));
  parts.push(h("p", "text-[12px] text-faint", why ? (why.full ? t.ownerOnly : t.publicOnly) : t.noReasons));
  return parts;
}

// What changed at the date shown; for today, that it has not traded since, and its last rebalance.
function changed(step: Step, before: Step | undefined, changes: Version[]): HTMLElement {
  const t = words[lang()];
  const box = h("div", "space-y-3 text-[13.5px]");
  if (step.move) box.append(h("p", "label", t.thatDay), ...moveParts(step.move));
  else {
    box.append(h("p", "label", t.sinceLast), h("p", "text-ink", before ? t.quiet(day(before.date)) : t.noTrades));
    if (before?.move) box.append(h("p", "label pt-2", t.lastMove(day(before.date))), ...moveParts(before.move));
  }
  for (const v of changes.filter((v) => v.from === step.date)) box.append(h("p", "text-[13px] text-ink-strong", `◆ ${said(v.what)}`));
  return box;
}

// One move in a line of words: "Bought AMGN and AXP, sold TXN and CRM".
function inWords(m: Move): string {
  const t = words[lang()];
  const bits: string[] = [];
  if (m.bought.length) bits.push(t.boughtList(list(m.bought.map((x) => x.ticker))));
  if (m.sold.length) bits.push(bits.length ? t.soldList(list(m.sold.map((x) => x.ticker))) : t.soldFirst(list(m.sold.map((x) => x.ticker))));
  const re = m.raised.length + m.cut.length;
  if (re) bits.push(bits.length ? t.reweighted(re) : t.reweightedFirst(re));
  if (!bits.length) return Object.keys(m.after).length ? common[lang()].weightsBack : common[lang()].wentToCash;
  return bits.join(", ");
}

export function portfolioHistory(o: {
  log: Move[]; versions: Version[];
  now: { weights: Record<string, number>; cash: number | null; as_of: string | null };
}): HTMLElement {
  const t = words[lang()];
  const steps = stepsOf(o.log, o.now);
  const root = h("div");
  if (!steps.length) return add(root, treemap(o.now.weights, o.now.cash));

  let at = steps.length - 1;
  let shown = LISTED;

  // The date picker: earlier, a slider, later, and the date it is on.
  const when = h("p", "text-[17px] font-semibold text-ink-strong");
  const whenNote = h("p", "text-[12.5px] text-muted");
  const count = h("span", "num text-[12px] text-faint");
  const slider = h("input", "slider");
  Object.assign(slider, { type: "range", min: "0", max: String(steps.length - 1), step: "1", value: String(at) });
  slider.setAttribute("aria-label", t.pick);
  const earlier = h("button", "btn btn-ghost h-9 w-9 shrink-0 p-0 text-[16px]", "‹");
  const later = h("button", "btn btn-ghost h-9 w-9 shrink-0 p-0 text-[16px]", "›");
  for (const [b, label] of [[earlier, t.earlier], [later, t.later]] as const) {
    b.type = "button";
    b.setAttribute("aria-label", label);
  }
  const picker = add(h("div", "history-picker"),
    add(h("div", "flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1"), add(h("div"), when, whenNote), count),
    steps.length > 1 ? add(h("div", "mt-3 flex items-center gap-3"), earlier, slider, later) : null,
    steps.length > 1 ? add(h("div", "mt-1 flex justify-between px-12 text-[12px] text-faint"), h("span", "num", day(steps[0].date)),
      h("span", "", steps[steps.length - 1].now ? t.today : day(steps[steps.length - 1].date))) : null);

  // What it held then, and what changed.
  const map = h("div");
  const side = h("div", "frame p-4");
  const body = add(h("div", "mt-5 grid gap-5 lg:grid-cols-[1.45fr_1fr]"), map, side);

  // Every move, the latest first, with the changes of its rules among them.
  const rows = h("ol", "history-moves");
  const more = h("button", "btn btn-ghost mt-3 py-1.5 text-[13px]");
  more.type = "button";
  more.addEventListener("click", () => ((shown = Infinity), drawList()));
  const moves = o.log.length
    ? add(h("div", "mt-10"),
      add(h("div", "sec-head"), h("h3", "sec-title text-[15px]", t.movesTitle), h("span", "sec-note", t.movesNote(plural(o.log.length, ...common[lang()].rebalance)))),
      rows, more)
    : null;

  function drawList() {
    type Row = { date: string; move?: Move; version?: Version };
    const all: Row[] = [...o.log.map((m): Row => ({ date: m.date, move: m })), ...o.versions.map((v): Row => ({ date: v.from, version: v }))]
      .sort((a, b) => (a.date === b.date ? (a.move ? -1 : 1) : a.date < b.date ? 1 : -1));
    const cut = Number.isFinite(shown) ? all.slice(0, shown) : all;
    rows.replaceChildren(...cut.map((r) => {
      if (r.version) {
        return add(h("li", "history-row is-change"), h("span", "num text-ink-strong", day(r.date)), h("span", "text-ink", `◆ ${said(r.version.what)}`), h("span"));
      }
      const m = r.move!;
      const i = steps.findIndex((s) => s.move === m);
      const b = add(h("button", "history-row"), h("span", "num text-ink-strong", day(m.date)), h("span", "text-ink", inWords(m)),
        h("span", "num text-[12.5px] text-muted sm:text-right", t.tradedShort(pct(m.turnover, 0))));
      b.type = "button";
      if (i === at) b.setAttribute("aria-current", "true");
      b.addEventListener("click", () => {
        go(i);
        picker.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      return add(h("li"), b);
    }));
    more.textContent = t.showAll(all.length);
    more.hidden = cut.length >= all.length;
  }

  function go(i: number) {
    at = Math.max(0, Math.min(steps.length - 1, i));
    const s = steps[at];
    slider.value = String(at);
    slider.style.setProperty("--p", `${steps.length > 1 ? (at / (steps.length - 1)) * 100 : 100}%`);
    earlier.disabled = at === 0;
    later.disabled = at === steps.length - 1;
    when.textContent = s.now ? `${t.today} · ${day(s.date)}` : day(s.date);
    const held = Object.keys(s.weights).length;
    whenNote.textContent = [s.move ? t.rebalancedAt(day(s.date)) : t.afterClose(day(s.date)),
      held ? t.holds(plural(held, ...common[lang()].stock)) : t.inCash].join(" · ");
    count.textContent = steps.length > 1 ? t.step(at + 1, steps.length) : "";
    const fresh = new Set(s.move?.bought.map((x) => x.ticker) ?? []);
    map.replaceChildren(treemap(s.weights, s.cash, { fresh, freshLabel: t.fresh }));
    side.replaceChildren(changed(s, steps[at - 1], o.versions));
    drawList();
  }

  slider.addEventListener("input", () => go(Number(slider.value)));
  earlier.addEventListener("click", () => go(at - 1));
  later.addEventListener("click", () => go(at + 1));
  go(at);
  return add(root, picker, body, moves);
}
