// Site-wide constants, links and the call to the API.
import { inLang, lang, type Lang } from "../i18n";

export const SITE_NAME = "Bot League";

// Market Hub, the portal: where members sign in, and what Bot League is part of.
export const HUB_URL = (import.meta.env.PUBLIC_HUB_URL ?? "https://themarkethub.app").replace(/\/$/, "");
// A page of the portal, in the reader's language (the portal has the same /es/ pages).
export const hub = (path = "/", l: Lang = lang()) => `${HUB_URL}${inLang(path, l)}`;
export const hubQuoteUrl = (ticker: string, l: Lang = lang()) => `${hub("/quote/", l)}?t=${encodeURIComponent(ticker)}`;

// Every internal link goes through here, so the site works under a sub-path too, and stays in the
// page's language. A page being built passes its language; in the browser it is the page's own.
export function link(path: string, l: Lang = lang()): string {
  return `${base()}${path.startsWith("/") ? inLang(path, l) : path}`;
}
// A file of the site (an icon, a picture): the same in every language.
export const asset = (path: string) => `${base()}${path}`;
const base = () => import.meta.env.BASE_URL.replace(/\/$/, "");
export const botUrl = (slug: string, l: Lang = lang()) => `${link("/bot/", l)}?b=${encodeURIComponent(slug)}`;

// The API lives on the same origin in production; in development it is another port.
export const API = (import.meta.env.PUBLIC_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly signin: string | null) {
    super(message);
  }
}

// The headers every call carries: the page's language, so what the service writes in words (the
// rules, the errors, Claude's replies) comes back in it. A header of our own, not Accept-Language:
// that one is sent by every browser and phone on its own, and only a page in Spanish asks for Spanish.
export const apiHeaders = (json = false): Record<string, string> => ({
  "x-mh-lang": lang(),
  ...(json ? { "content-type": "application/json" } : {}),
});

// GET or send JSON to the API. A failed answer throws its own words, and where to sign in when
// the answer is that one has to.
export async function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: init?.method ?? "GET",
    credentials: "include",
    headers: apiHeaders(init?.body !== undefined),
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) {
    let detail = lang() === "es" ? "Algo ha fallado. Inténtalo de nuevo en un minuto." : "Something went wrong. Try again in a minute.";
    let signin: string | null = null;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      if (typeof body?.signin === "string") signin = body.signin;
    } catch {}
    throw new ApiError(detail, res.status, signin);
  }
  return res.json() as Promise<T>;
}

// A local run (no Market Hub sign-in) is one local member; ?visitor=1 sees the site signed out,
// until ?visitor=0. The service only reads this cookie when it runs without Market Hub.
export function localVisitor(): void {
  const v = new URLSearchParams(location.search).get("visitor");
  if (v === "1") document.cookie = "bl_visitor=1; path=/; SameSite=Lax";
  if (v === "0") document.cookie = "bl_visitor=; path=/; max-age=0";
}
