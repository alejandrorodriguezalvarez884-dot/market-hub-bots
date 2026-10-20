// Every rule by hand, the advanced way of changing a bot: its parts as groups of sliders and
// choices (where it looks, what it keeps, how it ranks, how it holds, what it does when the market
// falls), with what changes in words as the member moves a control and the map of what it would
// hold at the last close. The companies left out with the switch are not here: they stay out until
// let back in.
import { add, h } from "./dom";
import { day } from "./format";
import { slider, segmented, rulesDiff, toggle } from "./controls";
import { treemap } from "./mybot";
import { ApiError, api } from "./site";
import type { Bot, Checked, Factor, Spec } from "./types";
import { changed, describe, diff, figure } from "./words";

const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x));
const NAMES: Record<string, string> = {
  momentum: "Return", trend: "Close against its average", sma_cross: "Short average against long", volatility: "Volatility",
  rsi: "RSI", drawdown: "Distance from its high", beta: "Beta to the S&P 500",
};
// The span of a bound's slider for each figure, its step and a starting value (fractions for the
// percentages).
const BOUNDS: Record<string, [number, number, number, number]> = {
  momentum: [-0.5, 1, 0.01, 0], trend: [-0.3, 0.3, 0.01, 0], sma_cross: [-0.2, 0.2, 0.01, 0], volatility: [0, 1, 0.01, 0.3],
  rsi: [0, 100, 1, 50], drawdown: [-0.6, 0, 0.01, -0.1], beta: [0, 3, 0.05, 1],
};
const SETTING: Record<string, string> = { days: "Over", skip: "Leaving out the last", fast: "Short average", slow: "Long average" };

export type EditorOptions = {
  before: Bot; // the bot as it is, or as it will be at the next close: what the change is measured against
  now: Record<string, number>; // what it holds now, drawn until a preview is read
  blocked: string | null; // why new rules cannot be applied today, if they cannot
  apply: (bot: Bot) => Promise<void>;
  back: () => void;
};

function group(title: string, hint: string | null, ...body: (Node | null)[]): HTMLElement {
  return add(h("section", "group"), add(h("header", "group-head"), h("h3", "group-title", title), hint ? h("p", "group-hint", hint) : null), ...body);
}

function row(label: string, control: Node): HTMLElement {
  return add(h("div", "ctl"), label ? h("span", "ctl-label", label) : null, control);
}

export function editor(spec: Spec, start: Bot, o: EditorOptions): HTMLElement {
  const bot: Bot = clone(start);
  const controls = h("div", "space-y-3");
  const words = h("div");
  const map = h("div");
  const mapNote = h("p", "mt-2 text-[12px] text-faint");
  const problem = h("p", "mt-3 hidden text-[12.5px] text-warn");
  const apply = h("button", "btn btn-primary w-full", "Apply at the next close");
  apply.type = "button";
  // On a phone what changes is under every group: a bar at the foot keeps the count and the button.
  const count = h("span", "min-w-0 flex-1 text-[13px] text-ink");
  const applyBar = h("button", "btn btn-primary py-1.5 text-[13px]", "Apply");
  applyBar.type = "button";
  applyBar.addEventListener("click", () => apply.click());
  let timer = 0, resting = false, previewed = "";

  // --- What changes, live ---

  function live() {
    const lines = diff(describe(o.before), describe(bot));
    words.replaceChildren(rulesDiff(lines));
    const differs = changed(lines) || bot.name !== o.before.name || bot.about !== o.before.about;
    apply.disabled = applyBar.disabled = !differs || !!o.blocked;
    const n = lines.filter((l) => l.kind === "new").length + (bot.name !== o.before.name || bot.about !== o.before.about ? 1 : 0);
    count.textContent = !differs ? "No change yet" : n === 0 ? "A rule goes" : `${n} ${n === 1 ? "rule changes" : "rules change"} · at the next close`;
    clearTimeout(timer);
    if (differs && !resting) timer = window.setTimeout(preview, 1200);
  }

  async function preview() {
    const key = JSON.stringify(bot);
    if (key === previewed) return;
    previewed = key;
    mapNote.textContent = "Reading the last close…";
    try {
      const got = await api<Checked>("/api/bots/preview", { method: "POST", body: { bot } });
      if (JSON.stringify(bot) !== key) return;
      problem.classList.add("hidden");
      if (got.holds) {
        map.replaceChildren(treemap(got.holds.weights, null, { preview: true, small: true }));
        mapNote.textContent = `What these rules would hold at the close of ${day(got.holds.as_of)}.`;
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) {
        resting = true;
        mapNote.textContent = "The map rests for a while; the rules in words still follow every move.";
      } else {
        problem.textContent = e instanceof Error ? e.message : "These rules could not be read.";
        problem.classList.remove("hidden");
        mapNote.textContent = "";
      }
    }
  }

  // --- A figure and its settings ---

  function factor(f: Factor, extra: "bounds" | "weight" | "market", remove: (() => void) | null): HTMLElement {
    const box = h("div", "factor");
    const pick = h("select", "field factor-pick");
    pick.setAttribute("aria-label", "Figure");
    for (const k of Object.keys(spec.factors)) {
      const opt = h("option", "", NAMES[k] ?? k);
      opt.value = k;
      opt.selected = k === f.factor;
      pick.append(opt);
    }
    pick.addEventListener("change", () => {
      for (const k of Object.keys(f)) if (!["factor", "min", "max", "weight", "cash"].includes(k)) delete f[k];
      f.factor = pick.value;
      for (const [k, s] of Object.entries(spec.factors[f.factor].settings)) f[k] = s.default ?? Math.min(s.max, Math.max(s.min, 63));
      if (f.factor === "sma_cross") Object.assign(f, { fast: 50, slow: 200 });
      if (extra !== "weight") {
        const [, top, , mid] = BOUNDS[f.factor] ?? [0, 1, 0.01, 0];
        if (f.min != null) f.min = mid;
        if (f.max != null) f.max = f.min != null ? top : mid;
      }
      draw();
    });
    const top = add(h("div", "factor-top"), pick);
    if (remove) {
      const x = h("button", "factor-x", "×");
      x.type = "button";
      x.setAttribute("aria-label", "Remove");
      x.addEventListener("click", () => (remove(), draw()));
      top.append(x);
    }
    box.append(top);
    for (const [k, s] of Object.entries(spec.factors[f.factor]?.settings ?? {})) {
      box.append(row(SETTING[k] ?? k, slider({ min: s.min, max: s.max, step: 1, value: Number(f[k] ?? s.default ?? s.min), label: SETTING[k] ?? k,
        show: (v) => `${v} sessions`, onInput: (v) => ((f[k] = v), live()) })));
    }
    if (extra === "weight") {
      box.append(row("Prefers", slider({ min: -5, max: 5, step: 0.5, value: f.weight ?? 1, label: "Weight",
        show: (v) => (v === 0 ? "—" : `${v > 0 ? "higher" : "lower"} · ×${Math.abs(v)}`),
        onInput: (v) => {
          f.weight = v === 0 ? (Math.sign(f.weight ?? 1) || 1) * 0.5 : v;
          live();
        } })));
      return box;
    }
    // Bounds: at least, at most, or between.
    const [lo0, hi0, step, mid] = BOUNDS[f.factor] ?? [-1, 1, 0.01, 0];
    const lo = Math.min(lo0, f.min ?? lo0, f.max ?? lo0), hi = Math.max(hi0, f.min ?? hi0, f.max ?? hi0);
    const show = (v: number) => (f.factor === "volatility" ? `${(v * 100).toFixed(0)}%` : figure(f.factor, v));
    const mode = f.min != null && f.max != null ? "between" : f.max != null ? "most" : "least";
    box.append(row(extra === "market" ? "Holds stocks while it is" : "Keeps a stock if it is", segmented([["least", "At least"], ["most", "At most"], ["between", "Between"]], mode, (m) => {
      const a = f.min ?? f.max ?? mid, b = f.max ?? f.min ?? mid;
      if (m === "least") (f.min = a), delete f.max;
      else if (m === "most") (f.max = b), delete f.min;
      else (f.min = Math.min(a, b)), (f.max = Math.max(a, b, Math.min(hi, a + (hi - lo) / 4)));
      draw();
    }, "Bound")));
    if (f.min != null) box.append(row(mode === "between" ? "From" : "", slider({ min: lo, max: hi, step, value: f.min, show, label: "At least", onInput: (v) => ((f.min = v), live()) })));
    if (f.max != null) box.append(row(mode === "between" ? "To" : "", slider({ min: lo, max: hi, step, value: f.max, show, label: "At most", onInput: (v) => ((f.max = v), live()) })));
    if (extra === "market") {
      box.append(row("Otherwise, in cash", slider({ min: 0.05, max: 1, step: 0.05, value: f.cash ?? 1, label: "Cash", show: (v) => `${(v * 100).toFixed(0)}%`, onInput: (v) => ((f.cash = v), live()) })));
    }
    return box;
  }

  function more(text: string, onClick: () => void): HTMLButtonElement {
    const b = h("button", "add-btn", text);
    b.type = "button";
    b.addEventListener("click", onClick);
    return b;
  }

  // --- The groups ---

  function draw() {
    const byList = Array.isArray(bot.universe.tickers);
    const universe = group("Where it looks", null,
      segmented([["largest", "The largest companies"], ["tickers", "A list I choose"]], byList ? "tickers" : "largest", (v) => {
        bot.universe = v === "tickers" ? { tickers: o.before.universe.tickers ?? [], exclude: bot.universe.exclude } : { largest: o.before.universe.largest ?? 100, exclude: bot.universe.exclude };
        draw();
      }, "Where it looks"));
    if (byList) {
      const list = h("textarea", "field num mt-3 min-h-[60px] uppercase");
      list.value = (bot.universe.tickers ?? []).join(", ");
      list.placeholder = "AAPL, MSFT, NVDA…";
      list.setAttribute("aria-label", "Tickers");
      list.addEventListener("input", () => ((bot.universe.tickers = list.value.split(/[\s,]+/).map((t) => t.trim().toUpperCase()).filter(Boolean)), live()));
      universe.append(list, h("p", "group-hint mt-1", "2 to 100 tickers, among the 500 largest US companies."));
    } else {
      universe.append(row("How many", slider({ min: spec.universe.largest.min, max: spec.universe.largest.max, step: 1, value: bot.universe.largest ?? 100, label: "How many companies",
        show: (v) => `the ${v} largest`, onInput: (v) => ((bot.universe.largest = v), live()) })));
    }

    const keeps = group("What it keeps", bot.filters.length ? "A company outside these bounds is left out." : "No filter: any company it looks at can be chosen.",
      ...bot.filters.map((f, i) => factor(f, "bounds", () => bot.filters.splice(i, 1))),
      bot.filters.length < 8 ? more("+ Add a filter", () => (bot.filters.push({ factor: "trend", days: 200, min: 0 }), draw())) : null);

    const ranks = group("How it ranks", "Those left are ranked on these figures.",
      ...bot.score.map((f, i) => factor(f, "weight", bot.score.length > 1 ? () => bot.score.splice(i, 1) : null)),
      bot.score.length < 8 ? more("+ Add a figure", () => (bot.score.push({ factor: "momentum", days: 126, skip: 0, weight: 1 }), draw())) : null);

    const holds = group("How it holds", null,
      row("Stocks", slider({ min: spec.hold.min, max: spec.hold.max, step: 1, value: bot.hold, label: "How many stocks", show: (v) => `the best ${v}`, onInput: (v) => ((bot.hold = v), live()) })),
      row("Sizes", segmented([["equal", "Equal"], ["inverse_volatility", "Calmer more"], ["score", "Best more"]], bot.weighting, (v) => ((bot.weighting = v), live()), "Weighting")),
      row("At most in one", slider({ min: 2, max: 100, step: 1, value: Math.round(bot.max_weight * 100), label: "Most in one stock",
        show: (v) => (v >= 100 ? "no limit" : `${v}%`), onInput: (v) => ((bot.max_weight = v / 100), live()) })),
      row("Looks again", segmented([["daily", "Every close"], ["weekly", "Weekly"], ["monthly", "Monthly"]], bot.rebalance, (v) => ((bot.rebalance = v), live()), "Rebalance")));

    const market = group("When the market falls", null,
      add(h("div", "flex items-center justify-between gap-3"), h("span", "text-[13.5px] text-ink", "Step aside to cash when the S&P 500 is out of bounds"),
        toggle(!!bot.market, "Market switch", (on) => {
          if (on) bot.market = { factor: "trend", days: 200, min: 0, cash: 1 };
          else delete bot.market;
          draw();
        })),
      bot.market ? factor(bot.market, "market", null) : null);

    const name = h("input", "field");
    name.value = bot.name;
    name.maxLength = 40;
    name.setAttribute("aria-label", "Name");
    name.addEventListener("input", () => ((bot.name = name.value), live()));
    const about = h("textarea", "field min-h-[60px]");
    about.value = bot.about;
    about.maxLength = 280;
    about.setAttribute("aria-label", "Idea");
    about.addEventListener("input", () => ((bot.about = about.value), live()));
    const named = group("Its name and idea", null, add(h("div", "grid gap-2"), name, about));

    controls.replaceChildren(universe, keeps, ranks, holds, market, named);
    live();
  }

  apply.addEventListener("click", async () => {
    apply.disabled = true;
    apply.textContent = "Applying…";
    problem.classList.add("hidden");
    try {
      await o.apply(bot);
    } catch (e) {
      problem.textContent = e instanceof Error ? e.message : "That did not work.";
      problem.classList.remove("hidden");
      apply.textContent = "Apply at the next close";
      apply.disabled = false;
    }
  });

  map.append(treemap(o.now, null, { small: true }));
  mapNote.textContent = "What it holds now. Move a control to see what it would hold.";
  const back = h("button", "back-btn", "← The simple way");
  back.type = "button";
  back.addEventListener("click", o.back);
  draw();
  if (JSON.stringify(start) !== JSON.stringify(o.before)) void preview();
  return add(h("div", "adv"),
    add(h("div", "flex flex-wrap items-baseline justify-between gap-2"), back, h("p", "text-[12.5px] text-muted", "Every rule, by hand")),
    add(h("div", "mt-4 grid gap-6 lg:grid-cols-[minmax(0,1fr)_21rem]"), controls,
      add(h("aside", "adv-side"),
        h("p", "label pb-2", "What changes"), words,
        add(h("div", "mt-5"), h("p", "label pb-2", "What it would hold"), map, mapNote),
        add(h("div", "mt-5"), apply, problem,
          h("p", "mt-2 text-[12px] text-faint", o.blocked ?? "From the next close, once a day. Its record goes on.")))),
    add(h("div", "adv-bar lg:hidden"), count, applyBar));
}
