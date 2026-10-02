#!/usr/bin/env node
// Generates lib/rules.generated.json from the decision table in docs/state-machine.md.
// The document stays the source of truth; the UI never carries its own copy of the rules.
//   node scripts/gen-rules.mjs          write the file
//   node scripts/gen-rules.mjs --check  fail if the file is stale (used in CI and by a test)
import { readFileSync, writeFileSync } from "node:fs";

const DOC = new URL("../docs/state-machine.md", import.meta.url);
const OUT = new URL("../lib/rules.generated.json", import.meta.url);

export function parseRules(markdown) {
  const rules = [];
  for (const line of markdown.split("\n")) {
    if (!/^\| R\d\d \|/.test(line)) continue;
    const cells = line
      .replace(/^\||\|$/g, "")
      .split("|")
      .map((cell) => cell.trim());
    const [id, condition, status, codes] = cells;
    rules.push({
      id,
      condition: condition.replace(/`/g, ""),
      status: /`([a-z_]+)`/.exec(status)?.[1] ?? null,
      reasonCodes: [...codes.matchAll(/`([A-Z][A-Z_]+)`/g)].map((m) => m[1]),
    });
  }
  return rules;
}

export function renderRules(markdown) {
  const version = /Rule version: `([^`]+)`/.exec(markdown)?.[1];
  if (!version) throw new Error("docs/state-machine.md: rule version line not found");
  const rules = parseRules(markdown);
  if (rules.length === 0) throw new Error("docs/state-machine.md: no rule rows found");
  return JSON.stringify({ ruleVersion: version, rules }, null, 2) + "\n";
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const next = renderRules(readFileSync(DOC, "utf8"));
  if (process.argv.includes("--check")) {
    let current = "";
    try {
      current = readFileSync(OUT, "utf8");
    } catch {
      /* missing counts as stale */
    }
    if (current !== next) {
      console.error("lib/rules.generated.json is stale. Run: npm run gen:rules");
      process.exit(1);
    }
    console.log("rules: up to date");
  } else {
    writeFileSync(OUT, next);
    console.log("rules: wrote lib/rules.generated.json");
  }
}
