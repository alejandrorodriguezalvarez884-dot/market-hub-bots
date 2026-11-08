// "Always and never": the companies the member picks by hand. Always: held at every close, each at
// least at the share they set (the bot's "always"). Never: never held (its "universe.exclude"). The
// same card on the draft, where it changes the draft, and on the owner's page, where each press is a
// switch from the next close. What a press does is the caller's (``act``); this only draws and asks.
import { add, h } from "./dom";
import { lang } from "../i18n";
import { companies as words } from "../i18n/companies";
import type { Pin } from "./types";
import { share } from "./words";

export type CompanyAction = "pin" | "unpin" | "exclude" | "include";

export type CompaniesOptions = {
  always: Pin[];
  never: string[];
  picks: string[]; // what it holds, to tap instead of writing a ticker
  act: (action: CompanyAction, ticker: string, minWeight?: number) => Promise<void>; // throws with a message for the member
  foot?: string;
};

function button(cls: string, text: string, onClick: () => void, label?: string): HTMLButtonElement {
  const b = h("button", cls, text);
  b.type = "button";
  if (label) b.setAttribute("aria-label", label);
  b.addEventListener("click", onClick);
  return b;
}

export function companies(o: CompaniesOptions): HTMLElement {
  const w = words[lang()];
  const root = h("div", "switch-card companies");
  let open: "always" | "never" | null = null;
  let editing: Pin | null = null; // the company whose least share is being changed
  let busy = false;
  let problem = "";

  async function run(action: CompanyAction, ticker: string, minWeight?: number) {
    const t = ticker.trim().toUpperCase();
    if (!t || busy) return;
    busy = true;
    problem = "";
    draw();
    try {
      await o.act(action, t, minWeight);
      open = editing = null;
    } catch (e) {
      problem = e instanceof Error ? e.message : w.failed;
    }
    busy = false;
    draw();
  }

  // The row to add a company to a list (or change the least share of one already in "Always").
  function form(kind: "always" | "never"): HTMLElement {
    const ticker = h("input", "field num w-24 py-1 text-[13px] uppercase");
    ticker.placeholder = w.ticker;
    ticker.setAttribute("aria-label", w.tickerLabel);
    ticker.autocomplete = "off";
    const least = h("input", "field num w-16 py-1 text-[13px]");
    least.type = "number";
    least.min = "0";
    least.max = "100";
    least.step = "0.5";
    least.placeholder = "0";
    least.setAttribute("aria-label", w.leastLabel);
    if (editing) {
      ticker.value = editing.ticker;
      ticker.readOnly = true;
      least.value = editing.min_weight ? share(editing.min_weight, "en") : "";
    }
    const send = () => {
      if (kind === "never") return void run("exclude", ticker.value);
      const x = Number(least.value.replace(",", ".") || 0);
      void run("pin", ticker.value, Number.isFinite(x) ? Math.round(x * 10) / 1000 : 0);
    };
    for (const input of [ticker, least]) input.addEventListener("keydown", (e) => e.key === "Enter" && send());
    const listed = new Set([...o.always.map((p) => p.ticker), ...o.never]);
    const picks = editing ? [] : o.picks.filter((t) => !listed.has(t)).slice(0, 12);
    const row = add(h("div", "mt-2 flex flex-wrap items-center gap-2"), ticker,
      kind === "always" ? add(h("label", "flex items-center gap-1.5 text-[12.5px] text-muted"), w.atLeast, least, h("span", "", w.optional)) : null,
      button("btn btn-primary py-1 text-[13px]", editing ? w.save : w.addIt, send),
      button("btn btn-ghost py-1 text-[13px]", w.cancel, () => ((open = editing = null), (problem = ""), draw())));
    const out = add(h("div", "mt-1"), row);
    if (picks.length) {
      out.append(h("p", "mt-2 text-[12px] text-faint", w.tapOne), add(h("div", "mt-1.5 flex flex-wrap gap-1.5"),
        ...picks.map((t) => button("chip-pick num", t, () => {
          if (kind === "never") return void run("exclude", t);
          ticker.value = t;
          least.focus();
        }))));
    }
    queueMicrotask(() => (editing ? least : ticker).focus({ preventScroll: true }));
    return out;
  }

  function list(kind: "always" | "never"): HTMLElement {
    const pins = kind === "always";
    const chips = add(h("div", "mt-2 flex flex-wrap items-center gap-1.5"),
      ...(pins ? o.always : o.never.map((t) => ({ ticker: t, min_weight: 0 }))).map((p) => {
        const label = pins && p.min_weight > 0 ? `${p.ticker} · ${w.least(share(p.min_weight))}` : p.ticker;
        const name = pins ? button("chip-name", label, () => ((open = "always"), (editing = p), draw()), w.change(p.ticker)) : h("span", "", label);
        return add(h(`span`, `chip-x num ${pins ? "is-always" : "is-never"}`), name,
          button("chip-x-btn", "×", () => void run(pins ? "unpin" : "include", p.ticker), w.remove(p.ticker)));
      }),
      (pins ? o.always : o.never).length ? null : h("span", "text-[12.5px] text-faint", w.none),
      open === kind ? null : button("chip-add", w.add, () => ((open = kind), (editing = null), (problem = ""), draw())));
    return add(h("div", "companies-row"),
      add(h("div", "flex flex-wrap items-baseline gap-x-2"), h("p", `companies-kind ${pins ? "is-always" : "is-never"}`, pins ? w.always : w.never),
        h("p", "text-[12.5px] text-muted", pins ? w.alwaysHint : w.neverHint)),
      chips, open === kind ? form(kind) : null);
  }

  function draw() {
    root.classList.toggle("is-busy", busy);
    root.replaceChildren();
    add(root,
      h("p", "text-[14px] font-medium text-ink-strong", w.title),
      h("p", "text-[12.5px] text-muted", w.sub),
      list("always"), list("never"),
      problem ? h("p", "mt-3 text-[12.5px] text-warn", problem) : null,
      o.foot ? h("p", "mt-3 text-[12px] text-faint", o.foot) : null);
  }

  draw();
  return root;
}
