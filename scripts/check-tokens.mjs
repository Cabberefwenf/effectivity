// Design-token drift guard.
//  1. Raw colour literals (#hex, rgb(), hsl()) are allowed only in app/globals.css (the tokens)
//     and in the few files whose output cannot use CSS variables. There every hex must still be
//     one of the token colours, so the two cannot drift.
//  2. Every colour in tailwind.config.ts must point at a variable defined in globals.css.
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (p) => readFileSync(path.join(root, p), "utf8");

const ALLOWED_RAW = new Set([
  "app/globals.css",
  "app/icon.tsx",
  "app/opengraph-image.tsx",
  "app/layout.tsx",
]);
const SCAN_DIRS = ["app", "components", "lib"];
const LITERAL = /#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|\b(?:rgba?|hsla?)\(/g;

function walk(dir) {
  const out = [];
  for (const name of readdirSync(path.join(root, dir))) {
    const rel = `${dir}/${name}`;
    if (statSync(path.join(root, rel)).isDirectory()) out.push(...walk(rel));
    else if (/\.(tsx?|css)$/.test(name) && !/\.test\.tsx?$/.test(name)) out.push(rel);
  }
  return out;
}

const css = read("app/globals.css");
const vars = new Map();
for (const m of css.matchAll(/--([a-z0-9-]+):\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\s*;/g)) {
  vars.set(m[1], [m[2], m[3], m[4]].map(Number));
}
const toHex = (rgb) => "#" + rgb.map((n) => n.toString(16).padStart(2, "0")).join("");
const tokenHexes = new Set([...vars.values()].map(toHex));

const problems = [];
for (const file of SCAN_DIRS.flatMap(walk)) {
  const text = read(file);
  const found = text.match(LITERAL) ?? [];
  if (found.length === 0) continue;
  if (!ALLOWED_RAW.has(file)) {
    problems.push(`${file}: raw colour literal ${found[0]} (use a token)`);
    continue;
  }
  if (file === "app/globals.css") continue;
  for (const lit of found) {
    if (!lit.startsWith("#") || !tokenHexes.has(lit.toLowerCase())) {
      problems.push(`${file}: ${lit} is not one of the tokens in app/globals.css`);
    }
  }
}

for (const m of read("tailwind.config.ts").matchAll(/var\(--([a-z0-9-]+)\)/g)) {
  if (["font-sans", "font-serif", "font-mono"].includes(m[1])) continue;
  if (!vars.has(m[1]))
    problems.push(`tailwind.config.ts: var(--${m[1]}) is not defined in globals.css`);
}

if (problems.length > 0) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log(`tokens ok: ${vars.size} colour tokens, no stray literals`);
