import { describe, expect, it } from "vitest";
import { countByState, filterDecisions, toggleState } from "./filter";
import type { Decision } from "./schema";
import { STATE_ORDER, type State } from "./states";

const d = (
  unit: string,
  change: string,
  status: State,
  code: string,
  rules: string[],
): Decision => ({
  unit_id: unit,
  change_id: change,
  status,
  reason_code: code,
  rule_ids: rules,
});

const DECISIONS = [
  d("U-1", "C-1", "incorporated", "INCORPORATED", ["R02"]),
  d("U-2", "C-1", "late", "PAST_HOLD_POINT", ["R09"]),
  d("U-3", "C-2", "late", "PAST_HOLD_POINT", ["R09"]),
  d("U-3", "C-3", "blocked_material", "SUPERSEDED_PART_STAGED", ["R05"]),
];

describe("filterDecisions", () => {
  it("returns everything when nothing is selected and the query is empty", () => {
    expect(filterDecisions(DECISIONS, new Set(), "")).toHaveLength(4);
    expect(filterDecisions(DECISIONS, new Set(), "   ")).toHaveLength(4);
  });
  it("filters by selected states (union)", () => {
    expect(filterDecisions(DECISIONS, new Set<State>(["late"]), "")).toHaveLength(2);
    expect(filterDecisions(DECISIONS, new Set<State>(["late", "incorporated"]), "")).toHaveLength(
      3,
    );
  });
  it("matches the query against unit, change, reason code and rule ids, ignoring case", () => {
    expect(filterDecisions(DECISIONS, new Set(), "u-3")).toHaveLength(2);
    expect(filterDecisions(DECISIONS, new Set(), "c-2")).toHaveLength(1);
    expect(filterDecisions(DECISIONS, new Set(), "staged")).toHaveLength(1);
    expect(filterDecisions(DECISIONS, new Set(), "r09")).toHaveLength(2);
  });
  it("combines state and query with AND", () => {
    expect(filterDecisions(DECISIONS, new Set<State>(["late"]), "u-3")).toHaveLength(1);
    expect(filterDecisions(DECISIONS, new Set<State>(["incorporated"]), "u-3")).toHaveLength(0);
  });
  it("does not mutate its input", () => {
    const copy = structuredClone(DECISIONS);
    filterDecisions(DECISIONS, new Set<State>(["late"]), "u");
    expect(DECISIONS).toEqual(copy);
  });
});

describe("toggleState", () => {
  it("adds and removes without mutating the original", () => {
    const empty = new Set<State>();
    const one = toggleState(empty, "late");
    expect([...one]).toEqual(["late"]);
    expect(empty.size).toBe(0);
    expect(toggleState(one, "late").size).toBe(0);
  });
});

describe("countByState", () => {
  it("always has all six keys in canonical order", () => {
    expect(Object.keys(countByState([]))).toEqual([...STATE_ORDER]);
    expect(countByState(DECISIONS)).toEqual({
      out_of_effectivity: 0,
      not_yet_reached: 0,
      incorporable: 0,
      late: 2,
      blocked_material: 1,
      incorporated: 1,
    });
  });
});
