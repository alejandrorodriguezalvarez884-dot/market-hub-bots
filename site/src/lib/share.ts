// Sharing a bot as a picture: a "Share" button that opens a dialog with the bot's card, drawn by the
// service (GET /api/board/bot/{slug}/card.png, src/botleague/card.py), so the site, the iPhone app
// and the preview a link shows are the same picture. The reader picks a story (9:16) or a square
// and a period of the board; the picture is fetched as soon as it is picked, so "Share" can hand it
// to the system's share sheet (Web Share API) within the click, as Safari requires. Where the
// browser cannot share files, "Download" saves it and "Copy link" copies the bot's page.
import { add, h } from "./dom";
import { API, botUrl } from "./site";
import { PERIODS, type Period, type Returns } from "./types";
import { lang } from "../i18n";
import { share as words } from "../i18n/share";

type Format = "story" | "square";
export type Shared = { slug: string; name: string; returns: Returns | null };

export function cardUrl(slug: string, format: Format | "link", period: Period): string {
  return `${API}/api/board/bot/${encodeURIComponent(slug)}/card.png?format=${format}&period=${period}&lang=${lang()}`;
}

export function shareButton(bot: Shared, cls = "btn btn-ghost"): HTMLButtonElement {
  const t = words[lang()];
  const b = h("button", cls);
  b.type = "button";
  b.append(shareIcon(), document.createTextNode(t.share));
  b.addEventListener("click", () => openShare(bot));
  return b;
}

function shareIcon(): SVGSVGElement {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 20 20");
  s.setAttribute("width", "15");
  s.setAttribute("height", "15");
  s.setAttribute("aria-hidden", "true");
  s.innerHTML = '<path d="M10 12.5V3M6.5 6.5L10 3l3.5 3.5M5 9.5H4v7.5h12V9.5h-1" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>';
  return s;
}

function openShare(bot: Shared): void {
  const t = words[lang()];
  const periods = PERIODS.filter((p) => bot.returns?.[p.key] != null);
  let format: Format = "story";
  let period: Period = bot.returns?.all != null ? "all" : periods[0]?.key ?? "all";
  let file: File | null = null;
  let objectUrl: string | null = null;
  let asked = 0;

  const dialog = h("dialog", "share-dialog");
  dialog.setAttribute("aria-label", t.title);
  const close = h("button", "share-close", "×");
  close.type = "button";
  close.setAttribute("aria-label", t.close);
  close.addEventListener("click", () => dialog.close());

  const tabs = (label: string, items: { key: string; label: string }[], current: () => string, pick: (k: string) => void) => {
    const nav = h("div", "tabs");
    nav.setAttribute("role", "tablist");
    nav.setAttribute("aria-label", label);
    const draw = () => {
      nav.replaceChildren(...items.map((it) => {
        const b = h("button", "tab-btn", it.label);
        b.type = "button";
        b.setAttribute("role", "tab");
        b.setAttribute("aria-selected", String(it.key === current()));
        b.addEventListener("click", () => {
          pick(it.key);
          draw();
          load();
        });
        return b;
      }));
    };
    draw();
    return nav;
  };

  const picture = h("img", "share-picture");
  picture.alt = t.alt(bot.name);
  const frame = add(h("div", "share-frame"), picture);
  const status = h("p", "share-status", t.loading);
  frame.append(status);

  const canShareFiles = typeof navigator.share === "function" && typeof navigator.canShare === "function";
  const shareIt = h("button", "btn btn-primary", t.shareIt);
  shareIt.type = "button";
  const download = h("a", "btn btn-ghost", t.download);
  const copy = h("button", "btn btn-ghost", t.copyLink);
  copy.type = "button";
  const pageUrl = new URL(botUrl(bot.slug), location.origin).href;

  shareIt.addEventListener("click", async () => {
    if (!file) return;
    try {
      await navigator.share({ files: [file], title: bot.name, text: `${t.text(bot.name)} ${pageUrl}` });
    } catch {
      // Closed by the reader, or refused by the browser: nothing to say.
    }
  });
  copy.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(pageUrl);
      copy.textContent = t.copied;
      setTimeout(() => (copy.textContent = t.copyLink), 1800);
    } catch {
      prompt(t.copyLink, pageUrl);
    }
  });

  async function load() {
    const mine = ++asked;
    file = null;
    shareIt.disabled = true;
    download.removeAttribute("href");
    download.setAttribute("aria-disabled", "true");
    status.textContent = t.loading;
    status.hidden = false;
    frame.dataset.format = format;
    picture.classList.add("is-loading");
    try {
      const res = await fetch(cardUrl(bot.slug, format, period), { credentials: "include" });
      if (!res.ok) throw new Error(String(res.status));
      const blob = await res.blob();
      if (mine !== asked) return;
      const name = `bot-league-${bot.slug}-${format}.png`;
      file = new File([blob], name, { type: "image/png" });
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(blob);
      picture.src = objectUrl;
      picture.classList.remove("is-loading");
      status.hidden = true;
      download.href = objectUrl;
      download.download = name;
      download.removeAttribute("aria-disabled");
      shareIt.hidden = !(canShareFiles && navigator.canShare({ files: [file] }));
      shareIt.disabled = false;
    } catch {
      if (mine !== asked) return;
      status.textContent = t.failed;
    }
  }

  const formats = tabs(t.format, [{ key: "story", label: t.story }, { key: "square", label: t.square }], () => format, (k) => (format = k as Format));
  const when = periods.length > 1 ? tabs(t.period, periods.map((p) => ({ key: p.key, label: p.label })), () => period, (k) => (period = k as Period)) : null;

  add(dialog,
    add(h("div", "flex items-start justify-between gap-4"), h("h2", "text-[17px] font-semibold text-ink-strong", t.title), close),
    add(h("div", "mt-3 flex flex-wrap items-center gap-x-6 gap-y-2"), formats, when),
    frame,
    add(h("div", "mt-4 flex flex-wrap gap-2"), shareIt, download, copy),
    h("p", "mt-3 text-[12.5px] text-muted", t.note));
  dialog.addEventListener("close", () => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    dialog.remove();
  });
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close(); // a click on the backdrop
  });
  document.body.append(dialog);
  dialog.showModal();
  load();
}
