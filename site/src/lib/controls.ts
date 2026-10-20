// The controls of "Change it": a slider that says its value, a row of choices, an on/off switch,
// and the before → after of a bot's rules in words. In the ink, as the rest of the site.
import { add, h } from "./dom";
import type { Line } from "./words";

// A slider with its value written beside it. ``show`` writes the value; ``onInput`` gets every move.
export function slider(o: { min: number; max: number; step: number; value: number; show: (v: number) => string; onInput: (v: number) => void; label?: string }): HTMLElement {
  const input = h("input", "slider");
  input.type = "range";
  input.min = String(o.min);
  input.max = String(o.max);
  input.step = String(o.step);
  input.value = String(o.value);
  if (o.label) input.setAttribute("aria-label", o.label);
  const out = h("output", "slider-value num", o.show(o.value));
  const paint = () => input.style.setProperty("--p", `${((Number(input.value) - o.min) / (o.max - o.min || 1)) * 100}%`);
  input.addEventListener("input", () => {
    const v = Number(input.value);
    out.textContent = o.show(v);
    paint();
    o.onInput(v);
  });
  paint();
  return add(h("div", "slider-row"), input, out);
}

// One choice among a few, as a row of buttons.
export function segmented<T extends string>(options: [T, string][], value: T, onPick: (v: T) => void, label?: string): HTMLElement {
  const box = h("div", "seg");
  box.setAttribute("role", "radiogroup");
  if (label) box.setAttribute("aria-label", label);
  for (const [v, text] of options) {
    const b = h("button", "seg-btn", text);
    b.type = "button";
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", String(v === value));
    b.addEventListener("click", () => {
      box.querySelectorAll(".seg-btn").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
      onPick(v);
    });
    box.append(b);
  }
  return box;
}

// An on/off switch.
export function toggle(on: boolean, label: string, onFlip: (on: boolean) => void): HTMLButtonElement {
  const b = h("button", "toggle");
  b.type = "button";
  b.setAttribute("role", "switch");
  b.setAttribute("aria-checked", String(on));
  b.setAttribute("aria-label", label);
  b.addEventListener("click", () => {
    const now = b.getAttribute("aria-checked") !== "true";
    b.setAttribute("aria-checked", String(now));
    onFlip(now);
  });
  return b;
}

// The rules before and after, line by line: what goes struck through, what comes in full, and what
// stays folded into one line (or shown, with ``all``).
export function rulesDiff(lines: Line[], all = false): HTMLElement {
  const list = h("ul", "diff");
  const same = lines.filter((l) => l.kind === "same").length;
  for (const l of lines) {
    if (l.kind === "same" && !all) continue;
    list.append(add(h("li", `diff-line is-${l.kind}`), h("span", "diff-sign", l.kind === "new" ? "+" : l.kind === "gone" ? "−" : ""), h("span", "", l.text)));
  }
  if (!lines.some((l) => l.kind !== "same")) list.append(h("li", "diff-line is-same", "No change to its rules."));
  if (same && !all) {
    const more = h("button", "diff-more", `${same} ${same === 1 ? "rule stays" : "rules stay"} as they are ›`);
    more.type = "button";
    more.addEventListener("click", () => list.replaceWith(rulesDiff(lines, true)));
    list.append(add(h("li"), more));
  }
  return list;
}
