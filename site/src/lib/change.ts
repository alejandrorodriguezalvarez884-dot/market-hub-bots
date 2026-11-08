// "Change it" on the owner's page. The easy way first: say what to change, in words or with one
// tap, and Claude proposes new rules, shown as before → after in words with what they would hold;
// one button applies them at the next close. The switches beside it (pause, leave a company out)
// are toggles and chips. Every rule by hand stays one step away (editor.ts). What waits for the
// next close is on top, with a way to cancel it; the day's change, the chat's messages left and
// any error are said where they matter. Nothing of the chat is kept: it lives as long as the page.
import { add, h } from "./dom";
import { day, timeAgo } from "./format";
import { rulesDiff, toggle } from "./controls";
import { said } from "./doings";
import { editor } from "./editor";
import { treemap } from "./mybot";
import { ApiError, api } from "./site";
import type { Bot, ChatAnswer, ChatStatus, Checked, MyBot, Spec } from "./types";
import { companies } from "./companies";
import { diff, share } from "./words";
import { lang } from "../i18n";
import { change as words } from "../i18n/change";
import { companies as companyWords } from "../i18n/companies";

export type ChangeContext = {
  you: MyBot;
  spec: Spec;
  chat: ChatStatus; // its ``left`` is kept up to date here
  reload: () => Promise<void>; // reads the bot again and draws the page
  close: () => void;
};

type Said = { role: "user"; text: string };
type Answer = {
  role: "assistant"; text: string; error?: boolean; proposal?: Bot; rules?: string[]; problems?: string[]; before?: string[];
  holds?: Checked["holds"]; state?: "applied" | "dropped";
};
const talk: (Said | Answer)[] = []; // this visit only
let thinking = false;
let flash: { text: string; undo?: () => Promise<unknown> } | null = null;
let advanced: Bot | null = null; // the rules open in the editor, when it is open
let tuning: Answer | null = null; // the proposal the editor was opened from, if it was

// --- Dates as New York has them -----------------------------------------------------------------

const NY = "America/New_York";
const nyDay = (d: Date) => d.toLocaleDateString("en-CA", { timeZone: NY });
// The session whose close a change made at ``iso`` applies at: that day before the bell, else the
// next weekday (holidays are not known here).
export function closeOf(iso: string): string {
  const at = new Date(iso);
  const hour = Number(new Intl.DateTimeFormat("en-US", { timeZone: NY, hour: "numeric", hourCycle: "h23" }).format(at));
  const d = new Date(`${nyDay(at)}T12:00:00Z`);
  if (hour >= 16) d.setUTCDate(d.getUTCDate() + 1);
  while (d.getUTCDay() === 0 || d.getUTCDay() === 6) d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

function button(cls: string, text: string, onClick: (b: HTMLButtonElement) => void): HTMLButtonElement {
  const b = h("button", cls, text);
  b.type = "button";
  b.addEventListener("click", () => onClick(b));
  return b;
}

const message = (e: unknown, fallback: string) => (e instanceof Error ? e.message : fallback);

export function changePanel(ctx: ChangeContext): HTMLElement {
  const { you, spec, chat } = ctx;
  const w = words[lang()];
  const c = companyWords[lang()];
  const root = h("section", "change frame");
  const pendingRules = !!you.pending?.what.includes("rules");
  const rulesToday = !!you.rules_changed_utc && nyDay(new Date(you.rules_changed_utc)) === nyDay(new Date());
  const blocked = !rulesToday ? null : pendingRules
    ? w.blockedPending
    : w.blockedToday;
  const current: Bot = you.pending?.bot ?? you.bot; // as it will be at the next close
  const currentRules = you.pending?.rules ?? you.rules;
  const nextClose = day(closeOf(new Date().toISOString()));
  const held: Record<string, number> = you.since ? Object.fromEntries(you.holdings.map((x) => [x.ticker, x.weight])) : you.preview?.weights ?? {};

  const cancelAll = () => api("/api/bots/mine/pending", { method: "DELETE" });
  const flip = (action: string, ticker?: string, min_weight?: number) => () =>
    api("/api/bots/mine/switch", { method: "POST", body: { action, ticker, min_weight } });

  // Does ``run``, then says ``text`` on top of the page drawn again, with ``undo`` if there is one.
  async function act(text: string, run: () => Promise<unknown>, note: HTMLElement, undo?: () => Promise<unknown>) {
    try {
      await run();
      flash = { text, undo };
      await redraw();
    } catch (e) {
      note.textContent = message(e, w.failed);
      note.classList.remove("hidden");
    }
  }

  // The page drawn again, with this panel in view.
  async function redraw() {
    await ctx.reload();
    document.querySelector(".change")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // New rules, from a proposal (``from``) or the editor. The other proposals were made for the rules
  // before: they are set aside.
  async function applyRules(bot: Bot, from: Answer | null = tuning) {
    await api("/api/bots/mine/rules", { method: "PUT", body: { bot } });
    for (const t of talk) if (t.role === "assistant" && t.proposal && !t.state) t.state = t === from ? "applied" : "dropped";
    advanced = tuning = null;
    flash = { text: you.since ? w.doneAt(nextClose) : w.doneIn };
    await redraw();
  }

  // --- On top: what is waiting, and what just happened ---

  function waiting(): HTMLElement | null {
    const p = you.pending;
    if (!p) return null;
    const note = h("p", "mt-2 hidden text-[12.5px] text-warn");
    const lines = p.what.includes("rules") ? rulesDiff(diff(you.rules, p.rules)) : null;
    return add(h("div", "pending"),
      add(h("div", "flex flex-wrap items-center gap-x-3 gap-y-2"),
        h("span", "status is-waiting", w.waitingFor(day(closeOf(p.changed_utc)))),
        add(h("span", "flex flex-wrap gap-1.5"), ...p.what.map((w) => h("span", "chip", said([w])))),
        button("btn btn-ghost ml-auto py-1 text-[13px]", w.cancelIt, (b) => {
          b.disabled = true;
          void act(w.cancelled, cancelAll, note);
        })),
      lines ? add(h("div", "mt-3"), lines) : null,
      h("p", "mt-2 text-[12px] text-faint", w.asked(timeAgo(p.changed_utc))),
      note);
  }

  function flashed(): HTMLElement | null {
    if (!flash) return null;
    const f = flash;
    flash = null;
    const box = add(h("div", "flash"), h("span", "flash-tick", "✓"), h("span", "flex-1", f.text));
    if (f.undo) {
      const note = h("p", "hidden text-[12.5px] text-warn");
      box.append(button("flash-undo", w.undo, () => void act(w.undone, f.undo!, note)), note);
    }
    return box;
  }

  // --- Ask: in words or with one tap ---

  function proposalCard(a: Answer): HTMLElement {
    const card = h("div", "proposal");
    card.append(h("p", "label", w.proposed));
    if (a.state === "dropped") return add(card, h("p", "mt-1 text-[13px] text-faint", w.setAside));
    if (a.state === "applied") return add(card, h("p", "mt-1 text-[13px] text-ink-strong", you.pending ? w.appliedWaits : w.applied));
    card.append(add(h("div", "mt-2"), rulesDiff(diff(a.before ?? currentRules, a.rules ?? []))));
    if (a.holds) {
      card.append(add(h("div", "mt-4"), treemap(a.holds.weights, null, { preview: true, small: true }),
        h("p", "mt-2 text-[12px] text-faint", w.wouldHoldAt(day(a.holds.as_of)))));
    }
    const note = h("p", "mt-2 hidden text-[12.5px] text-warn");
    add(card, add(h("div", "mt-4 flex flex-wrap items-center gap-2"),
      button("btn btn-primary", you.since ? w.applyNext : w.apply, async (b) => {
        b.disabled = true;
        b.textContent = w.applying;
        try {
          await applyRules(a.proposal!, a);
        } catch (e) {
          note.textContent = message(e, w.failed);
          note.classList.remove("hidden");
          b.disabled = false;
          b.textContent = you.since ? w.applyNext : w.apply;
        }
      }),
      button("btn btn-ghost", w.fineTune, () => {
        advanced = a.proposal!;
        tuning = a;
        draw();
        root.scrollIntoView({ behavior: "smooth", block: "start" });
      }),
      button("ml-1 text-[13px] text-muted hover:text-ink-strong", w.notThis, () => {
        a.state = "dropped";
        draw();
      })), note);
    if (blocked) (card.querySelector(".btn-primary") as HTMLButtonElement).disabled = true, card.append(h("p", "mt-2 text-[12px] text-faint", blocked));
    return card;
  }

  function conversation(): HTMLElement | null {
    if (!talk.length && !thinking) return null;
    const list = h("div", "talk");
    for (const t of talk.slice(-8)) {
      if (t.role === "user") list.append(h("p", "bubble is-me", t.text));
      else {
        list.append(add(h("div", `bubble is-them ${t.error ? "is-error" : ""}`), h("span", "bubble-who", "Claude"), h("span", "", t.text)));
        if (t.problems?.length) list.append(h("p", "text-[12.5px] text-warn", w.problems(t.problems.join(" "))));
        if (t.proposal) list.append(proposalCard(t));
      }
    }
    if (thinking) list.append(add(h("div", "bubble is-them"), h("span", "bubble-who", "Claude"), add(h("span", "dots-typing"), h("i"), h("i"), h("i"))));
    return list;
  }

  async function send(text: string) {
    const msg = text.trim();
    if (!msg || thinking) return;
    talk.push({ role: "user", text: msg });
    thinking = true;
    draw();
    const history = talk.filter((t) => !("error" in t && t.error)).slice(0, -1).map((t) => ({ role: t.role, text: t.text }));
    try {
      const got = await api<ChatAnswer>("/api/bots/mine/chat", { method: "POST", body: { message: msg, history } });
      if (typeof got.left === "number") chat.left = got.left;
      const a: Answer = { role: "assistant", text: got.reply, problems: got.problems, before: currentRules };
      if (got.proposal) Object.assign(a, { proposal: got.proposal, rules: got.rules ?? [] });
      talk.push(a);
      if (got.proposal) {
        api<Checked>("/api/bots/preview", { method: "POST", body: { bot: got.proposal } })
          .then((c) => ((a.holds = c.holds), draw()))
          .catch(() => null);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 503 && /messages today|mensajes/.test(e.message)) chat.left = 0;
      talk.push({ role: "assistant", text: message(e, w.chatFailed), error: true });
    }
    thinking = false;
    draw();
    (root.querySelector(".ask textarea") as HTMLTextAreaElement | null)?.focus();
  }

  function ask(): HTMLElement {
    const box = h("div");
    const left = chat.left ?? chat.per_member_per_day;
    const byHand = (cls: string, text: string) => button(cls, text, () => {
      advanced = current;
      tuning = null;
      draw();
    });
    // When the chat cannot take a message, the box says why and the way by hand is the button.
    const why = !chat.on ? w.chatOff
      : left <= 0 ? w.usedUp(chat.per_member_per_day)
      : blocked;
    if (why) {
      return add(box, add(h("div", "ask is-off"), add(h("div", "min-w-0 flex-1 py-1"), h("p", "text-[14px] text-ink", why),
        blocked && why === blocked ? null : h("p", "mt-1 text-[12.5px] text-muted", w.stillByHand))),
        blocked && why === blocked ? null : add(h("div", "mt-3"), byHand("btn btn-ghost", w.changeByHand)),
        conversation());
    }
    const form = h("form", "ask");
    const input = h("textarea", "ask-input");
    input.rows = 1;
    input.maxLength = 600;
    input.placeholder = w.ask;
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
      void send(input.value);
    });
    add(form, input, go);

    const tap = ([label, say]: [string, string]) => button("suggest", label, () => void send(say));
    const chips = add(h("div", "suggests"),
      tap(w.chips.defensive),
      tap(w.chips.fewer),
      tap(w.chips.more),
      current.rebalance === "monthly" ? tap(w.chips.weekly) : tap(w.chips.monthly),
      button("suggest", w.dropSector, () => {
        input.value = w.dropFill;
        grow();
        input.focus();
        const at = w.dropFill.indexOf(w.dropWord);
        input.setSelectionRange(at, at + w.dropWord.length);
      }));
    const switchNote = h("p", "mt-2 hidden text-[12.5px] text-warn");
    const paused = you.pending?.paused ?? you.paused;
    chips.append(button("suggest is-switch", paused ? w.resume : w.pause, (b) => {
      b.disabled = true;
      void act(paused ? w.runningAgain : w.pausedFrom(nextClose),
        flip(paused ? "resume" : "pause"), switchNote, flip(paused ? "pause" : "resume"));
    }));
    if (thinking) chips.querySelectorAll("button").forEach((b) => (b.disabled = true));

    const meta = add(h("div", "mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-[12.5px]"),
      h("span", "num text-faint", w.left(left, chat.per_member_per_day)),
      byHand("text-muted underline-offset-4 hover:text-ink-strong hover:underline", w.byHand));
    return add(box, form, chips, switchNote, meta, conversation());
  }

  // --- The switches ---

  function switches(): HTMLElement {
    const paused = you.pending?.paused ?? you.paused;
    const exclude = you.pending?.exclude ?? you.exclude;
    const note = h("p", "mt-2 hidden text-[12.5px] text-warn");
    const UNDO: Record<string, string> = { pause: "resume", resume: "pause", exclude: "include", include: "exclude" };
    const press = (text: string, action: string) => act(text, flip(action), note, flip(UNDO[action]));

    const run = add(h("div", "switch-card"),
      add(h("div", "flex items-center justify-between gap-3"),
        add(h("div", "min-w-0"), h("p", "text-[14px] font-medium text-ink-strong", paused ? w.paused : w.running),
          h("p", "text-[12.5px] text-muted", paused ? w.pausedHint : w.runningHint)),
        toggle(!paused, w.running, (on) => void press(on ? w.runningAgain : w.pausedFrom(nextClose), on ? "resume" : "pause"))));

    // Always and never: each press is a switch from the next close, with its undo.
    const always = you.pending?.always ?? you.always ?? [];
    const was = (t: string) => always.find((p) => p.ticker === t);
    const out = companies({
      always, never: exclude, picks: Object.keys(held),
      act: async (action, t, min) => {
        const before = was(t);
        await api("/api/bots/mine/switch", { method: "POST", body: { action, ticker: t, min_weight: min } });
        const undo = action === "pin" ? (before ? flip("pin", t, before.min_weight) : flip("unpin", t))
          : action === "unpin" ? flip("pin", t, before?.min_weight ?? 0) : flip(UNDO[action], t);
        const text = action === "pin" ? c.pinnedFrom(t, min ? share(min) : "") : action === "unpin" ? c.unpinnedFrom(t)
          : action === "exclude" ? w.isLeftOut(t) : w.comesBack(t);
        flash = { text, undo };
        await redraw();
      },
    });
    return add(h("div", "space-y-3"), h("p", "label", w.switches), run, note, out,
      h("p", "text-[12px] text-faint", w.switchesNote));
  }

  // --- The panel ---

  function draw() {
    const head = add(h("div", "change-head"),
      add(h("div", "min-w-0"), h("h2", "change-title", w.title),
        h("p", "mt-0.5 text-[12.5px] text-muted", you.since ? w.fromNext(nextClose) : w.beforeStart)),
      button("change-close", "×", ctx.close));
    head.querySelector(".change-close")!.setAttribute("aria-label", w.close);
    if (advanced) {
      root.replaceChildren(head, add(h("div", "mt-5"), editor(spec, advanced, {
        before: current, now: held, blocked, apply: applyRules,
        back: () => ((advanced = tuning = null), draw()),
      })));
      return;
    }
    root.replaceChildren(head, flashed() ?? h("span"), waiting() ?? h("span"),
      add(h("div", "mt-5 grid gap-x-8 gap-y-8 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]"), ask(), switches()));
  }

  draw();
  return root;
}
