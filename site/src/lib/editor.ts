// The rules editor on a member's page: every part of a bot as a control (universe, filters, score,
// holdings, weighting, cap, rebalance, market switch), its rules in words and what it would hold at
// the last close, before the change is applied from the next close. The companies left out with
// the switch are not here: they stay out until let back in.
import { add, h } from "./dom";
import { bars } from "./doings";
import { day } from "./format";
import { ApiError, api } from "./site";
import type { Bot, Checked, Factor, Spec } from "./types";

const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x));
const NAMES: Record<string, string> = {
  momentum: "Momentum (return)", trend: "Trend (close vs average)", sma_cross: "Average cross", volatility: "Volatility",
  rsi: "RSI", drawdown: "Distance from the high", beta: "Beta to the S&P 500",
};
const PERCENT = new Set(["momentum", "trend", "sma_cross", "volatility", "drawdown"]);

function field(label: string, control: HTMLElement, hint?: string): HTMLElement {
  return add(h("label", "block min-w-0"), h("span", "label block pb-1", label), control, hint ? h("span", "mt-1 block text-[12px] text-faint", hint) : null);
}

function number(value: number | undefined, onChange: (v: number | undefined) => void, step = "any", cls = "w-24"): HTMLInputElement {
  const i = h("input", `field num ${cls}`);
  i.type = "number";
  i.step = step;
  if (value !== undefined) i.value = String(value);
  i.addEventListener("input", () => onChange(i.value === "" ? undefined : Number(i.value)));
  return i;
}

function select(options: [string, string][], value: string, onChange: (v: string) => void, cls = ""): HTMLSelectElement {
  const s = h("select", `field ${cls}`);
  for (const [v, label] of options) {
    const o = h("option", "", label);
    o.value = v;
    o.selected = v === value;
    s.append(o);
  }
  s.addEventListener("change", () => onChange(s.value));
  return s;
}

export function editor(spec: Spec, start: Bot, applied: () => void): HTMLElement {
  let bot: Bot = clone(start);
  const root = h("div", "space-y-6");
  const out = h("div", "mt-4");

  // A factor and its settings; ``extra`` are the fields its place takes (bounds, weight, cash).
  function factorRow(f: Factor, extra: ("bounds" | "weight" | "cash")[], redraw: () => void, remove?: () => void): HTMLElement {
    const row = h("div", "flex flex-wrap items-end gap-2 border-t border-line pt-3");
    const settings = spec.factors[f.factor]?.settings ?? {};
    row.append(field("Figure", select(Object.keys(spec.factors).map((k) => [k, NAMES[k] ?? k]), f.factor, (v) => {
      for (const k of Object.keys(f)) if (!["factor", "min", "max", "weight", "cash"].includes(k)) delete f[k];
      f.factor = v;
      for (const [k, s] of Object.entries(spec.factors[v].settings)) f[k] = s.default ?? Math.min(s.max, Math.max(s.min, 63));
      if (v === "sma_cross") Object.assign(f, { fast: 50, slow: 200 });
      redraw();
    }, "w-52")));
    for (const [k, s] of Object.entries(settings)) {
      row.append(field(k, number(f[k] as number | undefined, (v) => (f[k] = v), "1"), `${s.min}–${s.max}`));
    }
    const pctHint = PERCENT.has(f.factor) ? "0.25 is +25%" : undefined;
    if (extra.includes("bounds")) {
      row.append(field("At least", number(f.min, (v) => (v === undefined ? delete f.min : (f.min = v))), pctHint),
        field("At most", number(f.max, (v) => (v === undefined ? delete f.max : (f.max = v))), pctHint));
    }
    if (extra.includes("weight")) row.append(field("Weight", number(f.weight, (v) => (f.weight = v)), "−5 to 5; below 0 prefers the lowest"));
    if (extra.includes("cash")) row.append(field("Cash when out", number(f.cash, (v) => (f.cash = v)), "0.5 is half"));
    if (remove) {
      const x = h("button", "btn btn-ghost py-1.5 text-[13px]", "Remove");
      x.type = "button";
      x.addEventListener("click", () => (remove(), redraw()));
      row.append(x);
    }
    return row;
  }

  function draw() {
    const name = h("input", "field");
    name.value = bot.name;
    name.maxLength = 40;
    name.addEventListener("input", () => (bot.name = name.value));
    const about = h("textarea", "field min-h-[64px]");
    about.value = bot.about;
    about.maxLength = 280;
    about.addEventListener("input", () => (bot.about = about.value));

    const byList = Array.isArray(bot.universe.tickers);
    const universe = add(h("div", "flex flex-wrap items-end gap-3"),
      field("Chooses among", select([["largest", "The largest US companies"], ["tickers", "A list of companies"]], byList ? "tickers" : "largest", (v) => {
        bot.universe = v === "tickers" ? { tickers: [], exclude: bot.universe.exclude } : { largest: 300, exclude: bot.universe.exclude };
        draw();
      }, "w-60")));
    if (byList) {
      const list = h("input", "field num w-full min-w-[16rem] sm:w-[28rem]");
      list.value = (bot.universe.tickers ?? []).join(", ");
      list.placeholder = "AAPL, MSFT, NVDA…";
      list.addEventListener("input", () => (bot.universe.tickers = list.value.split(/[\s,]+/).map((t) => t.trim().toUpperCase()).filter(Boolean)));
      universe.append(field("Tickers", list, "2 to 100, among the 500 largest"));
    } else {
      universe.append(field("How many", number(bot.universe.largest, (v) => (bot.universe.largest = v), "1"), `20–${spec.universe.largest.max}`));
    }

    const filters = add(h("div", "space-y-3"), ...bot.filters.map((f, i) => factorRow(f, ["bounds"], draw, () => bot.filters.splice(i, 1))));
    const addFilter = h("button", "btn btn-ghost py-1.5 text-[13px]", "+ Add a filter");
    addFilter.type = "button";
    addFilter.addEventListener("click", () => (bot.filters.push({ factor: "trend", days: 200, min: 0 }), draw()));
    const score = add(h("div", "space-y-3"), ...bot.score.map((f, i) => factorRow(f, ["weight"], draw, bot.score.length > 1 ? () => bot.score.splice(i, 1) : undefined)));
    const addScore = h("button", "btn btn-ghost py-1.5 text-[13px]", "+ Add a figure to score on");
    addScore.type = "button";
    addScore.addEventListener("click", () => (bot.score.push({ factor: "momentum", days: 126, skip: 0, weight: 1 }), draw()));

    const holding = add(h("div", "flex flex-wrap items-end gap-3"),
      field("Holds", number(bot.hold, (v) => (bot.hold = v as number), "1"), `1–${spec.hold.max} stocks`),
      field("Weighting", select([["equal", "Equal parts"], ["inverse_volatility", "The calmer with more"], ["score", "The best scored with more"]], bot.weighting, (v) => (bot.weighting = v), "w-56")),
      field("Most in one stock", number(Math.round(bot.max_weight * 100), (v) => (bot.max_weight = (v ?? 100) / 100), "1"), "% (2 to 100)"),
      field("Looks again", select([["daily", "Every close"], ["weekly", "Each week"], ["monthly", "Each month"]], bot.rebalance, (v) => (bot.rebalance = v), "w-40")));

    const marketOn = h("input", "");
    marketOn.type = "checkbox";
    marketOn.checked = !!bot.market;
    marketOn.addEventListener("change", () => {
      if (marketOn.checked) bot.market = { factor: "trend", days: 200, min: 0, cash: 1 };
      else delete bot.market;
      draw();
    });
    const market = add(h("div", "space-y-2"),
      add(h("label", "flex items-center gap-2 text-[13.5px] text-ink"), marketOn, "Step aside when the S&P 500 is out of bounds"),
      bot.market ? factorRow(bot.market, ["bounds", "cash"], draw) : null);

    const previewBtn = h("button", "btn btn-ghost", "Preview");
    previewBtn.type = "button";
    previewBtn.addEventListener("click", () => run(false));
    const applyBtn = h("button", "btn btn-primary", "Apply from the next close");
    applyBtn.type = "button";
    applyBtn.addEventListener("click", () => run(true));

    const block = (title: string, ...body: (Node | null)[]) => add(h("div", "chapter"), h("h3", "text-[14px] font-semibold text-ink-strong", title), add(h("div", "mt-3"), ...body));
    root.replaceChildren(
      add(h("div", "grid gap-3 sm:grid-cols-[1fr_1.4fr]"), field("Name", name), field("Idea", about)),
      block("Companies", universe),
      block("Filters", add(h("p", "mb-2 text-[12.5px] text-muted"), "A company outside these bounds is left out."), filters, add(h("div", "mt-3"), addFilter)),
      block("Score", add(h("p", "mb-2 text-[12.5px] text-muted"), "The companies left are ranked on these figures, each turned into a z-score and weighted."), score, add(h("div", "mt-3"), addScore)),
      block("Holdings", holding),
      block("Market switch", market),
      add(h("div", "flex flex-wrap gap-2 border-t border-line-strong pt-4"), previewBtn, applyBtn),
      out);
  }

  async function run(apply: boolean) {
    out.replaceChildren(h("p", "text-[13px] text-muted", apply ? "Applying…" : "Reading the last close…"));
    try {
      const checked = await api<Checked>("/api/bots/preview", { method: "POST", body: { bot } });
      const show = add(h("div", "frame p-4"), h("p", "label pb-2", "The bot, in words"),
        add(h("ul", "space-y-1.5 text-[13.5px] text-ink"), ...checked.rules.map((r) => add(h("li", "flex gap-2"), h("span", "text-muted", "›"), h("span", "", r)))),
        checked.holds ? add(h("div", "mt-4"), h("p", "label pb-1.5", `What it would hold at the close of ${day(checked.holds.as_of)} (a preview)`), bars(checked.holds.weights)) : null);
      if (!apply) return out.replaceChildren(show);
      if (!confirm("Apply these rules from the next close? The bot keeps its record, and its page will say that its rules changed. The rules can change once a day.")) {
        return out.replaceChildren(show);
      }
      await api("/api/bots/mine/rules", { method: "PUT", body: { bot } });
      applied();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "That did not work.";
      out.replaceChildren(add(h("div", "frame p-4"), h("p", "label pb-1", "Not yet"), h("p", "text-[13.5px] text-ink", msg)));
      if (e instanceof ApiError) return;
    }
  }

  draw();
  return root;
}

// What the chat proposed, loaded into the editor.
export const asBot = (b: Bot): Bot => clone(b);
