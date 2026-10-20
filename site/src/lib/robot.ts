// Every bot's face: a small robot drawn from its slug, so the same bot looks the same on every page
// and on every visit. Head, eyes, mouth, antenna, ears, chest and an accessory or two are picked by
// a seeded random number from the slug. Drawn in the site's ink only: grey shells, warm-white lines,
// no colour (green and red are the market's).
//
// robotSvg() returns markup built only from numbers and the constants below; the slug is hashed,
// never written into it. robot() wraps it in an element for the client-side pages.

const LINE = "var(--color-ink-strong)";
const DARK = "var(--color-deep)";
const PANEL = "var(--color-panel)";
// The shells, from near-black to the ink itself. The light one draws its face in the page's black.
const SHELLS = ["var(--color-raised)", "#24272a", "#2f3236", "var(--color-line-strong)", "var(--color-ink)"];
const LIGHT_SHELL = SHELLS.length - 1;

// FNV-1a, then mulberry32: a small, stable stream of numbers from a string.
function seeded(text: string): () => number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  let a = h >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const HEADS = ["box", "wide", "round", "tall", "dome", "tv", "octagon", "egg"] as const;
const EYES = ["dots", "googly", "visor", "cyclops", "happy", "square", "mismatch", "sleepy", "dashes", "plus"] as const;
const MOUTHS = ["smile", "grille", "flat", "o", "zigzag", "smirk", "blep", "grin"] as const;
const ANTENNAS = ["none", "ball", "double", "spring", "bent", "bulb", "propeller", "dish"] as const;
const EARS = ["none", "bolts", "round", "cones"] as const;
const CHESTS = ["none", "dial", "lights", "heart", "slot"] as const;
const EXTRAS = ["bowtie", "monocle", "mustache", "headphones", "hat", "brows", "cheeks", "screw", "patch"] as const;

export type Traits = {
  head: (typeof HEADS)[number]; shell: number; eyes: (typeof EYES)[number]; look: [number, number];
  mouth: (typeof MOUTHS)[number]; antenna: (typeof ANTENNAS)[number]; ears: (typeof EARS)[number];
  chest: (typeof CHESTS)[number]; extras: (typeof EXTRAS)[number][]; tilt: number;
};

export function traits(slug: string): Traits {
  const r = seeded(`bot:${slug}`);
  const pick = <T>(xs: readonly T[]): T => xs[Math.floor(r() * xs.length)];
  const head = pick(HEADS);
  const shell = Math.floor(r() * SHELLS.length);
  const eyes = pick(EYES);
  const look: [number, number] = [Math.round((r() * 2 - 1) * 1.6 * 10) / 10, Math.round((r() * 2 - 1) * 1.2 * 10) / 10];
  const mouth = pick(MOUTHS);
  let antenna = pick(ANTENNAS);
  let ears = pick(EARS);
  const chest = pick(CHESTS);
  // None, one or two extras, each only where it fits the rest of the face.
  const want = r() < 0.25 ? 0 : r() < 0.7 ? 1 : 2;
  const extras: Traits["extras"] = [];
  for (let tries = 0; extras.length < want && tries < 12; tries++) {
    const x = pick(EXTRAS);
    if (extras.includes(x)) continue;
    if ((x === "monocle" || x === "patch" || x === "brows") && ["visor", "cyclops", "mismatch"].includes(eyes)) continue;
    if (x === "monocle" && extras.includes("patch")) continue;
    if (x === "patch" && extras.includes("monocle")) continue;
    if (x === "mustache" && ["grille", "grin"].includes(mouth)) continue;
    if (x === "hat" && (extras.includes("headphones") || head === "dome")) continue;
    if (x === "headphones" && extras.includes("hat")) continue;
    extras.push(x);
  }
  if (extras.includes("hat")) antenna = "none";
  if (extras.includes("headphones")) ears = "none";
  const tilt = r() < 0.45 ? Math.round((r() * 2 - 1) * 7) : 0;
  return { head, shell, eyes, look, mouth, antenna, ears, chest, extras, tilt };
}

// The head's outline and the box the face sits in.
type Box = { d: string; top: number; bottom: number; left: number; right: number };
const HEAD: Record<Traits["head"], Box> = {
  box: { d: "M20 16H44Q51 16 51 23V39Q51 46 44 46H20Q13 46 13 39V23Q13 16 20 16Z", top: 16, bottom: 46, left: 13, right: 51 },
  wide: { d: "M18 19H46Q55 19 55 28V36Q55 45 46 45H18Q9 45 9 36V28Q9 19 18 19Z", top: 19, bottom: 45, left: 9, right: 55 },
  round: { d: "M32 14A17 17 0 1 1 31.99 14Z", top: 14, bottom: 48, left: 15, right: 49 },
  tall: { d: "M29 12H35Q47 12 47 24V36Q47 48 35 48H29Q17 48 17 36V24Q17 12 29 12Z", top: 12, bottom: 48, left: 17, right: 47 },
  dome: { d: "M12 44V31A20 20 0 0 1 52 31V44Q52 47 49 47H15Q12 47 12 44Z", top: 11, bottom: 47, left: 12, right: 52 },
  tv: { d: "M15 16H49Q53 16 52.6 20L50 43.5Q49.6 47 46 47H18Q14.4 47 14 43.5L11.4 20Q11 16 15 16Z", top: 16, bottom: 47, left: 12, right: 52 },
  octagon: { d: "M23 14H41L51 24V38L41 48H23L13 38V24Z", top: 14, bottom: 48, left: 13, right: 51 },
  egg: { d: "M32 15C43 15 51 22 51 31.5S43 47 32 47S13 41 13 31.5S21 15 32 15Z", top: 15, bottom: 47, left: 13, right: 51 },
};

type A = Record<string, string | number>;
const tag = (name: string, a: A, inner = "") =>
  `<${name}${Object.entries(a).map(([k, v]) => ` ${k}="${typeof v === "number" ? +v.toFixed(2) : v}"`).join("")}${inner ? `>${inner}</${name}>` : "/>"}`;
const stroke = (color: string, width = 2.2): A => ({ fill: "none", stroke: color, "stroke-width": width, "stroke-linecap": "round", "stroke-linejoin": "round" });

export function robotSvg(slug: string, size = 40, opts: { frame?: boolean; label?: string } = {}): string {
  const t = traits(slug);
  const box = HEAD[t.head];
  const shell = SHELLS[t.shell];
  const light = t.shell === LIGHT_SHELL;
  const fg = light ? "var(--color-page)" : LINE; // the face's features
  const h = box.bottom - box.top;
  const cx = 32;
  const ey = box.top + h * 0.42;
  const my = box.top + h * 0.74;
  const ex = Math.min(9.5, (box.right - box.left) * 0.21);
  const parts: string[] = [];
  const put = (s: string) => parts.push(s);

  // Behind the head: the body, the neck, the ears.
  const chest: string[] = [];
  chest.push(tag("path", { d: "M12 66V58Q12 52 19 52H45Q52 52 52 58V66Z", ...stroke(LINE), fill: PANEL }));
  if (t.chest === "dial") chest.push(tag("circle", { cx, cy: 59, r: 3, ...stroke(LINE, 1.6) }), tag("path", { d: "M32 59L33.8 57.2", ...stroke(LINE, 1.6) }));
  if (t.chest === "lights") for (const dx of [-5, 0, 5]) chest.push(tag("circle", { cx: cx + dx, cy: 59, r: 1.3, fill: dx === 0 ? LINE : "var(--color-muted)" }));
  if (t.chest === "heart") chest.push(tag("path", { d: "M32 62.2L28.9 59.2A1.9 1.9 0 0 1 32 56.9A1.9 1.9 0 0 1 35.1 59.2Z", fill: LINE }));
  if (t.chest === "slot") chest.push(tag("path", { d: "M27 59H37", ...stroke(LINE, 1.8) }));
  put(`<g>${chest.join("")}</g>`);
  put(tag("rect", { x: 27.5, y: box.bottom - 2, width: 9, height: 56 - box.bottom, ...stroke(LINE, 2), fill: "#2a2d30" }));

  const head: string[] = [];
  const earY = ey + 2;
  if (t.ears === "bolts") for (const s of [-1, 1]) head.push(tag("rect", { x: s < 0 ? box.left - 4.5 : box.right - 0.5, y: earY - 4, width: 5, height: 8, rx: 1.5, fill: PANEL, stroke: LINE, "stroke-width": 2 }));
  if (t.ears === "round") for (const s of [-1, 1]) head.push(tag("circle", { cx: s < 0 ? box.left - 0.5 : box.right + 0.5, cy: earY, r: 4, fill: PANEL, stroke: LINE, "stroke-width": 2 }));
  if (t.ears === "cones") for (const s of [-1, 1]) {
    const x0 = s < 0 ? box.left + 1 : box.right - 1;
    head.push(tag("path", { d: `M${x0} ${earY - 4}L${x0 + s * 6} ${earY - 7}V${earY + 7}L${x0} ${earY + 4}Z`, fill: PANEL, stroke: LINE, "stroke-width": 2, "stroke-linejoin": "round" }));
  }

  // Above it: the antenna.
  const top = box.top;
  const ball = (x: number, y: number, r = 2.6) => tag("circle", { cx: x, cy: y, r, fill: LINE });
  if (t.antenna === "ball") head.push(tag("path", { d: `M32 ${top}V${top - 7}`, ...stroke(LINE) }), ball(32, top - 8.5));
  if (t.antenna === "double") for (const s of [-1, 1]) head.push(tag("path", { d: `M${32 + s * 6} ${top + 1}L${32 + s * 10} ${top - 7}`, ...stroke(LINE) }), ball(32 + s * 10.6, top - 8.4, 2.2));
  if (t.antenna === "spring") head.push(tag("path", { d: `M32 ${top}L29.5 ${top - 2}L34.5 ${top - 4}L29.5 ${top - 6}L34.5 ${top - 8}L32 ${top - 9.5}`, ...stroke(LINE, 1.8) }), ball(32, top - 11, 2.4));
  if (t.antenna === "bent") head.push(tag("path", { d: `M30 ${top}V${top - 6}L36 ${top - 9}`, ...stroke(LINE) }), ball(37.5, top - 9.8, 2.3));
  if (t.antenna === "bulb") {
    head.push(tag("path", { d: `M32 ${top}V${top - 4}`, ...stroke(LINE) }), tag("circle", { cx: 32, cy: top - 8, r: 4, ...stroke(LINE, 2), fill: PANEL }));
    head.push(tag("path", { d: `M26 ${top - 12}L24.5 ${top - 13.5}M38 ${top - 12}L39.5 ${top - 13.5}M32 ${top - 14.5}V${top - 16}`, ...stroke(LINE, 1.5) }));
  }
  if (t.antenna === "propeller") head.push(tag("path", { d: `M32 ${top}V${top - 6}`, ...stroke(LINE) }), tag("path", { d: `M23 ${top - 7.5}Q27.5 ${top - 10.5} 32 ${top - 7}Q36.5 ${top - 3.5} 41 ${top - 6.5}`, ...stroke(LINE, 2.4) }));
  if (t.antenna === "dish") head.push(tag("path", { d: `M33 ${top}L35 ${top - 6}`, ...stroke(LINE) }), tag("path", { d: `M29 ${top - 9}Q34 ${top - 3} 41 ${top - 8}`, ...stroke(LINE, 2.2) }), ball(35.6, top - 7.4, 1.4));

  // The shell.
  head.push(tag("path", { d: box.d, fill: shell, stroke: LINE, "stroke-width": 2.4, "stroke-linejoin": "round" }));
  // A highlight on the shell, as a drawn line.
  if (t.head !== "octagon") head.push(tag("path", { d: `M${box.left + 5} ${box.top + 9}Q${box.left + 5.5} ${box.top + 5} ${box.left + 10} ${box.top + 4.5}`, ...stroke(light ? "rgb(255 255 255 / 0.55)" : "rgb(242 240 234 / 0.28)", 1.6) }));

  // The eyes.
  const lx = cx - ex, rx = cx + ex;
  const sclera = "var(--color-ink-strong)";
  const pupil = "var(--color-page)";
  const [dx, dy] = t.look;
  const googly = (x: number, r: number) => [
    tag("circle", { cx: x, cy: ey, r, fill: sclera, stroke: light ? pupil : "none", "stroke-width": 1.4 }),
    tag("circle", { cx: x + dx * (r / 5), cy: ey + dy * (r / 5), r: r * 0.45, fill: pupil }),
  ].join("");
  const face: string[] = [];
  if (t.eyes === "dots") face.push(tag("circle", { cx: lx, cy: ey, r: 2.7, fill: fg }), tag("circle", { cx: rx, cy: ey, r: 2.7, fill: fg }));
  if (t.eyes === "googly") face.push(googly(lx, 4.6), googly(rx, 4.6));
  if (t.eyes === "visor") {
    face.push(tag("rect", { x: lx - 5.5, y: ey - 4, width: rx - lx + 11, height: 8, rx: 4, fill: DARK, stroke: LINE, "stroke-width": 1.6 }));
    face.push(tag("rect", { x: cx - 6 + dx * 2.5, y: ey - 1.3, width: 12, height: 2.6, rx: 1.3, fill: LINE }));
  }
  if (t.eyes === "cyclops") face.push(googly(cx, 6.6));
  if (t.eyes === "happy") for (const x of [lx, rx]) face.push(tag("path", { d: `M${x - 3.6} ${ey + 1.6}Q${x} ${ey - 4} ${x + 3.6} ${ey + 1.6}`, ...stroke(fg, 2.4) }));
  if (t.eyes === "square") for (const x of [lx, rx]) face.push(tag("rect", { x: x - 2.8, y: ey - 2.8, width: 5.6, height: 5.6, rx: 1, fill: fg }));
  if (t.eyes === "mismatch") face.push(googly(lx, 5.2), tag("circle", { cx: rx, cy: ey, r: 2.3, fill: fg }));
  if (t.eyes === "sleepy") for (const x of [lx, rx]) {
    face.push(tag("path", { d: `M${x - 4} ${ey}A4 4 0 0 0 ${x + 4} ${ey}Z`, fill: sclera, stroke: light ? pupil : "none", "stroke-width": 1.2 }));
    face.push(tag("circle", { cx: x + dx * 0.5, cy: ey + 1.8, r: 1.5, fill: pupil }), tag("path", { d: `M${x - 4.6} ${ey}H${x + 4.6}`, ...stroke(fg, 2) }));
  }
  if (t.eyes === "dashes") for (const x of [lx, rx]) face.push(tag("path", { d: `M${x - 3.4} ${ey}H${x + 3.4}`, ...stroke(fg, 2.6) }));
  if (t.eyes === "plus") for (const x of [lx, rx]) face.push(tag("path", { d: `M${x - 3} ${ey}H${x + 3}M${x} ${ey - 3}V${ey + 3}`, ...stroke(fg, 2.2) }));

  // The mouth.
  const mw = Math.min(7, ex * 0.8);
  if (t.mouth === "smile") face.push(tag("path", { d: `M${cx - mw} ${my - 1.5}Q${cx} ${my + 4} ${cx + mw} ${my - 1.5}`, ...stroke(fg, 2.2) }));
  if (t.mouth === "grille") {
    face.push(tag("rect", { x: cx - mw - 1, y: my - 3, width: 2 * mw + 2, height: 6, rx: 1.6, fill: DARK, stroke: fg, "stroke-width": 1.6 }));
    face.push(tag("path", { d: [-1, 0, 1].map((k) => `M${cx + k * (mw / 1.9)} ${my - 2.4}V${my + 2.4}`).join(""), ...stroke(LINE, 1.2) }));
  }
  if (t.mouth === "flat") face.push(tag("path", { d: `M${cx - mw * 0.75} ${my}H${cx + mw * 0.75}`, ...stroke(fg, 2.2) }));
  if (t.mouth === "o") face.push(tag("ellipse", { cx, cy: my, rx: 2.4, ry: 2.9, ...stroke(fg, 2) }));
  if (t.mouth === "zigzag") face.push(tag("path", { d: `M${cx - mw} ${my}L${cx - mw / 2} ${my - 2}L${cx} ${my}L${cx + mw / 2} ${my - 2}L${cx + mw} ${my}`, ...stroke(fg, 1.9) }));
  if (t.mouth === "smirk") face.push(tag("path", { d: `M${cx - mw * 0.6} ${my + 0.5}Q${cx + mw * 0.3} ${my + 1.8} ${cx + mw} ${my - 2.2}`, ...stroke(fg, 2.2) }));
  if (t.mouth === "blep") {
    face.push(tag("path", { d: `M${cx - mw * 0.8} ${my - 1}H${cx + mw * 0.8}`, ...stroke(fg, 2.2) }));
    face.push(tag("path", { d: `M${cx - 0.2} ${my - 0.8}V${my + 1.4}A2.2 2.2 0 0 0 ${cx + 4.2} ${my + 1.4}V${my - 0.8}`, fill: light ? "var(--color-muted)" : "var(--color-ink)", stroke: fg, "stroke-width": 1.4, "stroke-linejoin": "round" }));
  }
  if (t.mouth === "grin") {
    face.push(tag("path", { d: `M${cx - mw} ${my - 2.4}H${cx + mw}Q${cx + mw} ${my + 4} ${cx} ${my + 4}Q${cx - mw} ${my + 4} ${cx - mw} ${my - 2.4}Z`, fill: DARK, stroke: fg, "stroke-width": 1.8, "stroke-linejoin": "round" }));
    face.push(tag("rect", { x: cx - 3.2, y: my - 2.4, width: 2.8, height: 2.4, fill: LINE }), tag("rect", { x: cx + 0.4, y: my - 2.4, width: 2.8, height: 2.4, fill: LINE }));
  }

  // The extras.
  for (const x of t.extras) {
    if (x === "brows") {
      const up = t.look[1] > 0 ? 1 : -1; // cross or surprised
      face.push(tag("path", { d: `M${lx - 3.5} ${ey - 6.5 + up}L${lx + 3} ${ey - 6.5 - up}M${rx - 3} ${ey - 6.5 - up}L${rx + 3.5} ${ey - 6.5 + up}`, ...stroke(fg, 2) }));
    }
    if (x === "cheeks") for (const c of [lx - 2.5, rx + 2.5]) face.push(tag("ellipse", { cx: c, cy: my - 2.8, rx: 2.6, ry: 1.6, fill: light ? "rgb(11 12 13 / 0.18)" : "rgb(242 240 234 / 0.16)" }));
    if (x === "mustache") face.push(tag("path", { d: `M${cx} ${my - 4.4}Q${cx - 3} ${my - 6.4} ${cx - 6} ${my - 4.6}Q${cx - 8} ${my - 3.4} ${cx - 8.6} ${my - 5.2}Q${cx - 7.8} ${my - 1.6} ${cx - 4.4} ${my - 2.4}Q${cx - 2} ${my - 3} ${cx} ${my - 3.4}Q${cx + 2} ${my - 3} ${cx + 4.4} ${my - 2.4}Q${cx + 7.8} ${my - 1.6} ${cx + 8.6} ${my - 5.2}Q${cx + 8} ${my - 3.4} ${cx + 6} ${my - 4.6}Q${cx + 3} ${my - 6.4} ${cx} ${my - 4.4}Z`, fill: fg }));
    if (x === "monocle") face.push(tag("circle", { cx: rx, cy: ey, r: 5.6, ...stroke(fg, 1.6) }), tag("path", { d: `M${rx + 4} ${ey + 4}Q${rx + 6} ${my + 2} ${box.right - 3} ${box.bottom - 2}`, ...stroke(fg, 1.1) }));
    if (x === "patch") face.push(tag("path", { d: `M${box.left + 2} ${ey - 7}L${box.right - 4} ${ey + 4}`, ...stroke(DARK, 1.6) }), tag("ellipse", { cx: lx, cy: ey, rx: 5, ry: 4.4, fill: DARK, stroke: LINE, "stroke-width": 1.2 }));
    if (x === "screw") {
      const sx = box.right - 7, sy = box.top + 6;
      face.push(tag("circle", { cx: sx, cy: sy, r: 1.9, fill: "none", stroke: fg, "stroke-width": 1.2 }), tag("path", { d: `M${sx - 1.2} ${sy - 1.2}L${sx + 1.2} ${sy + 1.2}`, ...stroke(fg, 1.1) }));
    }
  }
  const over: string[] = [];
  for (const x of t.extras) {
    if (x === "headphones") {
      const y = ey + 1;
      over.push(tag("path", { d: `M${box.left - 1} ${y}V${y - 6}A${(box.right - box.left) / 2 + 1} ${y - top + 3} 0 0 1 ${box.right + 1} ${y - 6}V${y}`, ...stroke(LINE, 2.4) }));
      for (const s of [-1, 1]) over.push(tag("rect", { x: s < 0 ? box.left - 4.5 : box.right - 1.5, y: y - 3, width: 6, height: 10, rx: 2.5, fill: PANEL, stroke: LINE, "stroke-width": 2 }));
    }
    if (x === "hat") {
      over.push(tag("path", { d: `M${cx - 13} ${top + 1.5}H${cx + 13}`, ...stroke(LINE, 2.6) }));
      over.push(tag("path", { d: `M${cx - 8} ${top + 1}V${top - 10}Q${cx - 8} ${top - 12} ${cx - 6} ${top - 12}H${cx + 6}Q${cx + 8} ${top - 12} ${cx + 8} ${top - 10}V${top + 1}Z`, fill: DARK, stroke: LINE, "stroke-width": 2.2, "stroke-linejoin": "round" }));
      over.push(tag("path", { d: `M${cx - 8} ${top - 3}H${cx + 8}`, ...stroke(LINE, 1.6) }));
    }
  }
  const tilt = t.tilt ? ` transform="rotate(${t.tilt} 32 ${box.bottom})"` : "";
  put(`<g${tilt}>${head.join("")}${face.join("")}${over.join("")}</g>`);
  if (t.extras.includes("bowtie")) put(tag("path", { d: "M32 53.5L26 50.5V56.5ZM32 53.5L38 50.5V56.5Z", fill: LINE, stroke: LINE, "stroke-width": 1.4, "stroke-linejoin": "round" }));

  const bg = opts.frame === false ? "" : tag("rect", { x: 0, y: 0, width: 64, height: 64, rx: 12, fill: "var(--color-panel)" });
  const a11y = opts.label ? `role="img" aria-label="${opts.label.replace(/[<>&"]/g, "")}"` : `aria-hidden="true"`;
  return `<svg viewBox="0 0 64 64" width="${size}" height="${size}" ${a11y} class="robot-svg">${bg}<g>${parts.join("")}</g></svg>`;
}

// The face as an element, for the pages drawn in the browser.
export function robot(slug: string, size = 40, cls = ""): HTMLElement {
  const el = document.createElement("span");
  el.className = `robot ${cls}`.trim();
  el.innerHTML = robotSvg(slug, size);
  return el;
}

// The index on the board has no face: a small panel with a line going up, the size of a bot's.
export function indexFace(size = 28): HTMLElement {
  const el = document.createElement("span");
  el.className = "robot";
  el.innerHTML = `<svg viewBox="0 0 64 64" width="${size}" height="${size}" aria-hidden="true"><rect width="64" height="64" rx="12" fill="var(--color-panel)"/>`
    + `<path d="M14 44L24 36L32 40L42 26L50 22" fill="none" stroke="var(--color-muted)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>`
    + `<path d="M14 50H50" stroke="var(--color-line-strong)" stroke-width="2.4" stroke-linecap="round"/></svg>`;
  return el;
}
