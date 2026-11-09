// Writes the faces site/src/lib/robot.ts draws for a set of slugs, for the test that checks the
// server's copy (src/botleague/robot.py) draws the same ones (tests/test_card.py).
//
// Run from this repo: node scripts/robot_faces.mjs > tests/fixtures/robot_faces.json
// (Node 23.6 or later reads the TypeScript file as it is.)

import { robotSvg, traits } from "../site/src/lib/robot.ts";

const slugs = [];
for (let i = 0; i < 90; i++) slugs.push((i * 2654435761 >>> 0).toString(36).slice(0, 4 + (i % 9)));
slugs.push("a", "bag-holder", "momentum-0", "zz-top", "x".repeat(60));
const out = slugs.map((slug, i) => ({ slug, traits: traits(slug), svg: robotSvg(slug, 96), ...(i % 10 === 0 ? { bare: robotSvg(slug, 300, { frame: false, label: "A & <b>" }) } : {}) }));
process.stdout.write(JSON.stringify(out, null, 0) + "\n");
