// Charts drawn as SVG: a sparkline for a line of the board, and a bot against the index on its page.
// Values are growth from 1 (1.12 is +12%). One colour, the ink; green and red only for a move: the
// gap between the bot and the index, its fall from its peak, a line's end above or below its start.
import { add, h, svg } from "./dom";
import { day, signedPct } from "./format";

const UP = "var(--color-up)";
const DOWN = "var(--color-down)";
const UP_SOFT = "var(--color-up-soft)";
const DOWN_SOFT = "var(--color-down-soft)";
const MONO = "var(--font-mono)";

const text = (x: number, y: number, s: string, a: Record<string, string | number> = {}) => {
  const t = svg("text", { x, y, fill: "var(--color-faint)", "font-size": 11, "font-family": MONO, ...a });
  t.textContent = s;
  return t;
};
const fixed = (v: number) => v.toFixed(1);

export function sparkline(values: number[], width = 76, height = 24, color?: string): SVGSVGElement {
  const s = svg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, "aria-hidden": "true", class: "block overflow-visible" });
  if (values.length < 2) {
    // Not started: the line it will draw from, and where it starts.
    s.append(svg("line", { x1: 5, x2: width, y1: height / 2, y2: height / 2, stroke: "var(--color-line-strong)", "stroke-dasharray": "2 3" }));
    s.append(svg("circle", { cx: 3, cy: height / 2, r: 2.2, fill: "var(--color-page)", stroke: "var(--color-muted)", "stroke-width": 1.2 }));
    return s;
  }
  const lo = Math.min(1, ...values), hi = Math.max(1, ...values);
  const pad = 3;
  const y = (v: number) => (hi === lo ? height / 2 : height - pad - ((v - lo) / (hi - lo)) * (height - 2 * pad));
  const x = (i: number) => (i / (values.length - 1)) * (width - 3);
  const last = values[values.length - 1];
  const up = last >= 1;
  const stroke = color ?? (up ? UP : DOWN);
  const pts = values.map((v, i) => `${fixed(x(i))},${fixed(y(v))}`);
  // The ground it covered from its start, in the colour of where it ended.
  s.append(svg("polygon", { points: [`0,${fixed(y(1))}`, ...pts, `${fixed(x(values.length - 1))},${fixed(y(1))}`].join(" "), fill: color ? "var(--color-accent-soft)" : up ? UP_SOFT : DOWN_SOFT }));
  s.append(svg("line", { x1: 0, x2: width, y1: y(1), y2: y(1), stroke: "var(--color-line-strong)", "stroke-dasharray": "2 3" }));
  s.append(svg("polyline", { points: pts.join(" "), fill: "none", stroke, "stroke-width": 1.5, "stroke-linejoin": "round", "stroke-linecap": "round" }));
  s.append(svg("circle", { cx: x(values.length - 1), cy: y(last), r: 2.2, fill: stroke }));
  return s;
}

export type Series = { name: string; values: (number | null)[]; color: string; width?: number; dashed?: boolean };
export type ChartOptions = {
  // The fall from its peak of the last series, in a band under the chart.
  drawdown?: boolean;
  // Buttons for the last month, three months, year or all, when the curve is longer than that.
  ranges?: boolean;
};

const RANGES: { label: string; sessions: number }[] = [
  { label: "1M", sessions: 21 },
  { label: "3M", sessions: 63 },
  { label: "1Y", sessions: 252 },
  { label: "All", sessions: Infinity },
];

// Lines over the same sessions, from 1 the session before the first. The last series is the main
// one (the bot); with two, the gap between it and the first (the index) is shaded green where it
// is ahead and red where it is behind; with one, its distance from where it started. Hovering, or
// a finger on it, reads every line on a session.
export function lineChart(root: HTMLElement, dates: string[], series: Series[], height = 280, opts: ChartOptions = {}): void {
  const { drawdown = true, ranges = true } = opts;
  const offered = RANGES.filter((r) => r.sessions === Infinity || dates.length > r.sessions);
  let range = offered[offered.length - 1];
  const body = h("div");
  const draw = () => {
    const n = Math.min(dates.length, range.sessions);
    const from = dates.length - n;
    // A window that starts later is rebased to 1 on the close before it.
    const cut = series.map((se) => {
      const base = from === 0 ? 1 : se.values[from - 1];
      return { ...se, values: se.values.slice(from).map((v) => (v == null || base == null ? null : v / base)) };
    });
    plot(body, dates.slice(from), cut, height, drawdown);
  };
  root.replaceChildren();
  if (ranges && offered.length > 1) {
    const nav = h("div", "chart-ranges");
    nav.setAttribute("aria-label", "Range");
    for (const r of offered) {
      const b = h("button", "", r.label);
      b.type = "button";
      b.setAttribute("aria-pressed", String(r === range));
      b.addEventListener("click", () => {
        range = r;
        nav.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        draw();
      });
      nav.append(b);
    }
    root.append(nav);
  }
  root.append(body);
  draw();
}

type Pt = { x: number; a: number; b: number };

function plot(root: HTMLElement, dates: string[], series: Series[], tall: number, withDrawdown: boolean): void {
  root.replaceChildren();
  // Drawn at the width it is shown at, so its words keep their size.
  const W = Math.max(280, Math.round(root.clientWidth || root.parentElement?.clientWidth || 800));
  const compact = W < 560;
  const height = compact ? Math.min(tall, 230) : tall;
  const main = series[series.length - 1];
  const ref = series.length > 1 ? series[0] : null;
  const n = Math.max(dates.length, 1);
  // The fall of the main line from its highest close so far.
  const dd: (number | null)[] = [];
  let peak = 1;
  for (const v of main.values) {
    if (v == null) dd.push(null);
    else peak = Math.max(peak, v), dd.push(v / peak - 1);
  }
  const worst = Math.min(0, ...dd.filter((v): v is number => v != null));
  const showDd = withDrawdown && dates.length > 1;
  const ddH = showDd ? (compact ? 44 : 56) : 0, gap = showDd ? 28 : 0;
  const padL = compact ? 38 : 44, padR = compact ? 54 : 64, padT = 14, padB = 24;
  const H = height + gap + ddH;
  const plotB = height - padB; // the bottom of the main plot

  const all = series.flatMap((s) => s.values.filter((v): v is number => v != null));
  let lo = Math.min(1, ...all), hi = Math.max(1, ...all);
  const room = (hi - lo) * 0.1 || 0.01;
  lo -= room;
  hi += room;
  // Each line starts from 1 at the close before its first session: a point at x = padL.
  const x = (i: number) => padL + ((i + 1) / n) * (W - padL - padR);
  const y = (v: number) => padT + (1 - (v - lo) / (hi - lo)) * (plotB - padT);
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart block w-full h-auto select-none", role: "img" });
  s.setAttribute("aria-label", `${main.name}${ref ? ` against ${ref.name}` : ""}, ${dates.length} sessions`);

  // Grid: a few round percentages, written on the left.
  const span = hi - lo;
  const step = [0.0025, 0.005, 0.01, 0.02, 0.025, 0.05, 0.1, 0.2, 0.25, 0.5, 1, 2].find((st) => span / st <= (compact ? 4 : 5)) ?? 2;
  for (let v = Math.ceil((lo - 1) / step) * step; v <= hi - 1 + 1e-9; v += step) {
    const yy = y(1 + v);
    const zero = Math.abs(v) < 1e-9;
    s.append(svg("line", { x1: padL, x2: W - padR, y1: yy, y2: yy, stroke: zero ? "var(--color-line-strong)" : "var(--color-line)", "stroke-dasharray": zero ? "0" : "2 4" }));
    s.append(text(padL - 8, yy + 4, zero ? "0%" : signedPct(v, step < 0.01 ? 1 : 0), { "text-anchor": "end", fill: zero ? "var(--color-muted)" : "var(--color-faint)" }));
  }

  // Dates along the bottom, never closer than a label's width: over a few months, where each month
  // starts (with the year on January and the first); over less, days spread evenly.
  if (dates.length) {
    const room = compact ? 64 : 84;
    const when = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00Z`);
    const fmt = (iso: string, o: Intl.DateTimeFormatOptions) => when(iso).toLocaleDateString("en-US", { ...o, timeZone: "UTC" });
    let ticks: { i: number; label: string }[];
    if (dates.length > 60) {
      ticks = [];
      dates.forEach((d, i) => {
        if (i > 0 && d.slice(0, 7) === dates[i - 1].slice(0, 7)) return;
        const first = !ticks.length, jan = when(d).getUTCMonth() === 0;
        ticks.push({ i, label: first || jan ? `${fmt(d, { month: "short" })} ’${d.slice(2, 4)}` : fmt(d, { month: "short" }) });
      });
    } else {
      const count = Math.max(1, Math.floor((W - padL - padR) / room));
      const picks = new Set<number>([0]);
      if (dates.length > 1) for (let k = 1; k <= count; k++) picks.add(Math.round((k / count) * (dates.length - 1)));
      ticks = [...picks].sort((a, b) => a - b).map((i) => ({ i, label: fmt(dates[i], { month: "short", day: "numeric" }) }));
    }
    let lastX = -Infinity;
    for (const t of ticks) {
      const xx = x(t.i);
      if (xx - lastX < room || xx > W - padR + 6) continue;
      lastX = xx;
      s.append(svg("line", { x1: xx, x2: xx, y1: plotB, y2: plotB + 4, stroke: "var(--color-line-strong)" }));
      s.append(text(Math.min(xx, W - padR - 14), plotB + 17, t.label, { "text-anchor": "middle" }));
    }
  }

  // The gap between the bot and the index, or its distance from its start: green ahead, red behind.
  const base = ref ? ref.values : main.values.map(() => 1);
  const pts: Pt[] = [{ x: padL, a: 1, b: 1 }];
  main.values.forEach((v, i) => v != null && base[i] != null && pts.push({ x: x(i), a: v, b: base[i] as number }));
  const runs: { up: boolean; pts: Pt[] }[] = [];
  const extend = (p0: Pt, p1: Pt, up: boolean) => {
    const last = runs[runs.length - 1];
    if (last && last.up === up) last.pts.push(p1);
    else runs.push({ up, pts: [p0, p1] });
  };
  for (let k = 1; k < pts.length; k++) {
    const p0 = pts[k - 1], p1 = pts[k];
    const d0 = p0.a - p0.b, d1 = p1.a - p1.b;
    if (d0 * d1 < 0) {
      // They cross between two sessions: split there.
      const t = d0 / (d0 - d1);
      const mid = { x: p0.x + t * (p1.x - p0.x), a: p0.a + t * (p1.a - p0.a), b: p0.b + t * (p1.b - p0.b) };
      extend(p0, mid, d0 > 0);
      extend(mid, p1, d1 > 0);
    } else extend(p0, p1, d0 + d1 >= 0);
  }
  for (const r of runs) {
    const top = r.pts.map((p) => `${fixed(p.x)},${fixed(y(p.a))}`);
    const bottom = [...r.pts].reverse().map((p) => `${fixed(p.x)},${fixed(y(p.b))}`);
    s.append(svg("polygon", { points: [...top, ...bottom].join(" "), fill: r.up ? UP_SOFT : DOWN_SOFT }));
  }

  // The lines: the index first and quieter, the bot last and on top.
  for (const se of series) {
    const line = [`${padL},${fixed(y(1))}`];
    se.values.forEach((v, i) => v != null && line.push(`${fixed(x(i))},${fixed(y(v))}`));
    const el = svg("polyline", { points: line.join(" "), fill: "none", stroke: se.color, "stroke-width": se.width ?? 2,
      "stroke-linejoin": "round", "stroke-linecap": "round" });
    if (se.dashed) el.setAttribute("stroke-dasharray", "4 4");
    else el.setAttribute("pathLength", "2000"), el.classList.add("draw");
    s.append(el);
    // With few sessions, every close is a point.
    if (se === main && dates.length <= 12) se.values.forEach((v, i) => v != null && s.append(svg("circle", { cx: x(i), cy: y(v), r: 2.6, fill: "var(--color-page)", stroke: se.color, "stroke-width": 1.6 })));
  }
  // Where every line starts.
  s.append(svg("circle", { cx: padL, cy: y(1), r: 3, fill: "var(--color-page)", stroke: "var(--color-muted)", "stroke-width": 1.4 }));

  // Where each line ends, written at its end, nudged apart when they meet.
  type End = { se: Series; i: number; v: number; ty: number };
  const ends = series.map((se): End | null => {
    let i = se.values.length - 1;
    while (i >= 0 && se.values[i] == null) i--;
    return i < 0 ? null : { se, i, v: se.values[i] as number, ty: y(se.values[i] as number) };
  }).filter((e): e is End => e != null);
  const byY = [...ends].sort((a, b) => a.ty - b.ty);
  for (let k = 1; k < byY.length; k++) if (byY[k].ty - byY[k - 1].ty < 15) byY[k].ty = byY[k - 1].ty + 15;
  for (const e of ends) {
    const isMain = e.se === main;
    s.append(svg("circle", { cx: x(e.i), cy: y(e.v), r: isMain ? 3.4 : 2.6, fill: e.se.color }));
    s.append(text(W - padR + 8, e.ty + 4, signedPct(e.v - 1, 1), { fill: isMain ? (e.v >= 1 ? UP : DOWN) : "var(--color-muted)", "font-weight": isMain ? 600 : 400 }));
  }

  // Under it: how far the bot has fallen from its best close.
  const ddTop = height + gap;
  // At least 4% deep, so a small fall looks small.
  const depth = Math.max(-worst, 0.04) * 1.15;
  const yd = (v: number) => ddTop + (-v / depth) * ddH;
  if (showDd) {
    s.append(text(padL, ddTop - 9, "From its peak", { fill: "var(--color-muted)", "font-family": "var(--font-sans)", "font-size": 11.5 }));
    s.append(svg("line", { x1: padL, x2: W - padR, y1: ddTop, y2: ddTop, stroke: "var(--color-line-strong)" }));
    s.append(svg("line", { x1: padL, x2: W - padR, y1: ddTop + ddH, y2: ddTop + ddH, stroke: "var(--color-line)", "stroke-dasharray": "2 4" }));
    const line = [`${padL},${ddTop}`];
    dd.forEach((v, i) => v != null && line.push(`${fixed(x(i))},${fixed(yd(v))}`));
    s.append(svg("polygon", { points: [...line, `${fixed(x(dd.length - 1))},${ddTop}`].join(" "), fill: DOWN_SOFT }));
    s.append(svg("polyline", { points: line.join(" "), fill: "none", stroke: DOWN, "stroke-width": 1.2, "stroke-linejoin": "round", "stroke-opacity": 0.85 }));
    s.append(text(padL - 8, ddTop + 4, "0%", { "text-anchor": "end" }));
    if (worst < 0) s.append(text(W - padR + 8, yd(worst) + 4, signedPct(worst, 1), { fill: DOWN }));
  }

  // The reading under the pointer.
  const cross = svg("line", { y1: padT, y2: showDd ? ddTop + ddH : plotB, stroke: "var(--color-muted)", "stroke-width": 1, "stroke-dasharray": "3 3", visibility: "hidden" });
  const dots = series.map((se) => svg("circle", { r: se === main ? 4 : 3.2, fill: se.color, stroke: "var(--color-page)", "stroke-width": 2, visibility: "hidden" }));
  const ddDot = svg("circle", { r: 3, fill: DOWN, stroke: "var(--color-page)", "stroke-width": 1.5, visibility: "hidden" });
  s.append(cross, ...dots, ddDot);
  const tip = h("div", "chart-tip hidden");
  root.append(add(h("div", "relative"), s, tip));
  const hide = () => {
    for (const el of [cross, ...dots, ddDot]) el.setAttribute("visibility", "hidden");
    tip.classList.add("hidden");
  };
  const at = (el: SVGElement, cx: number, cy: number) => (el.setAttribute("cx", String(cx)), el.setAttribute("cy", String(cy)), el.setAttribute("visibility", "visible"));
  const row = (swatch: string | null, name: string, v: string, cls: string) => {
    const sw = h("span", "inline-block h-[3px] w-3 shrink-0 rounded");
    if (swatch) sw.style.background = swatch;
    else sw.style.visibility = "hidden";
    return add(h("div", "flex items-center gap-2"), sw, h("span", "truncate text-ink", name), h("span", `num ml-auto pl-3 ${cls}`, v));
  };
  const read = (ev: PointerEvent) => {
    if (!dates.length) return;
    const r = s.getBoundingClientRect();
    const px = ((ev.clientX - r.left) / r.width) * W;
    const i = Math.max(0, Math.min(dates.length - 1, Math.round(((px - padL) / (W - padL - padR)) * n - 1)));
    const xx = x(i);
    cross.setAttribute("x1", String(xx));
    cross.setAttribute("x2", String(xx));
    cross.setAttribute("visibility", "visible");
    series.forEach((se, k) => {
      const v = se.values[i];
      if (v == null) dots[k].setAttribute("visibility", "hidden");
      else at(dots[k], xx, y(v));
    });
    const lines = [...series].reverse().map((se) => {
      const v = se.values[i];
      return row(se.color, se.name, v == null ? "—" : signedPct(v - 1, 1), v == null ? "text-faint" : v >= 1 ? "text-up" : "text-down");
    });
    const mv = main.values[i], rv = ref?.values[i];
    if (ref && mv != null && rv != null) {
      lines.push(row(null, mv >= rv ? "Ahead by" : "Behind by", `${(Math.abs(mv - rv) * 100).toFixed(1)} pts`, mv >= rv ? "text-up" : "text-down"));
    }
    const d = dd[i];
    if (showDd && d != null) {
      at(ddDot, xx, yd(d));
      lines.push(row(null, "From its peak", signedPct(d, 1), d < 0 ? "text-down" : "text-muted"));
    }
    tip.replaceChildren(h("div", "num pb-0.5 text-muted", day(dates[i])), ...lines);
    tip.classList.remove("hidden");
    const left = (xx / W) * r.width;
    tip.style.left = left > r.width / 2 ? "" : `${left + 14}px`;
    tip.style.right = left > r.width / 2 ? `${r.width - left + 14}px` : "";
  };
  s.addEventListener("pointermove", read);
  s.addEventListener("pointerdown", read);
  s.addEventListener("pointerleave", hide);
}

// A chart with nothing on it yet: the line it will start from, and when.
export function chartWaiting(root: HTMLElement, message: string, height = 180): void {
  const W = Math.max(280, Math.round(root.clientWidth || root.parentElement?.clientWidth || 800));
  const padL = 44, padR = 64, mid = height / 2 + 10;
  const s = svg("svg", { viewBox: `0 0 ${W} ${height}`, class: "block w-full h-auto", "aria-hidden": "true" });
  for (const dy of [-0.28, 0.28]) s.append(svg("line", { x1: padL, x2: W - padR, y1: mid + dy * height, y2: mid + dy * height, stroke: "var(--color-line)", "stroke-dasharray": "2 4" }));
  s.append(svg("line", { x1: padL, x2: W - padR, y1: mid, y2: mid, stroke: "var(--color-line-strong)", "stroke-dasharray": "3 4" }));
  s.append(text(padL - 8, mid + 4, "0%", { "text-anchor": "end", fill: "var(--color-muted)" }));
  s.append(svg("circle", { cx: padL, cy: mid, r: 4, fill: "var(--color-page)", stroke: "var(--color-ink-strong)", "stroke-width": 1.6, class: "chart-pulse" }));
  root.replaceChildren(add(h("div", "relative"), s, h("p", "absolute inset-x-0 top-[14%] px-4 text-center text-[13px] text-muted", message)));
}
