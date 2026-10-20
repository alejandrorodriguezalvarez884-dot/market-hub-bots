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
import { diff } from "./words";

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
let leaving = false; // the "leave one out" chooser is open

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
  const root = h("section", "change frame");
  const pendingRules = !!you.pending?.what.includes("rules");
  const rulesToday = !!you.rules_changed_utc && nyDay(new Date(you.rules_changed_utc)) === nyDay(new Date());
  const blocked = !rulesToday ? null : pendingRules
    ? "Today's change of rules is waiting for the close. Cancel it to make another."
    : "Its rules changed today. They can change again tomorrow; the switches still work.";
  const current: Bot = you.pending?.bot ?? you.bot; // as it will be at the next close
  const currentRules = you.pending?.rules ?? you.rules;
  const nextClose = day(closeOf(new Date().toISOString()));
  const held: Record<string, number> = you.since ? Object.fromEntries(you.holdings.map((x) => [x.ticker, x.weight])) : you.preview?.weights ?? {};

  const cancelAll = () => api("/api/bots/mine/pending", { method: "DELETE" });
  const flip = (action: string, ticker?: string) => () => api("/api/bots/mine/switch", { method: "POST", body: { action, ticker } });

  // Does ``run``, then says ``text`` on top of the page drawn again, with ``undo`` if there is one.
  async function act(text: string, run: () => Promise<unknown>, note: HTMLElement, undo?: () => Promise<unknown>) {
    try {
      await run();
      flash = { text, undo };
      await redraw();
    } catch (e) {
      note.textContent = message(e, "That did not work.");
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
    flash = { text: you.since ? `Done. The new rules apply at the close of ${nextClose}.` : "Done. Its new rules are in." };
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
        h("span", "status is-waiting", `Waiting for the close of ${day(closeOf(p.changed_utc))}`),
        add(h("span", "flex flex-wrap gap-1.5"), ...p.what.map((w) => h("span", "chip", said([w])))),
        button("btn btn-ghost ml-auto py-1 text-[13px]", "Cancel it", (b) => {
          b.disabled = true;
          void act("Cancelled. Your bot goes on as it is.", cancelAll, note);
        })),
      lines ? add(h("div", "mt-3"), lines) : null,
      h("p", "mt-2 text-[12px] text-faint", `Asked ${timeAgo(p.changed_utc)}. Until that close the bot goes on as it is; its record goes on after.`),
      note);
  }

  function flashed(): HTMLElement | null {
    if (!flash) return null;
    const f = flash;
    flash = null;
    const box = add(h("div", "flash"), h("span", "flash-tick", "✓"), h("span", "flex-1", f.text));
    if (f.undo) {
      const note = h("p", "hidden text-[12.5px] text-warn");
      box.append(button("flash-undo", "Undo", () => void act("Undone.", f.undo!, note)), note);
    }
    return box;
  }

  // --- Ask: in words or with one tap ---

  function proposalCard(a: Answer): HTMLElement {
    const card = h("div", "proposal");
    card.append(h("p", "label", "Proposed change"));
    if (a.state === "dropped") return add(card, h("p", "mt-1 text-[13px] text-faint", "Set aside."));
    if (a.state === "applied") return add(card, h("p", "mt-1 text-[13px] text-ink-strong", you.pending ? "✓ Applied: it waits for the next close, above." : "✓ Applied."));
    card.append(add(h("div", "mt-2"), rulesDiff(diff(a.before ?? currentRules, a.rules ?? []))));
    if (a.holds) {
      card.append(add(h("div", "mt-4"), treemap(a.holds.weights, null, { preview: true, small: true }),
        h("p", "mt-2 text-[12px] text-faint", `What it would hold at the close of ${day(a.holds.as_of)}.`)));
    }
    const note = h("p", "mt-2 hidden text-[12.5px] text-warn");
    add(card, add(h("div", "mt-4 flex flex-wrap items-center gap-2"),
      button("btn btn-primary", you.since ? "Apply at the next close" : "Apply", async (b) => {
        b.disabled = true;
        b.textContent = "Applying…";
        try {
          await applyRules(a.proposal!, a);
        } catch (e) {
          note.textContent = message(e, "That did not work.");
          note.classList.remove("hidden");
          b.disabled = false;
          b.textContent = you.since ? "Apply at the next close" : "Apply";
        }
      }),
      button("btn btn-ghost", "Fine-tune by hand", () => {
        advanced = a.proposal!;
        tuning = a;
        draw();
        root.scrollIntoView({ behavior: "smooth", block: "start" });
      }),
      button("ml-1 text-[13px] text-muted hover:text-ink-strong", "Not this", () => {
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
        if (t.problems?.length) list.append(h("p", "text-[12.5px] text-warn", `Its proposal did not pass the checks: ${t.problems.join(" ")}`));
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
      if (e instanceof ApiError && e.status === 503 && /messages today/.test(e.message)) chat.left = 0;
      talk.push({ role: "assistant", text: message(e, "The chat could not answer."), error: true });
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
    const why = !chat.on ? "The chat is off on this copy of the site."
      : left <= 0 ? `That is the ${chat.per_member_per_day} messages of today: the chat is back tomorrow.`
      : blocked;
    if (why) {
      return add(box, add(h("div", "ask is-off"), add(h("div", "min-w-0 flex-1 py-1"), h("p", "text-[14px] text-ink", why),
        blocked && why === blocked ? null : h("p", "mt-1 text-[12.5px] text-muted", "Every rule can still be changed by hand."))),
        blocked && why === blocked ? null : add(h("div", "mt-3"), byHand("btn btn-ghost", "Change every rule by hand")),
        conversation());
    }
    const form = h("form", "ask");
    const input = h("textarea", "ask-input");
    input.rows = 1;
    input.maxLength = 600;
    input.placeholder = "Tell it what to change…";
    input.setAttribute("aria-label", "What to change");
    input.disabled = thinking;
    const go = h("button", "ask-send");
    go.type = "submit";
    go.disabled = thinking;
    go.setAttribute("aria-label", "Send");
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

    const tap = (label: string, say: string) => button("suggest", label, () => void send(say));
    const chips = add(h("div", "suggests"),
      tap("More defensive", "Make it more defensive"),
      tap("Fewer stocks", "Hold fewer stocks"),
      tap("More stocks", "Hold more stocks"),
      current.rebalance === "monthly" ? tap("Look again weekly", "Look again weekly") : tap("Look again monthly", "Look again monthly"),
      button("suggest", "Drop a sector", () => {
        input.value = "Leave out the tech stocks";
        grow();
        input.focus();
        input.setSelectionRange(14, 18);
      }));
    const switchNote = h("p", "mt-2 hidden text-[12.5px] text-warn");
    const paused = you.pending?.paused ?? you.paused;
    chips.append(button("suggest is-switch", paused ? "Resume" : "Pause", (b) => {
      b.disabled = true;
      void act(paused ? "Running again from the next close." : `Paused: it holds cash from the close of ${nextClose}.`,
        flip(paused ? "resume" : "pause"), switchNote, flip(paused ? "pause" : "resume"));
    }));
    if (thinking) chips.querySelectorAll("button").forEach((b) => (b.disabled = true));

    const meta = add(h("div", "mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-[12.5px]"),
      h("span", "num text-faint", `${left} of ${chat.per_member_per_day} messages left today`),
      byHand("text-muted underline-offset-4 hover:text-ink-strong hover:underline", "Every rule, by hand ›"));
    return add(box, form, chips, switchNote, meta, conversation());
  }

  // --- The switches ---

  function switches(): HTMLElement {
    const paused = you.pending?.paused ?? you.paused;
    const exclude = you.pending?.exclude ?? you.exclude;
    const note = h("p", "mt-2 hidden text-[12.5px] text-warn");
    const UNDO: Record<string, string> = { pause: "resume", resume: "pause", exclude: "include", include: "exclude" };
    const press = (text: string, action: string, ticker?: string) => {
      if (action === "exclude") leaving = false;
      return act(text, flip(action, ticker), note, flip(UNDO[action], ticker?.toUpperCase()));
    };

    const run = add(h("div", "switch-card"),
      add(h("div", "flex items-center justify-between gap-3"),
        add(h("div", "min-w-0"), h("p", "text-[14px] font-medium text-ink-strong", paused ? "Paused" : "Running"),
          h("p", "text-[12.5px] text-muted", paused ? "In cash from the next close, until it runs again." : "Pause it to hold cash from the next close.")),
        toggle(!paused, "Running", (on) => void press(on ? "Running again from the next close." : `Paused: it holds cash from the close of ${nextClose}.`, on ? "resume" : "pause"))));

    const out = add(h("div", "switch-card"),
      h("p", "text-[14px] font-medium text-ink-strong", "Left out"),
      h("p", "text-[12.5px] text-muted", exclude.length ? "Never chosen until you let it back in." : "A company left out is sold at the next close and never chosen again."));
    const chips = h("div", "mt-3 flex flex-wrap gap-1.5");
    for (const t of exclude) {
      chips.append(add(h("span", "chip-x num"), t, button("chip-x-btn", "×", () => void press(`${t} comes back from the next close.`, "include", t))));
      (chips.lastElementChild!.querySelector("button") as HTMLButtonElement).setAttribute("aria-label", `Let ${t} back in`);
    }
    chips.append(button("chip-add", leaving ? "Done" : "+ Leave one out", () => ((leaving = !leaving), draw())));
    out.append(chips);
    if (leaving) {
      const pick = h("div", "mt-3 flex flex-wrap gap-1.5");
      const choices = Object.keys(held).filter((t) => !exclude.includes(t)).slice(0, 12);
      for (const t of choices) pick.append(button("chip-pick num", t, () => void press(`${t} is left out from the next close.`, "exclude", t)));
      const other = h("input", "field num w-28 py-1 text-[13px] uppercase");
      other.placeholder = "Ticker";
      other.setAttribute("aria-label", "Another ticker");
      other.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && other.value.trim()) void press(`${other.value.trim().toUpperCase()} is left out from the next close.`, "exclude", other.value.trim());
      });
      add(out, choices.length ? h("p", "mt-3 text-[12px] text-faint", "Tap one it holds, or write another:") : null, pick,
        add(h("div", "mt-2 flex items-center gap-2"), other, button("btn btn-ghost py-1 text-[13px]", "Leave out", () => {
          if (other.value.trim()) void press(`${other.value.trim().toUpperCase()} is left out from the next close.`, "exclude", other.value.trim());
        })));
    }
    out.append(note);
    return add(h("div", "space-y-3"), h("p", "label", "Switches"), run, out,
      h("p", "text-[12px] text-faint", "Switches apply at the next close and are not the day's change. There are no orders: the bot only follows its rules."));
  }

  // --- The panel ---

  function draw() {
    const head = add(h("div", "change-head"),
      add(h("div", "min-w-0"), h("h2", "change-title", "Change your bot"),
        h("p", "mt-0.5 text-[12.5px] text-muted", you.since ? `From the next close (${nextClose}) · once a day · its record goes on` : "Before it starts, a change just becomes the bot")),
      button("change-close", "×", ctx.close));
    head.querySelector(".change-close")!.setAttribute("aria-label", "Close");
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
