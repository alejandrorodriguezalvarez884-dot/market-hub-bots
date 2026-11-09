// Weekly prizes: a trophy for the best bot of each market week, Monday to Friday (league.py works
// them out). On the board: the week being played as it stands, every week's winners and the bots
// that have won the most weeks. On the board's lines and a bot's page: its trophies.
import { add, h, svg } from "./dom";
import { day, plural, signedPct, tone } from "./format";
import { robot } from "./robot";
import { botUrl } from "./site";
import type { Weekly, Who, Winner } from "./types";
import { lang } from "../i18n";
import { common } from "../i18n/common";
import { weekly as words } from "../i18n/weekly";

const SHOWN = 8; // winners listed before "Show all"

// A small cup, in the ink of whatever holds it.
export function trophy(size = 14): SVGSVGElement {
  const s = svg("svg", { viewBox: "0 0 16 16", width: size, height: size, fill: "none", stroke: "currentColor", "stroke-width": 1.4,
    "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", class: "shrink-0" });
  for (const d of ["M4.5 2.5h7v3.2a3.5 3.5 0 0 1-7 0z", "M4.5 3.5H2.5v1a2.5 2.5 0 0 0 2.3 2.5", "M11.5 3.5h2v1a2.5 2.5 0 0 1-2.3 2.5",
    "M8 9.2v2.6", "M5.5 13.5h5", "M6.2 11.8h3.6v1.7H6.2z"]) s.append(svg("path", { d }));
  return s;
}

// The weeks a bot has won, as a tag next to its name ("🏆 2").
export function winsTag(n: number | undefined): HTMLElement | null {
  if (!n) return null;
  const t = words[lang()];
  const el = add(h("span", "tag trophy-tag shrink-0 gap-1"), trophy(11), n > 1 ? String(n) : null);
  el.title = t.winsTitle(n);
  return el;
}

const weekOf = (from: string) => words[lang()].weekOf(day(from));

function who(w: Winner | Who, size = 26): HTMLElement {
  const t = words[lang()];
  const c = common[lang()];
  if ("gone" in w) {
    const dot = h("span", "inline-block shrink-0 rounded-full border border-dashed border-line-strong");
    dot.style.width = dot.style.height = `${size}px`;
    return add(h("span", "flex min-w-0 items-center gap-2.5"), dot, h("span", "truncate text-[13px] text-muted", t.gone));
  }
  const a = add(h("a", "flex min-w-0 items-center gap-2.5 hover:text-ink-strong"), robot(w.slug, size),
    add(h("span", "min-w-0"), add(h("span", "flex min-w-0 items-center gap-2"), h("span", "truncate font-semibold text-ink-strong", w.name),
      w.you ? h("span", "tag tag-you shrink-0", c.you) : null),
      h("span", "block truncate text-[12px] text-muted", c.by(w.handle))));
  a.href = botUrl(w.slug);
  return a;
}

// The week being played, as it stands: its leader first, the index over the same closes.
function current(wk: Weekly): HTMLElement {
  const t = words[lang()];
  const c = common[lang()];
  const box = h("div", "frame px-4 py-4 sm:px-5");
  const now = wk.current;
  if (!now) {
    const last = wk.winners[0];
    return add(box, add(h("p", "label flex items-center gap-1.5"), t.thisWeek),
      h("p", "mt-2 text-[14px] text-ink", t.nextWeek),
      last && last.bots.length ? add(h("div", "mt-4 border-t border-line pt-3"),
        add(h("p", "label flex items-center gap-1.5"), trophy(12), `${t.lastWinner} · ${weekOf(last.from)}`),
        add(h("div", "mt-2 flex items-center justify-between gap-3"), who(last.bots[0], 30),
          h("span", `num font-semibold ${tone(last.return)}`, signedPct(last.return)))) : null);
  }
  add(box, add(h("div", "flex flex-wrap items-baseline justify-between gap-2"),
    h("p", "label", `${t.thisWeek} · ${weekOf(now.from)}`),
    h("span", "text-[12px] text-muted", t.soFar(plural(now.sessions, ...t.close)))));
  if (!now.standing.length) box.append(h("p", "mt-3 text-[14px] text-ink", t.noneYet));
  const list = h("div", "mt-2 divide-y divide-line");
  for (const s of now.standing) {
    list.append(add(h("div", `flex items-center gap-3 py-2.5 ${s.place === 1 ? "" : "opacity-90"}`),
      h("span", `num w-5 shrink-0 text-[13px] ${s.place === 1 ? "text-ink-strong" : "text-muted"}`, String(s.place)),
      add(h("span", "min-w-0 flex-1"), who(s, s.place === 1 ? 34 : 26)),
      s.place === 1 ? add(h("span", "tag trophy-tag hidden gap-1 sm:inline-flex"), trophy(11), t.leads) : null,
      h("span", `num shrink-0 text-right font-semibold ${tone(s.return)}`, signedPct(s.return))));
  }
  list.append(add(h("div", "flex items-center gap-3 py-2.5 text-muted"), h("span", "w-5 shrink-0 text-[13px] text-faint", "—"),
    h("span", "min-w-0 flex-1 text-[13px]", "S&P 500"), h("span", `num shrink-0 font-semibold opacity-80 ${tone(now.index)}`, signedPct(now.index))));
  return add(box, list, h("p", "mt-3 text-[12px] text-muted", `${t.inRunning(plural(now.entrants, ...c.bot))}. ${t.whole}`));
}

// The bots with the most weeks won: most first, then the latest win.
function ranking(wk: Weekly): HTMLElement {
  const t = words[lang()];
  const box = add(h("div", "frame px-4 py-4 sm:px-5"), h("p", "label", t.most));
  if (!wk.ranking.length) return add(box, h("p", "mt-2 text-[13.5px] text-muted", t.noWinners));
  let place = 0, before = -1;
  const list = h("div", "mt-2 divide-y divide-line");
  wk.ranking.forEach((r, i) => {
    if (r.wins !== before) place = i + 1, before = r.wins;
    list.append(add(h("div", "flex items-center gap-3 py-2.5"), h("span", "num w-5 shrink-0 text-[13px] text-muted", String(place)),
      add(h("span", "min-w-0 flex-1"), who(r)),
      add(h("span", "shrink-0 text-right"), add(h("span", "num flex items-center justify-end gap-1.5 font-semibold text-ink-strong"), trophy(13),
        plural(r.wins, ...t.weeks)), h("span", "block text-[11.5px] text-muted", t.lastWon(day(r.last))))));
  });
  return add(box, list);
}

// Every week's winners, newest first: the week, the bot, its return, the index's and how many played.
function winners(wk: Weekly): HTMLElement {
  const t = words[lang()];
  const c = common[lang()];
  const box = add(h("div", "mt-4"), h("p", "label", t.winners));
  if (!wk.winners.length) return add(box, h("p", "mt-2 text-[13.5px] text-muted", t.noWinners));
  const grid = "grid grid-cols-[minmax(0,1fr)_4.6rem] md:grid-cols-[12rem_minmax(0,1fr)_5rem_5.6rem_5rem] items-center gap-x-4 px-3 py-2.5";
  const list = add(h("div", "mt-2 divide-y divide-line"),
    add(h("div", `${grid} !py-2 text-[12px] text-muted`), h("span", "hidden md:block", t.colWeek), h("span", "", t.colBot),
      h("span", "text-right", t.colReturn), h("span", "hidden text-right md:block", "S&P 500"), h("span", "hidden text-right md:block", t.colPlayed)));
  const rows = wk.winners.map((w) => {
    const bots = add(h("span", "flex min-w-0 flex-col gap-1.5"), h("span", "text-[12px] text-muted md:hidden", weekOf(w.from)), ...w.bots.map((b) => who(b)),
      w.bots.length > 1 ? h("span", "text-[11.5px] text-muted", t.tied) : null);
    return add(h("div", grid), add(h("span", "hidden items-center gap-1.5 text-[13px] text-ink md:flex"), trophy(13), weekOf(w.from)), bots,
      h("span", `num text-right font-semibold ${tone(w.return)}`, signedPct(w.return)),
      h("span", `num hidden text-right opacity-80 md:block ${tone(w.index)}`, signedPct(w.index)),
      h("span", "hidden text-right text-[12px] text-muted md:block", t.of(plural(w.entrants, ...c.bot))));
  });
  return add(box, ...shown(list, rows));
}

// The first rows of a list, and a button for the rest.
function shown(list: HTMLElement, rows: HTMLElement[]): HTMLElement[] {
  rows.slice(0, SHOWN).forEach((r) => list.append(r));
  if (rows.length <= SHOWN) return [list];
  const more = h("button", "btn btn-ghost mt-3", words[lang()].showAll(rows.length));
  more.type = "button";
  more.addEventListener("click", () => (rows.slice(SHOWN).forEach((r) => list.append(r)), more.remove()));
  return [list, more];
}

// The board page's section.
export function weeklySection(wk: Weekly): HTMLElement {
  const t = words[lang()];
  return add(h("section", "sec mt-12 scroll-mt-20"),
    add(h("div", "sec-head"), add(h("h2", "sec-title flex items-center gap-2"), trophy(15), t.title), h("span", "sec-note", t.note)),
    add(h("div", "grid gap-4 md:grid-cols-2"), current(wk), ranking(wk)),
    winners(wk));
}

// A bot's page: its trophy, by its name.
export function badge(n: number): HTMLElement | null {
  if (!n) return null;
  return add(h("span", "tag trophy-tag gap-1.5"), trophy(12), words[lang()].badge(n));
}

// A bot's page: the weeks it won, newest first.
export function wonSection(wins: { week: string; from: string; return: number; index: number | null; entrants: number; shared: boolean }[]): HTMLElement | null {
  if (!wins.length) return null;
  const t = words[lang()];
  const c = common[lang()];
  const list = h("div", "max-w-3xl divide-y divide-line");
  const rows = wins.map((w) =>
    add(h("div", "grid grid-cols-[minmax(0,1fr)_4.6rem] items-center gap-x-4 py-2.5 sm:grid-cols-[minmax(0,1fr)_5rem_6rem_5.5rem]"),
      add(h("span", "flex min-w-0 items-center gap-2 text-[13.5px] text-ink"), trophy(13), weekOf(w.from),
        w.shared ? h("span", "truncate text-[12px] text-muted", `· ${t.sharedNote}`) : null),
      h("span", `num text-right font-semibold ${tone(w.return)}`, signedPct(w.return)),
      h("span", `num hidden text-right text-[13px] opacity-80 sm:block ${tone(w.index)}`, `S&P ${signedPct(w.index)}`),
      h("span", "hidden text-right text-[12px] text-muted sm:block", t.of(plural(w.entrants, ...c.bot)))));
  return add(h("section", "sec mt-12"), add(h("div", "sec-head"), add(h("h2", "sec-title flex items-center gap-2"), trophy(15), t.won),
    h("span", "sec-note", t.wonNote)), ...shown(list, rows));
}
