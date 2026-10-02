import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { renderRules } from "../scripts/gen-rules.mjs";
import golden from "../tests/golden/examples-report.json";
import { STATE_ORDER } from "./states";
import { RULES, RULE_VERSION, findRule } from "./rules";

const doc = readFileSync(new URL("../docs/state-machine.md", import.meta.url), "utf8");
const committed = readFileSync(new URL("./rules.generated.json", import.meta.url), "utf8");

describe("rules", () => {
  it("lib/rules.generated.json is exactly what docs/state-machine.md generates", () => {
    expect(committed).toBe(renderRules(doc));
  });
  it("the rule version matches the Python constant", () => {
    const py = readFileSync(new URL("../src/effectivity/__init__.py", import.meta.url), "utf8");
    const resolve = readFileSync(new URL("../src/effectivity/resolve.py", import.meta.url), "utf8");
    expect(`${py}\n${resolve}`).toContain(`RULE_VERSION = "${RULE_VERSION}"`);
  });
  it("has R01 to R10 in order, each with a reason code", () => {
    expect(RULES.map((r) => r.id)).toEqual(
      Array.from({ length: 10 }, (_, i) => `R${String(i + 1).padStart(2, "0")}`),
    );
    for (const rule of RULES) expect(rule.reasonCodes.length).toBeGreaterThan(0);
  });
  it("every one of the six states is decided by at least one rule", () => {
    const decided = new Set(RULES.map((r) => r.status));
    for (const state of STATE_ORDER) expect(decided.has(state)).toBe(true);
  });
  it("only R03 has no state of its own", () => {
    expect(RULES.filter((r) => r.status === null).map((r) => r.id)).toEqual(["R03"]);
  });
  it("every golden decision names rules, and its reason code is listed by one of them", () => {
    for (const d of golden.decisions) {
      const codes = d.rule_ids.flatMap((id) => {
        const rule = findRule(id);
        expect(rule, id).toBeDefined();
        return rule?.reasonCodes ?? [];
      });
      expect(codes, `${d.unit_id}/${d.change_id}`).toContain(d.reason_code);
    }
  });
  it("findRule", () => {
    expect(findRule("R05")?.id).toBe("R05");
    expect(findRule("R99")).toBeUndefined();
  });
});
