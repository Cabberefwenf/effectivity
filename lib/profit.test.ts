import { describe, expect, it } from "vitest";
import vectors from "../tests/profit-vectors.json";
import {
  BILLING_ENABLED,
  DEMO_LEDGER,
  DEMO_RETENTION_PERIODS,
  DEMO_USAGE,
  PACKAGE_ORDER,
  dashboardSummary,
  formatCents,
  ledgerSummary,
  priceQuote,
  retentionScore,
  upgradeEligibility,
  upgradePath,
  validateLedger,
  type LedgerEntry,
} from "./profit";

describe("price quotes", () => {
  it("matches the shared vectors", () => {
    for (const vector of vectors.price_quotes) {
      expect(priceQuote(vector.package_id, vector.cycle as "monthly" | "annual")).toEqual(vector);
    }
  });
  it("billing is off and no quote ever charges", () => {
    expect(BILLING_ENABLED).toBe(false);
    for (const id of PACKAGE_ORDER) {
      for (const cycle of ["monthly", "annual"] as const) {
        const quote = priceQuote(id, cycle);
        expect(quote.charge_amount_cents).toBe(0);
        expect(quote.billing_enabled).toBe(false);
        expect(quote.status).toBe("proposed_not_charged");
      }
    }
  });
  it("annual price equals ten monthly payments", () => {
    for (const id of PACKAGE_ORDER) {
      expect(priceQuote(id, "annual").proposed_cents).toBe(
        priceQuote(id, "monthly").proposed_cents * 10,
      );
    }
  });
  it("rejects unknown packages and cycles", () => {
    expect(() => priceQuote("nope", "monthly")).toThrow();
    expect(() => priceQuote("pilot", "weekly" as "monthly")).toThrow();
  });
  it("formats cents as whole dollars", () => {
    expect(formatCents(49000)).toBe("$490");
    expect(formatCents(1900000)).toBe("$19,000");
    expect(formatCents(0)).toBe("$0");
  });
});

describe("upgrade flows", () => {
  it("matches the shared upgrade kinds", () => {
    for (const vector of vectors.upgrade_kinds) {
      const path = upgradePath(vector.current_id, vector.target_id);
      expect(path.kind).toBe(vector.kind);
    }
  });
  it("lists steps and limits changes for an upgrade", () => {
    const path = upgradePath("library", "pilot");
    expect(path.steps[0]).toMatch(/^Confirm the move/);
    expect(path.limits_change.units).toEqual({ from: 50, to: 250 });
    expect(upgradePath("pilot", "pilot").steps).toEqual([
      "No change: the current package already applies.",
    ]);
  });
  it("states a downgrade is not a refund", () => {
    const path = upgradePath("per_programme", "pilot");
    expect(path.steps.some((step) => step.includes("not a refund"))).toBe(true);
  });
  it("blocks moves when usage exceeds the target limits", () => {
    expect(upgradeEligibility("library", "pilot", { units: 10, changes: 5 }).allowed).toBe(true);
    const blocked = upgradeEligibility("per_programme", "pilot", { units: 900 });
    expect(blocked.allowed).toBe(false);
    expect(blocked.blockers).toHaveLength(1);
    expect(blocked.blockers[0]).toContain("900");
  });
});

describe("retention", () => {
  it("matches the shared vectors", () => {
    for (const vector of vectors.retention) {
      const got = retentionScore(vector.periods);
      expect(got.score).toBe(vector.score);
      expect(got.band).toBe(vector.band);
      expect(got.active_periods).toBe(vector.active_periods);
      expect(got.value_events).toBe(vector.value_events);
    }
  });
  it("caps at 100 and reports dormant for no periods", () => {
    const busy = Array.from({ length: 9 }, () => ({ runs: 9, blocked_material: 99, late: 99 }));
    expect(retentionScore(busy).score).toBe(100);
    expect(retentionScore([]).band).toBe("dormant");
  });
});

describe("ledger", () => {
  it("matches the shared ledger summary", () => {
    const summary = ledgerSummary(vectors.ledger.entries as never);
    expect(summary.entries).toBe(vectors.ledger.summary.entries);
    expect(summary.totals).toEqual(vectors.ledger.summary.totals);
    expect(summary.by_kind).toEqual(vectors.ledger.summary.by_kind);
    expect(summary.revenue.real_revenue_cents).toBe(0);
  });
  it("rejects duplicate ids, missing evidence, negatives, and bad kinds", () => {
    const base: LedgerEntry = DEMO_LEDGER[0] as LedgerEntry;
    expect(validateLedger([base])).toEqual([]);
    expect(validateLedger([base, base]).some((p) => p.includes("duplicate"))).toBe(true);
    expect(
      validateLedger([{ ...base, evidence_ref: "" }]).some((p) => p.includes("evidence_ref")),
    ).toBe(true);
    expect(
      validateLedger([{ ...base, entry_id: "X1", blocked_material: -1 }]).some((p) =>
        p.includes("blocked_material"),
      ),
    ).toBe(true);
    expect(
      validateLedger([{ ...base, entry_id: "X2", kind: "sale" as never }]).some((p) =>
        p.includes("kind"),
      ),
    ).toBe(true);
    expect(() => ledgerSummary([base, base])).toThrow();
  });
});

describe("dashboard", () => {
  it("reports null conversion rates for an empty funnel", () => {
    const vector = vectors.dashboard;
    const summary = dashboardSummary({
      package_id: vector.package_id,
      usage: vector.usage,
      ledger_entries: vectors.ledger.entries as never,
    });
    expect(summary.funnel.conversion).toEqual(vector.conversion);
    expect(summary.funnel).toMatchObject(vector.funnel);
    expect(summary.billing.real_revenue_cents).toBe(0);
    expect(summary.usage_vs_limits.units.percent).toBe(vector.units_percent);
  });
  it("computes conversion rates from a supplied funnel", () => {
    const summary = dashboardSummary({
      package_id: "pilot",
      usage: {},
      ledger_entries: [],
      funnel: { visitors: 100, trials_started: 20, pilots_started: 5, paid_programmes: 1 },
    });
    expect(summary.funnel.conversion).toEqual({
      visitor_to_trial: 0.2,
      trial_to_pilot: 0.25,
      pilot_to_paid: 0.2,
      visitor_to_paid: 0.01,
    });
  });
  it("flags over limit usage and carries the demo retention periods", () => {
    const summary = dashboardSummary({
      package_id: "library",
      usage: { units: 51 },
      ledger_entries: [],
    });
    expect(summary.usage_vs_limits.units.over).toBe(true);
    const demo = dashboardSummary({
      package_id: "pilot",
      usage: DEMO_USAGE,
      ledger_entries: DEMO_LEDGER,
      retention_periods: DEMO_RETENTION_PERIODS,
    });
    expect(demo.retention.band).toBe("strong");
    expect(demo.retention.score).toBe(80);
  });
});
