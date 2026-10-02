import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return walk(full);
    return /\.(tsx?|css)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [full] : [];
  });
}

const FILES = ["app", "components", "lib"].flatMap(walk);
const text = FILES.map((f) => [f, readFileSync(f, "utf8")] as const);

describe("public copy", () => {
  it("has no em dashes or en dashes (house style)", () => {
    for (const [file, body] of text) expect(body, file).not.toMatch(/[\u2013\u2014]/);
  });
  it("makes no claims about customers, results or scale", () => {
    for (const [file, body] of text) {
      expect(body, file).not.toMatch(
        /trusted by|customers love|\d+x faster|enterprise-grade|AI-powered|revolution/i,
      );
    }
  });
  it("does not use startup vocabulary", () => {
    for (const [file, body] of text)
      expect(body, file).not.toMatch(/\b(unlock|supercharge|seamless|game-changing)\b/i);
  });
  it("the Next.js app never imports the Python decision logic or re-implements a state resolver", () => {
    for (const [file, body] of text) {
      expect(body, file).not.toMatch(/function (resolve|decidePair|decide_pair)\b/);
    }
  });
});
