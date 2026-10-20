// Draws the picture a shared link to Bot League shows (Open Graph and Twitter Card, 1200 x 630):
// the mark and the name, who it is by, what it is, and its address. The mark is the one of
// site/src/components/Mark.astro and site/public/favicon.svg.
//
// It drives the Chrome installed on this machine (FILM_BROWSER=msedge for Edge), as the portal's
// own share.mjs does, and writes site/public/share.png.

import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, "..", "site", "public", "share.png");

const card = `<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400&family=IBM+Plex+Sans:wght@400;600&display=block" rel="stylesheet">
<style>
  html, body { margin: 0; width: 1200px; height: 630px; background: #0b0c0d; color: #f2f0ea; }
  body { display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: "IBM Plex Sans", sans-serif; }
  .brand { display: flex; align-items: center; gap: 34px; }
  .brand svg { width: 140px; height: 140px; }
  .name { font-size: 104px; font-weight: 600; letter-spacing: -0.025em; line-height: 1; }
  .by { margin-top: 26px; font-size: 30px; color: #8c8b86; }
  .what { margin-top: 40px; font-size: 38px; color: #c9c7c1; }
  .where { margin-top: 26px; font-family: "IBM Plex Mono", monospace; font-size: 26px; color: #8c8b86; }
</style></head><body>
  <div class="brand">
    <svg viewBox="0 0 20 20" fill="none" stroke="#f2f0ea" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 2v16M3.5 2h4l3 3v1.5L7 10M7.5 10l4 4v.5L8 18H3.5M3.5 10h10"/><circle cx="16.25" cy="10" r="2.5" fill="#f2f0ea" stroke="none"/></svg>
    <span class="name">Bot League</span>
  </div>
  <p class="by">by The Market Hub</p>
  <p class="what">Your AI agent builds the bot. The market keeps score.</p>
  <p class="where">bots.themarkethub.app</p>
</body></html>`;

const browser = await chromium.launch({ channel: process.env.FILM_BROWSER ?? "chrome", headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  await page.setContent(card, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: out, type: "png" });
  console.log(out);
} finally {
  await browser.close();
}
