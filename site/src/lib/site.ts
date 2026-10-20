// Site-wide constants, links and the call to the API.
export const SITE_NAME = "Bot League";

// Market Hub, the portal: where members sign in, and what Bot League is part of.
export const HUB_URL = (import.meta.env.PUBLIC_HUB_URL ?? "https://themarkethub.app").replace(/\/$/, "");
export const hubQuoteUrl = (ticker: string) => `${HUB_URL}/quote/?t=${encodeURIComponent(ticker)}`;

// Every internal link goes through here, so the site works under a sub-path too.
export function link(path: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return `${base}${path}`;
}
export const botUrl = (slug: string) => `${link("/bot/")}?b=${encodeURIComponent(slug)}`;

// The API lives on the same origin in production; in development it is another port.
export const API = (import.meta.env.PUBLIC_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly signin: string | null) {
    super(message);
  }
}

// GET or send JSON to the API. A failed answer throws its own words, and where to sign in when
// the answer is that one has to.
export async function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: init?.method ?? "GET",
    credentials: "include",
    headers: init?.body !== undefined ? { "content-type": "application/json" } : undefined,
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) {
    let detail = "Something went wrong. Try again in a minute.";
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
