// The changes of a bot, as the service names them, in the page's language.
import { lang } from "../i18n";
import { common } from "../i18n/common";

const w = () => common[lang()];

// The changes the service names ("rules", "paused", "resumed", "excluded NVDA", "included NVDA",
// "renamed from Old name"), in the page's language. Anything else is shown as it comes.
function sayOne(what: string): string {
  const t = w().said;
  if (what === "rules" || what === "paused" || what === "resumed") return t[what];
  const m = /^(excluded|included|renamed from) (.+)$/.exec(what);
  if (!m) return what;
  return m[1] === "excluded" ? t.excluded(m[2]) : m[1] === "included" ? t.included(m[2]) : t.renamed(m[2]);
}
export const said = (what: string[]) => what.map(sayOne).join(" · ");
