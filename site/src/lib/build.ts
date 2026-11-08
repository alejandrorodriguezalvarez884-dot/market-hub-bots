// Building a bot on the member's page, by talking to Claude.
// On the left, the conversation: the member's words, Claude's replies and, between them, what the
// code did (each draft checked and mapped, each backtest run), like the steps of an agent. On the
// right, the draft as it stands: its robot, its rules in words (what changed since the last one),
// what it would hold at the last close, a backtest on demand marked as a simulation of the past,
// and the button that sends it in. Nothing is kept on the server until it is sent in: the
// conversation and the draft live in this browser only.
import { add, h, svg } from "./dom";
import { day, pct, plural, signedPct, tone } from "./format";
import { lineChart, type Series } from "./chart";
import { rulesDiff, segmented } from "./controls";
import { closeOf } from "./change";
import { companies, type CompanyAction } from "./companies";
import { editor } from "./editor";
import { treemap } from "./mybot";
import { robotSvg } from "./robot";
import { ApiError, api } from "./site";
import type { Backtest, Bot, ChatStatus, DraftAnswer, MyBot, Preview, Spec } from "./types";
import { diff } from "./words";
import { lang } from "../i18n";
import { build as words } from "../i18n/build";
import { companies as companyWords } from "../i18n/companies";

export type BuildContext = {
  name: string; // the member's first name, as the board shows it
  seed: string; // the robot's slug while it is a draft
  spec: Spec;
  chat: ChatStatus; // its ``left`` is kept up to date here
  replacing: MyBot | null; // the bot a new one would replace, when building again from scratch
  sent: () => Promise<void>; // reads the page again once the bot is in
  cancel?: () => void; // back to the member's bot
};

type Turn =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; error?: boolean }
  | { role: "step"; kind: "draft" | "test" | "problems" | "hand"; text: string; note?: string };

type State = {
  talk: Turn[];
  draft: Bot | null;
  rules: string[];
  before: string[]; // the rules of the draft before this one
  holds: Preview;
  version: number;
  test: { years: number; result: Backtest } | null;
};

const fresh = (): State => ({ talk: [], draft: null, rules: [], before: [], holds: null, version: 0, test: null });

// --- Ideas to start from, each with a small drawing of what it does --------------------------------

// The words of each idea (its title, its line and what it says to Claude) are in i18n/build.ts.
type Idea = { key: keyof (typeof words)["en"]["ideas"]; glyph: (g: SVGSVGElement) => void };
const path = (d: string, extra: Record<string, string | number> = {}) => svg("path", { d, fill: "none", stroke: "currentColor", "stroke-width": 1.6, "stroke-linecap": "round", "stroke-linejoin": "round", ...extra });
const IDEAS: Idea[] = [
  { key: "momentum",
    glyph: (g) => g.append(path("M3 25 C16 23 24 17 32 12 S48 5 57 3")) },
  { key: "trend",
    glyph: (g) => g.append(path("M3 22 L57 9", { "stroke-dasharray": "2 3", opacity: 0.55 }), path("M3 19 L14 15 L22 17 L33 9 L42 11 L57 4")) },
  { key: "calm",
    glyph: (g) => g.append(path("M3 17 C11 15 17 16 25 14 S41 13 57 11")) },
  { key: "pullbacks",
    glyph: (g) => g.append(path("M3 25 L19 13 L27 18 L31 21 L40 10 L57 4"), svg("circle", { cx: 31, cy: 21, r: 2.2, fill: "currentColor" })) },
  { key: "highs",
    glyph: (g) => g.append(path("M3 4 L57 4", { "stroke-dasharray": "2 3", opacity: 0.55 }), path("M3 24 L15 17 L25 13 L35 9 L45 6 L57 5")) },
  { key: "megacaps",
    glyph: (g) => [[6, 14], [18, 8], [30, 18], [42, 11]].forEach(([x, y]) => g.append(svg("rect", { x, y, width: 8, height: 27 - y, rx: 1.5, fill: "currentColor", opacity: y === 8 ? 0.9 : 0.4 }))) },
];

function glyph(idea: Idea): SVGSVGElement {
  const g = svg("svg", { viewBox: "0 0 60 28", width: 60, height: 28, "aria-hidden": "true", class: "idea-glyph" });
  idea.glyph(g);
  return g;
}

function button(cls: string, text: string, onClick: (b: HTMLButtonElement) => void): HTMLButtonElement {
  const b = h("button", cls, text);
  b.type = "button";
  b.addEventListener("click", () => onClick(b));
  return b;
}

const message = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);
const short = (v: number | null | undefined) => signedPct(v ?? null, 1);

export function builder(ctx: BuildContext): HTMLElement {
  const { spec, chat } = ctx;
  const w = words[lang()];
  const KEY = `bl-build:${ctx.seed}`;
  let s: State = fresh();
  try {
    const kept = JSON.parse(localStorage.getItem(KEY) ?? "null");
    if (kept && Array.isArray(kept.talk)) s = { ...fresh(), ...kept };
  } catch {}
  const save = () => {
    try {
      localStorage.setItem(KEY, JSON.stringify({ ...s, talk: s.talk.slice(-40) }));
    } catch {}
  };
  let thinking = false;
  let testing = 0; // the years of the backtest being run, if one is
  let years = s.test?.years ?? 1;
  let confirming = false;
  let byHand = false;
  let sendNote = "";
  let mapping = false; // what the draft would hold is being read
  let mapNote = ""; // why it could not be
  const root = h("div", "build");

  // --- Talking ---

  async function say(text: string) {
    const msg = text.trim();
    if (!msg || thinking) return;
    s.talk.push({ role: "user", text: msg });
    thinking = true;
    confirming = false;
    draw();
    const history = s.talk.slice(0, -1).filter((t): t is { role: "user" | "assistant"; text: string } => t.role !== "step" && !("error" in t && t.error))
      .map((t) => ({ role: t.role, text: t.text })).slice(-10);
    const backtest = s.test ? { ...s.test.result, years: s.test.years, curve: undefined, months: undefined } : null;
    try {
      const got = await api<DraftAnswer>("/api/bots/draft/chat", { method: "POST", body: { message: msg, history, draft: s.draft, backtest } });
      if (typeof got.left === "number") chat.left = got.left;
      s.talk.push({ role: "assistant", text: got.reply });
      if (got.problems?.length) s.talk.push({ role: "step", kind: "problems", text: w.problemsStep, note: got.problems.join(" ") });
      if (got.proposal) {
        adopt(got.proposal, got.rules ?? [], got.holds ?? null, "draft");
        if (!s.holds) void mapIt();
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 503 && /messages today|mensajes/.test(e.message)) chat.left = 0;
      s.talk.push({ role: "assistant", text: message(e, w.chatFailed), error: true });
    }
    thinking = false;
    save();
    draw();
    root.querySelector<HTMLTextAreaElement>(".ask-input")?.focus({ preventScroll: true });
    root.querySelector(".build-talk > :last-child")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  // A new draft: from Claude, or from every rule by hand.
  function adopt(bot: Bot, rules: string[], holds: Preview, kind: "draft" | "hand") {
    s.before = s.rules;
    s.draft = bot;
    s.rules = rules;
    s.holds = holds;
    s.version += 1;
    s.test = null; // the backtest was of the draft before
    s.talk.push({ role: "step", kind, text: w.draftStep(s.version, bot.name), note: stepNote(rules, holds) });
  }

  function stepNote(rules: string[], holds: Preview): string {
    const held = holds ? w.holdsToday(plural(Object.keys(holds.weights).length, w.stock, w.stocks)) : mapping ? w.mapping : null;
    return [w.checked(plural(rules.length, w.rule, w.rules)), held].filter(Boolean).join(" · ");
  }

  // What the draft would hold at the last close, asked for after Claude's reply is on the page: on a
  // service just woken up, reading the closes of its companies takes a while.
  async function mapIt() {
    if (!s.draft || mapping) return;
    const version = s.version;
    const step = [...s.talk].reverse().find((t) => t.role === "step" && t.text.startsWith(w.draftStep(version, ""))) as Extract<Turn, { role: "step" }> | undefined;
    mapping = true;
    mapNote = "";
    if (step) step.note = stepNote(s.rules, null);
    draw();
    try {
      const seen = await api<{ holds: Preview }>("/api/bots/preview", { method: "POST", body: { bot: s.draft } });
      if (s.version === version) s.holds = seen.holds;
    } catch (e) {
      if (s.version === version) mapNote = message(e, w.mapFailed);
    }
    mapping = false;
    if (step && s.version === version) step.note = stepNote(s.rules, s.holds);
    save();
    draw();
  }

  async function backtest(n: number) {
    if (!s.draft || testing) return;
    testing = n;
    years = n;
    draw();
    try {
      const result = await api<Backtest>("/api/bots/backtest", { method: "POST", body: { bot: s.draft, years: n } });
      s.test = { years: n, result };
      s.talk.push({ role: "step", kind: "test", text: w.testStep(s.version, plural(n, w.year, w.years)),
        note: w.testNote(short(result.bot.total_return), short(result.benchmark.total_return), short(result.bot.max_drawdown)) });
      save();
    } catch (e) {
      s.talk.push({ role: "step", kind: "problems", text: w.testFailed, note: message(e, w.tryAgain) });
    }
    testing = 0;
    draw();
  }

  async function sendIn(b: HTMLButtonElement) {
    if (!s.draft) return;
    b.disabled = true;
    b.textContent = w.sending;
    try {
      await api("/api/bots/mine", { method: "PUT", body: { bot: s.draft } });
      try {
        localStorage.removeItem(KEY);
      } catch {}
      await ctx.sent();
    } catch (e) {
      sendNote = message(e, w.sendFailed);
      b.disabled = false;
      draw();
    }
  }

  function startOver() {
    if (s.talk.length && !confirm(w.startOverConfirm)) return;
    s = fresh();
    confirming = byHand = false;
    save();
    draw();
  }

  // --- The conversation (left) ---

  function turn(t: Turn): HTMLElement {
    if (t.role === "user") return h("p", "bubble is-me", t.text);
    if (t.role === "assistant") return add(h("div", `bubble is-them ${t.error ? "is-error" : ""}`), h("span", "bubble-who", "Claude"), h("span", "", t.text));
    const line = add(h("div", `step-line is-${t.kind}`), h("span", "step-dot"),
      add(h("div", "min-w-0"), h("p", "step-text", t.text), t.note ? h("p", "step-note", t.note) : null));
    if (t.kind === "draft" || t.kind === "hand") line.append(button("step-see lg:hidden", w.seeIt, () => root.querySelector(".draft")?.scrollIntoView({ behavior: "smooth", block: "start" })));
    return line;
  }

  function welcome(): HTMLElement {
    return add(h("div", "bubble is-them"), h("span", "bubble-who", "Claude"),
      h("span", "", w.greeting(ctx.name)));
  }

  function ideas(): HTMLElement {
    return add(h("div", "ideas"), ...IDEAS.map((i) => {
      const b = add(h("button", "idea"), glyph(i), h("span", "idea-title", w.ideas[i.key].title), h("span", "idea-line", w.ideas[i.key].line));
      b.type = "button";
      b.disabled = thinking || !canTalk();
      b.addEventListener("click", () => void say(w.ideas[i.key].say));
      return b;
    }));
  }

  const left = () => chat.left ?? chat.per_member_per_day;
  const canTalk = () => chat.on && left() > 0;

  function box(): HTMLElement {
    if (!chat.on) return add(h("div", "ask is-off"), h("p", "py-1 text-[14px] text-ink", w.chatOff));
    if (left() <= 0) {
      return add(h("div", "ask is-off"), add(h("div", "py-1"), h("p", "text-[14px] text-ink", w.usedUp(chat.per_member_per_day)),
        s.draft ? h("p", "mt-1 text-[12.5px] text-muted", w.draftStays) : null));
    }
    const form = h("form", "ask");
    const input = h("textarea", "ask-input");
    input.rows = 1;
    input.maxLength = 600;
    input.placeholder = s.draft ? w.askChange : w.askIdea;
    input.setAttribute("aria-label", w.askLabel);
    input.disabled = thinking;
    const go = h("button", "ask-send");
    go.type = "submit";
    go.disabled = thinking;
    go.setAttribute("aria-label", w.send);
    go.innerHTML = '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="M4 10h11M10.5 5.5 15 10l-4.5 4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    const grow = () => ((input.style.height = "auto"), (input.style.height = `${Math.min(input.scrollHeight, 160)}px`));
    input.addEventListener("input", grow);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) (e.preventDefault(), form.requestSubmit());
    });
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      void say(input.value);
    });
    return add(form, input, go);
  }

  function chips(): HTMLElement | null {
    if (!s.draft || !canTalk()) return null;
    const tap = ([label, text]: [string, string]) => button("suggest", label, () => void say(text));
    const row = add(h("div", "suggests"),
      tap(w.chips.fewer),
      tap(w.chips.more),
      tap(w.chips.calmer),
      s.draft.rebalance === "monthly" ? tap(w.chips.weekly) : tap(w.chips.monthly),
      s.test ? tap(w.chips.backtest) : null,
      tap(w.chips.rename));
    if (thinking) row.querySelectorAll("button").forEach((b) => (b.disabled = true));
    return row;
  }

  function conversation(): HTMLElement {
    const list = h("div", "build-talk");
    list.append(welcome());
    for (const t of s.talk.slice(-30)) list.append(turn(t));
    if (thinking) list.append(add(h("div", "bubble is-them"), h("span", "bubble-who", "Claude"), add(h("span", "dots-typing"), h("i"), h("i"), h("i"))));
    return list;
  }

  function chatSide(): HTMLElement {
    const started = s.talk.some((t) => t.role === "user");
    const meta = add(h("div", "mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-[12.5px]"),
      h("span", "num text-faint", chat.on ? w.left(left(), chat.per_member_per_day) : ""),
      s.talk.length ? button("text-muted underline-offset-4 hover:text-ink-strong hover:underline", w.startOver, startOver) : null);
    return add(h("section", "build-chat frame"),
      add(h("div", "build-head"), h("span", "build-mark", "✳"), add(h("div", "min-w-0"), h("h2", "change-title", w.title),
        h("p", "text-[12.5px] text-muted", w.sub)),
        ctx.cancel ? Object.assign(button("change-close", "×", ctx.cancel), { ariaLabel: w.backToBot, title: w.backToBot }) : null),
      conversation(),
      !started && !s.draft ? ideas() : null,
      add(h("div", "mt-4"), box()), chips(), meta);
  }

  // --- The draft (right) ---

  function testPanel(): HTMLElement {
    const box = h("div", "mt-6");
    const head = add(h("div", "flex flex-wrap items-center justify-between gap-2"), h("p", "label", w.wouldHaveDone), h("span", "tag", w.simulation));
    const pick = segmented([["1", w.oneYear], ["3", w.threeYears]], String(years) as "1" | "3", (v) => ((years = Number(v)), void backtest(years)), w.testYears);
    const t = s.test;
    if (!t) {
      const run = button("btn btn-ghost w-full", testing ? w.testing : w.runTest, () => void backtest(years));
      run.disabled = !!testing;
      return add(box, head, add(h("div", "mt-2 flex flex-wrap items-center gap-2"), pick, run),
        h("p", "mt-2 text-[12px] text-faint", w.testHint));
    }
    const r = t.result;
    const chart = h("div", "mt-3");
    requestAnimationFrame(() => {
      const series: Series[] = [
        { name: "S&P 500", values: r.curve.map((p) => p.benchmark), color: "var(--color-muted)", width: 1.5 },
        { name: s.draft?.name ?? w.draft, values: r.curve.map((p) => p.bot), color: "var(--color-signal)", width: 2.25 },
      ];
      lineChart(chart, r.curve.map((p) => p.date), series, 190, { ranges: false });
    });
    const cell = (label: string, bot: number | null, index: number | null) => add(h("div", "bt-cell"), h("span", "label", label),
      h("span", `num text-[17px] font-semibold ${tone(bot)}`, short(bot)), h("span", "num text-[11.5px] text-faint", `S&P ${short(index)}`));
    if (testing) (pick.querySelectorAll("button") as NodeListOf<HTMLButtonElement>).forEach((b) => (b.disabled = true));
    return add(box, head, add(h("div", "mt-2 flex items-center gap-2"), pick, testing ? h("span", "text-[12px] text-faint", w.runningShort) : null),
      chart,
      add(h("div", "bt-cells"), cell(w.total, r.bot.total_return, r.benchmark.total_return), cell(w.aYear, r.bot.annual_return, r.benchmark.annual_return),
        cell(w.worstFall, r.bot.max_drawdown, r.benchmark.max_drawdown)),
      h("p", "mt-2 text-[12px] text-faint", w.span(day(r.start), day(r.end), pct(r.turnover_per_year, 0))),
      add(h("ul", "mt-2 space-y-1"), ...r.notes.map((n) => h("li", "text-[12px] text-faint", n))));
  }

  function sendBox(): HTMLElement {
    const box = h("div", "send-box");
    const starts = day(closeOf(new Date().toISOString()));
    if (!confirming) {
      return add(box, button("btn btn-signal w-full", w.sendIn, () => ((confirming = true), (sendNote = ""), draw())),
        h("p", "mt-2 text-center text-[12px] text-faint", w.startsAt(starts)));
    }
    const name = s.draft!.name;
    return add(box, h("p", "label", w.beforeIn),
      add(h("ul", "mt-2 space-y-1.5 text-[13.5px] text-ink"),
        add(h("li", "flex gap-2"), h("span", "text-muted", "›"), h("span", "", w.publicLine(name, ctx.name))),
        add(h("li", "flex gap-2"), h("span", "text-muted", "›"), h("span", "", w.rulesYours)),
        add(h("li", "flex gap-2"), h("span", "text-muted", "›"), h("span", "", w.paperFrom(starts))),
        ctx.replacing ? add(h("li", "flex gap-2"), h("span", "text-warn", "›"), h("span", "text-warn", w.replaces(ctx.replacing.name))) : null),
      add(h("div", "mt-3 flex flex-wrap gap-2"), button("btn btn-signal flex-1", w.sendIn, (b) => void sendIn(b)),
        button("btn btn-ghost", w.notYet, () => ((confirming = false), draw()))),
      sendNote ? h("p", "mt-2 text-[12.5px] text-warn", sendNote) : null);
  }

  // Always and never, on the draft: each press changes the draft at once, checked by the service.
  async function pick(action: CompanyAction, t: string, min?: number) {
    if (!s.draft) return;
    const bot: Bot = JSON.parse(JSON.stringify(s.draft));
    // A company is in one list at most: always takes it out of never, and never out of always.
    const pins = action === "include" ? (bot.always ?? []) : (bot.always ?? []).filter((p) => p.ticker !== t);
    const never = action === "unpin" ? bot.universe.exclude : bot.universe.exclude.filter((x) => x !== t);
    if (action === "pin") pins.push({ ticker: t, min_weight: min ?? 0 });
    if (action === "exclude") never.push(t);
    bot.universe.exclude = never;
    if (pins.length) bot.always = pins;
    else delete bot.always;
    const seen = await api<{ bot: Bot; rules: string[]; holds: Preview }>("/api/bots/preview", { method: "POST", body: { bot } });
    adopt(seen.bot, seen.rules, seen.holds, "hand");
    save();
    draw();
  }

  function draftSide(): HTMLElement {
    const card = h("aside", "draft frame");
    const face = h("span", `robot draft-face ${s.draft ? (s.test ? "is-tested" : "is-drafted") : ""}`);
    face.innerHTML = robotSvg(ctx.seed, 64);
    if (!s.draft) {
      return add(card, add(h("div", "flex items-center gap-4"), face, add(h("div", "min-w-0"), h("p", "label", w.yourBot), h("p", "mt-1 text-[15px] text-ink-strong", w.takesShape))),
        add(h("ol", "draft-steps"),
          add(h("li", ""), h("span", "step-n", "1"), h("span", "", w.steps[0])),
          add(h("li", ""), h("span", "step-n", "2"), h("span", "", w.steps[1])),
          add(h("li", ""), h("span", "step-n", "3"), h("span", "", w.steps[2]))));
    }
    const d = s.draft;
    const held = s.holds ? Object.keys(s.holds.weights).length : 0;
    return add(card,
      add(h("div", "flex items-center gap-4"), face, add(h("div", "min-w-0 flex-1"),
        add(h("p", "flex items-center gap-2"), h("span", "label", w.yourBot), h("span", "tag", w.draftTag(s.version))),
        h("h2", "mt-1 text-[19px] font-medium leading-tight text-ink-strong", d.name),
        d.about ? h("p", "mt-1 text-[13px] text-muted", d.about) : null)),
      add(h("div", "mt-5"), h("p", "label pb-2", s.before.length ? w.rulesChanged : w.rulesInWords),
        s.before.length ? rulesDiff(diff(s.before, s.rules), true)
          : add(h("ul", "space-y-1.5 text-[13.5px] text-ink"), ...s.rules.map((r) => add(h("li", "flex gap-2"), h("span", "text-muted", "›"), h("span", "", r))))),
      add(h("div", "mt-5"), companies({ always: d.always ?? [], never: d.universe.exclude, picks: Object.keys(s.holds?.weights ?? {}),
        act: pick, foot: companyWords[lang()].draftNote })),
      s.holds ? add(h("div", "mt-6"), add(h("div", "flex items-baseline justify-between gap-2 pb-2"), h("p", "label", w.wouldHold),
        h("span", "text-[12px] text-faint", w.heldAt(plural(held, w.stock, w.stocks), day(s.holds.as_of)))),
        treemap(s.holds.weights, null, { preview: true, small: true }))
        : add(h("div", "mt-6"), h("p", "label pb-2", w.wouldHold),
          mapping ? add(h("div", "skeleton grid h-[180px] place-items-center"), h("span", "text-[12.5px] text-muted", w.readingCloses))
            : add(h("div", "flex flex-wrap items-center gap-3"), h("p", "text-[12.5px] text-muted", mapNote || w.notRead),
              button("btn btn-ghost py-1 text-[13px]", w.retry, () => void mapIt()))),
      testPanel(),
      add(h("div", "mt-5 flex justify-end"), button("text-[12.5px] text-muted underline-offset-4 hover:text-ink-strong hover:underline", w.byHand, () => ((byHand = true), draw()))),
      sendBox());
  }

  // --- The page ---

  function draw() {
    if (byHand && s.draft) {
      const panel = add(h("section", "change frame"), editor(spec, s.draft, {
        before: s.draft, now: s.holds?.weights ?? {}, blocked: null, applyLabel: w.useRules, backLabel: w.backToTalk,
        note: w.handNote,
        apply: async (bot) => {
          const seen = await api<{ bot: Bot; rules: string[]; holds: Preview }>("/api/bots/preview", { method: "POST", body: { bot } });
          adopt(seen.bot, seen.rules, seen.holds, "hand");
          byHand = false;
          save();
          draw();
        },
        back: () => ((byHand = false), draw()),
      }));
      root.replaceChildren(panel);
      return;
    }
    root.replaceChildren(add(h("div", "build-grid"), chatSide(), draftSide()));
  }

  draw();
  if (s.draft && !s.holds) void mapIt(); // a draft kept from before the map came back
  return root;
}
