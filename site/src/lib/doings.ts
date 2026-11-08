// The changes of a bot, as the service names them, in the page's language.
import { lang } from "../i18n";
import { common } from "../i18n/common";

const w = () => common[lang()];

// The changes the service names ("rules", "paused", "resumed", "excluded NVDA", "included NVDA",
// "pinned NVDA", "unpinned NVDA", "renamed from Old name"), in the page's language. Anything else is shown as it comes.
function sayOne(what: string): string {
  const t = w().said;
  if (what === "rules" || what === "paused" || what === "resumed") return t[what];
  const m = /^(excluded|included|pinned|unpinned|renamed from) (.+)$/.exec(what);
  if (!m) return what;
  return m[1] === "renamed from" ? t.renamed(m[2]) : t[m[1] as "excluded" | "included" | "pinned" | "unpinned"](m[2]);
}
export const said = (what: string[]) => what.map(sayOne).join(" · ");
