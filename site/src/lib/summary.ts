// The player's summary, on the board and on Your bot: how their bot did since their last visit (or
// over the last close), against the S&P 500 over the same closes, its place and how it changed, what
// it bought and sold, and what waits for the next close. It describes; it never says what to do.
//
// "Your last visit" is the last close this browser showed a summary for, kept in this browser alone
// (localStorage, "bl-seen"): the service keeps nothing about visits. While no new close comes in,
// the same summary is shown again, so the board and Your bot say the same thing.
import { lang } from "../i18n";
import { summary as words } from "../i18n/summary";
import { said } from "./doings";
import { add, h } from "./dom";
import { day, ordinal, plural, signedPct, tone } from "./format";
import { inWords } from "./history";
import { robot } from "./robot";
import { api, link } from "./site";
import type { Summary } from "./types";

const KEY = "bl-seen";
type Seen = { slug: string; as_of: string; since: string | null };

function seen(): Seen | null {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "null");
    return v && typeof v.slug === "string" && typeof v.as_of === "string" ? v : null;
  } catch {
    return null;
  }
}

// The close to count from: the last one this browser showed, or, while no new close has come in
// since, the one that summary counted from. Another bot (a new one) starts over.
export function sinceFor(slug: string, asOf: string | null): string | null {
  const s = seen();
  if (!s || s.slug !== slug) return null;
  return asOf && s.as_of >= asOf ? s.since : s.as_of;
}

export function remember(slug: string, s: Summary, since: string | null): void {
  if (!s.started || !s.as_of) return;
  try {
    localStorage.setItem(KEY, JSON.stringify({ slug, as_of: s.as_of, since } satisfies Seen));
  } catch {}
}

// The summary of the player's bot, `slug`, whose last close the page knows (`asOf`), as a card.
export async function summaryCard(slug: string, asOf: string | null, cls = "mb-6"): Promise<HTMLElement | null> {
  const since = sinceFor(slug, asOf);
  const got = await api<{ summary: Summary | null }>(`/api/bots/summary${since ? `?since=${since}` : ""}`).catch(() => null);
  const s = got?.summary;
  if (!s || (s.slug && s.slug !== slug)) return null;
  remember(slug, s, since);
  return card(s, cls);
}

function card(s: Summary, cls: string): HTMLElement {
  const t = words[lang()];
  const box = h("section", `frame summary ${cls} px-4 py-4 sm:px-5`);
  const hide = h("button", "summary-hide", "×");
  hide.type = "button";
  hide.title = t.hide;
  hide.setAttribute("aria-label", t.hide);
  hide.addEventListener("click", () => box.remove());
  const lines = h("div", "mt-3 space-y-1.5 text-[13.5px] text-muted");

  if (!s.started) {
    const head = add(h("a", "flex items-center gap-4"), robot(s.slug ?? "", 40), add(h("div", "min-w-0"),
      h("p", "label", `${t.yourBot} · ${s.name}`),
      h("p", "mt-1 text-[14px] text-ink-strong", s.starts ? t.starts(day(s.starts)) : "")));
    head.href = link("/me/");
    add(box, hide, head);
    if (s.pending) box.append(add(lines, h("p", "", t.waiting(day(s.pending.applies), said(s.pending.what)))));
    return box;
  }

  const title = s.since_visit ? t.sinceVisit : s.from_start ? t.sinceStart : t.lastClose;
  const when = s.from && !s.from_start ? t.fromTo(day(s.from), day(s.as_of)) : t.toClose(day(s.as_of));
  const place = s.place;
  const moved = place && place.now && place.then && place.then !== place.now
    ? (place.then > place.now ? t.upFrom(ordinal(place.then)) : t.downFrom(ordinal(place.then)))
    : place && place.now && place.then ? t.same : null;
  const head = add(h("a", "flex items-start gap-4"), robot(s.slug ?? "", 44),
    add(h("div", "min-w-0 flex-1"),
      add(h("p", "label"), `${title} · ${s.name}`),
      h("p", "mt-0.5 text-[12.5px] text-faint", `${when} · ${plural(s.sessions ?? 0, ...t.closes)}`),
      add(h("p", "mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1"),
        add(h("span", "flex items-baseline gap-2"), h("span", "text-[13px] text-muted", t.yourBot),
          h("span", `num text-[22px] font-semibold ${tone(s.bot)}`, signedPct(s.bot, 2))),
        add(h("span", "flex items-baseline gap-2"), h("span", "text-[13px] text-muted", "S&P 500"),
          h("span", `num text-[16px] font-semibold opacity-80 ${tone(s.index)}`, signedPct(s.index, 2)))),
      place?.now ? add(h("p", "mt-1 text-[13px]"), h("span", "num text-ink-strong", t.place(ordinal(place.now), place.of)),
        moved ? h("span", "text-muted", ` · ${moved}`) : null) : null));
  head.href = link("/me/");
  add(box, hide, head);

  const moves = s.moves ?? [];
  if (!moves.length) lines.append(h("p", "", t.noTrades));
  for (const m of moves) lines.append(h("p", "", t.traded(day(m.date), inWords(m))));
  if ((s.moved ?? 0) > moves.length) lines.append(h("p", "text-faint", t.more((s.moved ?? 0) - moves.length)));
  for (const v of s.changed ?? []) lines.append(h("p", "text-ink", `◆ ${t.changed(day(v.from), said(v.what))}`));
  if (s.paused) lines.append(h("p", "", t.paused));
  if (s.pending) lines.append(h("p", "text-ink", t.waiting(day(s.pending.applies), said(s.pending.what))));
  box.append(lines);
  return box;
}
