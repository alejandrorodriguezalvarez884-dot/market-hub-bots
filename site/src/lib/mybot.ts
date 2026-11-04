// The owner's page drawn rather than written: what the bot holds as a map of tiles and where it
// ranks as a mark on a line (what it has done is in history.ts). In the ink;
// green and red stay for the market's moves.
import { add, h } from "./dom";
import { ordinal, pct } from "./format";
import { hubQuoteUrl } from "./site";
import { lang } from "../i18n";
import { common } from "../i18n/common";

const w = () => common[lang()];

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

// Each company a tile as big as its weight, the largest the brightest, the cash hatched; those in
// ``fresh`` (just bought) outlined and tagged.
export function treemap(weights: Record<string, number>, cash: number | null | undefined,
  opts: { preview?: boolean; small?: boolean; fresh?: Set<string>; freshLabel?: string } = {}): HTMLElement {
  const held = Object.entries(weights).filter(([, w]) => w > 0).sort((a, b) => b[1] - a[1]);
  const left = cash ?? Math.max(0, 1 - held.reduce((s, [, w]) => s + w, 0));
  const tiles: Tile[] = held.map(([key, w]) => ({ key, w }));
  if (left > 0.005) tiles.push({ key: w().cashTile, w: left, cash: true });
  const box = h("div", `treemap ${opts.preview ? "is-preview" : ""} ${opts.small ? "is-small" : ""}`);
  if (!tiles.length) return add(box, h("p", "absolute inset-0 grid place-items-center text-[13px] text-muted", w().nothingHeld));
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
      const fresh = !t.cash && !!opts.fresh?.has(t.key);
      if (fresh) el.classList.add("is-new");
      el.title = `${t.key} ${share(t.w)}${fresh && opts.freshLabel ? ` · ${opts.freshLabel}` : ""}`;
      if (fresh && opts.freshLabel && t.dx > 64 && t.dy > 56) el.append(h("span", "tile-new", opts.freshLabel));
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
  if (!rank || of < 1) return add(box, h("span", "text-[12px] text-faint", w().notRanked));
  const track = h("span", "rank-track");
  if (of <= 16) {
    for (let i = 1; i <= of; i++) track.append(h("i", i === rank ? "on" : ""));
  } else {
    const mark = h("b", "rank-mark");
    mark.style.left = `${((rank - 1) / (of - 1)) * 100}%`;
    track.classList.add("is-line");
    track.append(mark);
  }
  return add(box, track, h("span", "num text-[12px] text-muted", w().rankOf(ordinal(rank), of)));
}
