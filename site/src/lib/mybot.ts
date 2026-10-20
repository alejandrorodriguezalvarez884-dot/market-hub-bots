// The owner's page drawn rather than written: what the bot holds as a map of tiles, where it ranks
// as a mark on a line, and what it has done as a timeline of its rebalances and changes. In the ink;
// green and red stay for the market's moves.
import { add, h, svg } from "./dom";
import { day, ordinal, pct } from "./format";
import { hubQuoteUrl } from "./site";
import type { Move, Version } from "./types";

const share = (w: number) => pct(w, w < 0.1 ? 1 : 0);

// --- What it holds: a treemap -------------------------------------------------------------------

type Tile = { key: string; w: number; cash?: boolean };
type Placed = Tile & { x: number; y: number; dx: number; dy: number };

// Squarified treemap (Bruls, Huizing and van Wijk): rows of tiles as close to square as they come.
function squarify(tiles: Tile[], x: number, y: number, W: number, H: number): Placed[] {
  const total = tiles.reduce((s, t) => s + t.w, 0) || 1;
  let rest = tiles.map((t) => ({ ...t, a: (t.w / total) * W * H }));
  const out: Placed[] = [];
  const worst = (row: { a: number }[], side: number) => {
    const s = row.reduce((t, r) => t + r.a, 0);
    const hi = Math.max(...row.map((r) => r.a)), lo = Math.min(...row.map((r) => r.a));
    return Math.max((side * side * hi) / (s * s), (s * s) / (side * side * lo));
  };
  while (rest.length) {
    const side = Math.min(W, H);
    let n = 1;
    while (n < rest.length && worst(rest.slice(0, n + 1), side) <= worst(rest.slice(0, n), side)) n++;
    const row = rest.slice(0, n);
    const thick = row.reduce((s, r) => s + r.a, 0) / side;
    let at = W >= H ? y : x;
    for (const r of row) {
      const len = r.a / thick;
      out.push(W >= H ? { ...r, x, y: at, dx: thick, dy: len } : { ...r, x: at, y, dx: len, dy: thick });
      at += len;
    }
    if (W >= H) (x += thick), (W -= thick);
    else (y += thick), (H -= thick);
    rest = rest.slice(n);
  }
  return out;
}

// Each company a tile as big as its weight, the largest the brightest, the cash hatched.
export function treemap(weights: Record<string, number>, cash: number | null | undefined, opts: { preview?: boolean } = {}): HTMLElement {
  const held = Object.entries(weights).filter(([, w]) => w > 0).sort((a, b) => b[1] - a[1]);
  const left = cash ?? Math.max(0, 1 - held.reduce((s, [, w]) => s + w, 0));
  const tiles: Tile[] = held.map(([key, w]) => ({ key, w }));
  if (left > 0.005) tiles.push({ key: "Cash", w: left, cash: true });
  const box = h("div", `treemap ${opts.preview ? "is-preview" : ""}`);
  if (!tiles.length) return add(box, h("p", "absolute inset-0 grid place-items-center text-[13px] text-muted", "Nothing held"));
  const place = () => {
    const pxW = box.clientWidth || 600, pxH = box.clientHeight || 280;
    const layout = squarify(tiles, 0, 0, pxW, pxH);
    box.querySelectorAll(".tile").forEach((t) => t.remove());
    layout.forEach((t, i) => {
      const el = t.cash ? h("div", "tile is-cash") : Object.assign(h("a", "tile"), { href: hubQuoteUrl(t.key) });
      el.style.left = `${(t.x / pxW) * 100}%`;
      el.style.top = `${(t.y / pxH) * 100}%`;
      el.style.width = `${(t.dx / pxW) * 100}%`;
      el.style.height = `${(t.dy / pxH) * 100}%`;
      if (!t.cash) el.style.setProperty("--a", (0.26 - (0.18 * i) / Math.max(1, held.length - 1)).toFixed(3));
      el.title = `${t.key} ${share(t.w)}`;
      if (t.dx > 38 && t.dy > 22) {
        el.append(h("span", "tile-name", t.key));
        if (t.dy > 40) el.append(h("span", "tile-w", share(t.w)));
      }
      box.append(el);
    });
  };
  requestAnimationFrame(place);
  new ResizeObserver(() => place()).observe(box);
  return box;
}

// --- Where it ranks: a mark on a line, first on the left ----------------------------------------

export function rankMeter(rank: number | undefined, of: number): HTMLElement {
  const box = h("div", "rank");
  if (!rank || of < 1) return add(box, h("span", "text-[12px] text-faint", "not ranked yet"));
  const track = h("span", "rank-track");
  if (of <= 16) {
    for (let i = 1; i <= of; i++) track.append(h("i", i === rank ? "on" : ""));
  } else {
    const mark = h("b", "rank-mark");
    mark.style.left = `${((rank - 1) / (of - 1)) * 100}%`;
    track.classList.add("is-line");
    track.append(mark);
  }
  return add(box, track, h("span", "num text-[12px] text-muted", `${ordinal(rank)} of ${of}`));
}

// --- What it has done: its rebalances and changes on a timeline --------------------------------

const ms = (iso: string) => Date.parse(`${iso.slice(0, 10)}T00:00:00Z`);

// Bars up for what it bought or raised, down for what it sold or cut, at the close it traded; a
// diamond under the line where its rules changed or it was paused. A tap reads one.
export function timeline(log: Move[], changes: Version[], from: string, to: string, pick: (m: Move | Version) => void): HTMLElement {
  const wrap = h("div", "relative");
  const draw = () => {
    const lanes = changes.length > 0;
    const W = Math.max(280, wrap.clientWidth || 800), padL = 50, padR = 12, mid = 64, room = 50, lane = 146, H = lanes ? 176 : 138;
    const t0 = ms(from), t1 = Math.max(ms(to), t0 + 86400000);
    const x = (iso: string) => padL + ((ms(iso) - t0) / (t1 - t0)) * (W - padL - padR);
    const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart block w-full h-auto select-none", role: "img" });
    s.setAttribute("aria-label", `${log.length} rebalances and ${changes.length} changes`);
    const label = (y: number, text: string) => {
      const t = svg("text", { x: padL - 10, y, fill: "var(--color-faint)", "font-size": 11, "text-anchor": "end", "font-family": "var(--font-sans)" });
      t.textContent = text;
      s.append(t);
    };
    label(mid - room + 10, "bought");
    label(mid + room - 2, "sold");
    s.append(svg("line", { x1: padL, x2: W - padR, y1: mid, y2: mid, stroke: "var(--color-line-strong)" }));
    if (lanes) {
      s.append(svg("line", { x1: padL, x2: W - padR, y1: lane, y2: lane, stroke: "var(--color-line)", "stroke-dasharray": "2 4" }));
      label(lane + 4, "changes");
    }
    const amount = (m: Move) => ({
      up: m.bought.reduce((t, b) => t + b.weight, 0) + m.raised.reduce((t, r) => t + r.after - r.before, 0),
      down: m.sold.reduce((t, b) => t + b.weight, 0) + m.cut.reduce((t, r) => t + r.before - r.after, 0),
    });
    const sizes = log.map(amount);
    // On a square-root scale, so the first buy of everything does not flatten the trades after it.
    const top = Math.sqrt(Math.max(0.05, ...sizes.map((a) => Math.max(a.up, a.down))));
    const tall = (v: number) => (Math.sqrt(v) / top) * room;
    const bw = Math.max(2, Math.min(10, ((W - padL - padR) / Math.max(log.length, 1)) * 0.55));
    const marks: { x: number; item: Move | Version; els: SVGElement[] }[] = [];
    log.forEach((m, i) => {
      const xx = x(m.date), a = sizes[i];
      const up = svg("rect", { x: xx - bw / 2, y: mid - tall(a.up), width: bw, height: Math.max(1, tall(a.up)), rx: 1, fill: "var(--color-ink-strong)" });
      const down = svg("rect", { x: xx - bw / 2, y: mid + 1, width: bw, height: Math.max(1, tall(a.down)), rx: 1, fill: "var(--color-muted)" });
      s.append(up, down);
      marks.push({ x: xx, item: m, els: [up, down] });
    });
    for (const v of changes) {
      const xx = x(v.from);
      const d = svg("path", { d: `M${xx} ${lane - 6}L${xx + 6} ${lane}L${xx} ${lane + 6}L${xx - 6} ${lane}Z`, fill: "var(--color-page)", stroke: "var(--color-ink-strong)", "stroke-width": 1.6 });
      s.append(d);
      marks.push({ x: xx, item: v, els: [d] });
    }
    for (const [iso, anchor] of [[from, "start"], [to, "end"]] as const) {
      const t = svg("text", { x: anchor === "start" ? padL : W - padR, y: H - 2, fill: "var(--color-faint)", "font-size": 11, "text-anchor": anchor, "font-family": "var(--font-mono)" });
      t.textContent = day(iso);
      s.append(t);
    }
    const cursor = svg("line", { y1: 8, y2: lanes ? lane + 8 : mid + room, stroke: "var(--color-muted)", "stroke-dasharray": "3 3", visibility: "hidden" });
    s.append(cursor);
    const choose = (ev: PointerEvent) => {
      if (!marks.length) return;
      const r = s.getBoundingClientRect();
      const px = ((ev.clientX - r.left) / r.width) * W;
      const near = marks.reduce((best, m) => (Math.abs(m.x - px) < Math.abs(best.x - px) ? m : best));
      cursor.setAttribute("x1", String(near.x));
      cursor.setAttribute("x2", String(near.x));
      cursor.setAttribute("visibility", "visible");
      for (const m of marks) for (const el of m.els) el.setAttribute("opacity", m === near ? "1" : "0.45");
      pick(near.item);
    };
    s.addEventListener("pointermove", choose);
    s.addEventListener("pointerdown", choose);
    wrap.replaceChildren(s);
  };
  requestAnimationFrame(draw);
  return wrap;
}

// What one rebalance did, as chips, or one change, in a line.
export function detail(item: Move | Version, words: (what: string[]) => string): HTMLElement {
  if ("from" in item) {
    return add(h("div", "flex flex-wrap items-baseline gap-x-3"), h("span", "num text-[13px] text-ink-strong", day(item.from)), h("span", "text-[13px] text-ink", `◆ ${words(item.what)}`));
  }
  const chip = (text: string, cls = "") => h("span", `chip ${cls}`, text);
  const parts = [
    ...item.bought.map((x) => chip(`+ ${x.ticker} ${share(x.weight)}`, "text-ink-strong")),
    ...item.sold.map((x) => chip(`− ${x.ticker}`, "text-muted")),
    ...item.raised.map((x) => chip(`↑ ${x.ticker} ${share(x.after)}`)),
    ...item.cut.map((x) => chip(`↓ ${x.ticker} ${share(x.after)}`)),
  ];
  return add(h("div", "flex flex-wrap items-center gap-1.5"), h("span", "num mr-1.5 text-[13px] text-ink-strong", day(item.date)),
    ...(parts.length ? parts : [h("span", "text-[13px] text-muted", Object.keys(item.after).length ? "Weights back into place" : "Went to cash")]),
    h("span", "num ml-auto pl-2 text-[12px] text-faint", `traded ${pct(item.turnover, 0)}`));
}
