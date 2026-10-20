// Charts drawn as SVG: a sparkline for a line of the board, and a bot against the index on its page.
// Values are growth from 1 (1.12 is +12%).
import { add, h, svg } from "./dom";
import { day, signedPct } from "./format";

const UP = "var(--color-up)";
const DOWN = "var(--color-down)";

export function sparkline(values: number[], width = 76, height = 24, color?: string): SVGSVGElement {
  const s = svg("svg", { viewBox: `0 0 ${width} ${height}`, width, height, "aria-hidden": "true", class: "block overflow-visible" });
  if (values.length < 2) {
    s.append(svg("line", { x1: 0, x2: width, y1: height / 2, y2: height / 2, stroke: "var(--color-line-strong)", "stroke-dasharray": "2 3" }));
    return s;
  }
  const lo = Math.min(1, ...values), hi = Math.max(1, ...values);
  const y = (v: number) => (hi === lo ? height / 2 : height - 2 - ((v - lo) / (hi - lo)) * (height - 4));
  const x = (i: number) => (i / (values.length - 1)) * width;
  const stroke = color ?? (values[values.length - 1] >= 1 ? UP : DOWN);
  s.append(svg("line", { x1: 0, x2: width, y1: y(1), y2: y(1), stroke: "var(--color-line-strong)", "stroke-dasharray": "2 3" }));
  s.append(svg("polyline", { points: values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" "), fill: "none", stroke,
    "stroke-width": 1.5, "stroke-linejoin": "round", "stroke-linecap": "round" }));
  return s;
}

export type Series = { name: string; values: (number | null)[]; color: string; width?: number; dashed?: boolean };

// Lines over the same sessions, from 1 the session before the first. Hovering reads each one.
export function lineChart(root: HTMLElement, dates: string[], series: Series[], height = 280): void {
  root.replaceChildren();
  // Drawn at the width it is shown at, so its words keep their size.
  const W = Math.max(300, Math.round(root.clientWidth || 800)), H = height, padL = 8, padR = 56, padT = 14, padB = 26;
  const all = series.flatMap((s) => s.values.filter((v): v is number => v != null));
  let lo = Math.min(1, ...all), hi = Math.max(1, ...all);
  const room = (hi - lo) * 0.08 || 0.01;
  lo -= room;
  hi += room;
  const n = Math.max(dates.length, 1);
  // Each line starts from 1 at the close before its first session: a point at x = padL.
  const x = (i: number) => padL + ((i + 1) / n) * (W - padL - padR);
  const y = (v: number) => padT + (1 - (v - lo) / (hi - lo)) * (H - padT - padB);
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "block w-full h-auto select-none", role: "img" });
  // Grid: a few round percentages.
  const span = hi - lo;
  const step = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1].find((st) => span / st <= 5) ?? 1;
  for (let v = Math.ceil((lo - 1) / step) * step; v <= hi - 1 + 1e-9; v += step) {
    const yy = y(1 + v);
    const zero = Math.abs(v) < 1e-9;
    s.append(svg("line", { x1: padL, x2: W - padR, y1: yy, y2: yy, stroke: zero ? "var(--color-line-strong)" : "var(--color-line)", "stroke-dasharray": zero ? "0" : "2 4" }));
    const t = svg("text", { x: W - padR + 8, y: yy + 4, fill: "var(--color-faint)", "font-size": 11, "font-family": "var(--font-mono)" });
    t.textContent = zero ? "0%" : signedPct(v, step < 0.01 ? 1 : 0);
    s.append(t);
  }
  if (dates.length) {
    for (const [i, anchor] of [[0, "start"], [dates.length - 1, "end"]] as const) {
      const t = svg("text", { x: i === 0 ? padL : x(i), y: H - 6, fill: "var(--color-faint)", "font-size": 11, "text-anchor": anchor, "font-family": "var(--font-mono)" });
      t.textContent = day(dates[i]);
      s.append(t);
    }
  }
  for (const se of series) {
    const pts = [`${padL},${y(1).toFixed(1)}`];
    se.values.forEach((v, i) => v != null && pts.push(`${x(i).toFixed(1)},${y(v).toFixed(1)}`));
    const line = svg("polyline", { points: pts.join(" "), fill: "none", stroke: se.color, "stroke-width": se.width ?? 2,
      "stroke-linejoin": "round", "stroke-linecap": "round" });
    if (se.dashed) line.setAttribute("stroke-dasharray", "4 4");
    else line.setAttribute("pathLength", "2000"), line.classList.add("draw");
    s.append(line);
  }
  // The reading under the pointer.
  const cross = svg("line", { y1: padT, y2: H - padB, stroke: "var(--color-muted)", "stroke-width": 1, visibility: "hidden" });
  s.append(cross);
  const tip = h("div", "pointer-events-none absolute top-2 hidden rounded-[3px] border border-line-strong bg-deep/95 px-2.5 py-1.5 text-[12px] shadow-lg");
  root.append(add(h("div", "relative"), s, tip));
  const read = (ev: PointerEvent) => {
    if (!dates.length) return;
    const r = s.getBoundingClientRect();
    const px = ((ev.clientX - r.left) / r.width) * W;
    const i = Math.max(0, Math.min(dates.length - 1, Math.round(((px - padL) / (W - padL - padR)) * n - 1)));
    cross.setAttribute("x1", String(x(i)));
    cross.setAttribute("x2", String(x(i)));
    cross.setAttribute("visibility", "visible");
    tip.replaceChildren(h("div", "num text-muted", day(dates[i])), ...series.map((se) => {
      const v = se.values[i];
      const swatch = h("span", "inline-block h-[3px] w-3 rounded");
      swatch.style.background = se.color;
      return add(h("div", "flex items-center gap-2"), swatch, h("span", "text-ink", se.name),
        h("span", `num ml-auto pl-3 ${v == null ? "text-faint" : v >= 1 ? "text-up" : "text-down"}`, v == null ? "—" : signedPct(v - 1, 1)));
    }));
    tip.classList.remove("hidden");
    const left = (x(i) / W) * r.width;
    tip.style.left = left > r.width / 2 ? "" : `${left + 12}px`;
    tip.style.right = left > r.width / 2 ? `${r.width - left + 12}px` : "";
  };
  s.addEventListener("pointermove", read);
  s.addEventListener("pointerleave", () => (cross.setAttribute("visibility", "hidden"), tip.classList.add("hidden")));
}
