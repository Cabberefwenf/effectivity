/**
 * Profit systems: packaging, pricing, upgrades, retention, ledger of value
 * delivered, and dashboard aggregates. Pure functions only. No clock, no
 * network, no storage. Every time dependent value is supplied by the caller.
 *
 * This mirrors src/effectivity/profit.py. The two implementations are kept
 * in sync by the shared vectors in tests/profit-vectors.json, asserted by
 * both test suites. This module never decides a unit/change pair.
 *
 * Honesty rules, enforced by the code:
 * - Billing is OFF. priceQuote returns a PROPOSED price and a charge of 0.
 * - Real revenue is always 0. The ledger records usage and value delivered,
 *   never revenue. Nothing here claims a customer, a sale, or a result.
 * - Money is integer cents.
 */

export const BILLING_ENABLED = false as const;

export const PACKAGE_ORDER = ["library", "pilot", "per_programme"] as const;
export type PackageId = (typeof PACKAGE_ORDER)[number];
export type BillingCycle = "monthly" | "annual";

export const LIMIT_KEYS = ["programmes", "units", "changes", "pairs", "seats"] as const;
export type LimitKey = (typeof LIMIT_KEYS)[number];
export type Usage = Partial<Record<LimitKey, number>>;

export type Package = {
  id: PackageId;
  name: string;
  tagline: string;
  monthlyCents: number;
  annualCents: number;
  limits: Record<LimitKey, number>;
  features: readonly string[];
};

/** Proposed prices only. Annual equals 10 monthly payments. Nothing is charged. */
export const PACKAGES: Record<PackageId, Package> = {
  library: {
    id: "library",
    name: "Library",
    tagline: "Read the rules and run the bundled synthetic sample.",
    monthlyCents: 0,
    annualCents: 0,
    limits: { programmes: 1, units: 50, changes: 10, pairs: 100, seats: 1 },
    features: [
      "Rule text and worked example",
      "Bundled synthetic sample only",
      "No exports beyond the on screen result",
    ],
  },
  pilot: {
    id: "pilot",
    name: "Pilot",
    tagline: "One programme, one trial period, with a value ledger.",
    monthlyCents: 49000,
    annualCents: 490000,
    limits: { programmes: 1, units: 250, changes: 50, pairs: 5000, seats: 5 },
    features: [
      "One programme for one trial period",
      "JSON download of each run",
      "Value ledger: runs, blocked material, late units",
      "Dashboard: usage, conversion, retention",
    ],
  },
  per_programme: {
    id: "per_programme",
    name: "Per programme",
    tagline: "One licence per programme, priced per programme.",
    monthlyCents: 190000,
    annualCents: 1900000,
    limits: { programmes: 1, units: 1000, changes: 200, pairs: 5000, seats: 25 },
    features: [
      "One licence per programme",
      "JSON and CSV download of each run",
      "Value ledger with evidence references",
      "Dashboard: usage, conversion, retention",
      "Upgrade and downgrade flows with ledger entries",
    ],
  },
};

export const LEDGER_KINDS = [
  "run",
  "upgrade",
  "downgrade",
  "renewal",
  "pilot_start",
  "pilot_end",
  "note",
] as const;
export type LedgerKind = (typeof LEDGER_KINDS)[number];

export type LedgerEntry = {
  entry_id: string;
  kind: LedgerKind;
  period_label: string;
  recorded_by: string;
  note: string;
  evidence_ref: string;
  units: number;
  changes: number;
  decisions: number;
  blocked_material: number;
  late_surfaced: number;
  incorporated: number;
};

export type RetentionPeriod = { runs: number; blocked_material: number; late: number };

export function getPackage(packageId: string): Package {
  const found = (PACKAGES as Record<string, Package | undefined>)[packageId];
  if (!found) throw new Error(`Unknown package: ${packageId}`);
  return found;
}

export function isPackageId(value: string): value is PackageId {
  return (PACKAGE_ORDER as readonly string[]).includes(value);
}

/** Proposed price. Quoting is not charging: the charge is always 0. */
export function priceQuote(packageId: string, cycle: BillingCycle) {
  const pkg = getPackage(packageId);
  if (cycle !== "monthly" && cycle !== "annual") {
    throw new Error(`Unknown billing cycle: ${cycle}`);
  }
  return {
    package_id: packageId,
    cycle,
    proposed_cents: cycle === "monthly" ? pkg.monthlyCents : pkg.annualCents,
    billing_enabled: BILLING_ENABLED,
    charge_amount_cents: 0,
    status: "proposed_not_charged" as const,
  };
}

export function formatCents(cents: number): string {
  return `$${(cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

function tierIndex(packageId: string): number {
  return (PACKAGE_ORDER as readonly string[]).indexOf(getPackage(packageId).id);
}

export function upgradePath(currentId: string, targetId: string) {
  const current = getPackage(currentId);
  const target = getPackage(targetId);
  if (currentId === targetId) {
    return {
      current_id: currentId,
      target_id: targetId,
      kind: "same" as const,
      steps: ["No change: the current package already applies."],
      limits_change: {} as Record<string, { from: number; to: number }>,
    };
  }
  const direction = tierIndex(targetId) > tierIndex(currentId) ? "upgrade" : "downgrade";
  const steps = [
    `Confirm the move from ${current.name} to ${target.name} with a reason.`,
    "Check current usage fits inside the target limits.",
    "Record the move in the value ledger with the reason.",
    "Apply the new limits from the next run.",
    "Review the dashboard after the first run on the new package.",
  ];
  if (direction === "downgrade") {
    steps.splice(2, 0, "Confirm the downgrade is not a refund: past periods keep their terms.");
  }
  const limitsChange: Record<string, { from: number; to: number }> = {};
  for (const key of LIMIT_KEYS) {
    if (current.limits[key] !== target.limits[key]) {
      limitsChange[key] = { from: current.limits[key], to: target.limits[key] };
    }
  }
  return {
    current_id: currentId,
    target_id: targetId,
    kind: direction,
    steps,
    limits_change: limitsChange,
  };
}

/** A move is blocked only when supplied usage exceeds a target limit. */
export function upgradeEligibility(currentId: string, targetId: string, usage: Usage) {
  const target = getPackage(targetId);
  getPackage(currentId);
  const blockers = LIMIT_KEYS.filter((key) => (usage[key] ?? 0) > target.limits[key]).map(
    (key) =>
      `Usage ${key} is ${usage[key] ?? 0}, above the ${target.name} limit of ${target.limits[key]}.`,
  );
  return { current_id: currentId, target_id: targetId, allowed: blockers.length === 0, blockers };
}

export type RetentionBand = "strong" | "steady" | "at_risk" | "dormant";

/** Descriptive score from supplied per period usage. It predicts nothing. */
export function retentionScore(periods: RetentionPeriod[]) {
  const activePeriods = periods.filter((p) => p.runs > 0).length;
  const last = periods.length > 0 ? periods[periods.length - 1] : undefined;
  const recentActive = last !== undefined && last.runs > 0;
  const valueEvents = periods.reduce((sum, p) => sum + p.blocked_material + p.late, 0);
  const score = Math.min(
    100,
    20 * Math.min(activePeriods, 3) +
      (recentActive ? 15 : 0) +
      Math.min(25, 5 * Math.min(valueEvents, 5)),
  );
  const band: RetentionBand =
    score >= 80 ? "strong" : score >= 50 ? "steady" : score >= 25 ? "at_risk" : "dormant";
  return {
    score,
    band,
    active_periods: activePeriods,
    periods_supplied: periods.length,
    recent_active: recentActive,
    value_events: valueEvents,
  };
}

export function validateLedger(entries: LedgerEntry[]): string[] {
  const problems: string[] = [];
  const seen = new Set<string>();
  const countKeys = [
    "units",
    "changes",
    "decisions",
    "blocked_material",
    "late_surfaced",
    "incorporated",
  ] as const;
  entries.forEach((entry, i) => {
    const where = `entry ${i}`;
    if (!entry.entry_id) {
      problems.push(`${where}: entry_id must be a non-empty string.`);
    } else if (seen.has(entry.entry_id)) {
      problems.push(`${where}: duplicate entry_id ${entry.entry_id}.`);
    } else {
      seen.add(entry.entry_id);
    }
    if (!(LEDGER_KINDS as readonly string[]).includes(entry.kind)) {
      problems.push(`${where}: kind must be one of ${LEDGER_KINDS.join(", ")}.`);
    }
    if (entry.kind === "run" && !entry.evidence_ref) {
      problems.push(`${where}: a run entry needs an evidence_ref.`);
    }
    for (const key of countKeys) {
      const value = entry[key];
      if (!Number.isInteger(value) || value < 0) {
        problems.push(`${where}: ${key} must be a non-negative integer.`);
      }
    }
  });
  return problems;
}

/** Aggregate a validated ledger into proof of value delivered. Revenue is always zero. */
export function ledgerSummary(entries: LedgerEntry[]) {
  const problems = validateLedger(entries);
  if (problems.length > 0) throw new Error(problems.join("; "));
  const totals = {
    units: 0,
    changes: 0,
    decisions: 0,
    blocked_material: 0,
    late_surfaced: 0,
    incorporated: 0,
  };
  const byKind: Record<string, number> = {};
  for (const entry of entries) {
    totals.units += entry.units;
    totals.changes += entry.changes;
    totals.decisions += entry.decisions;
    totals.blocked_material += entry.blocked_material;
    totals.late_surfaced += entry.late_surfaced;
    totals.incorporated += entry.incorporated;
    byKind[entry.kind] = (byKind[entry.kind] ?? 0) + 1;
  }
  return {
    entries: entries.length,
    totals,
    by_kind: byKind,
    evidence_refs: entries.map((e) => e.evidence_ref).filter((ref) => ref !== ""),
    revenue: { real_revenue_cents: 0, claimed_revenue_cents: 0, billing_enabled: BILLING_ENABLED },
  };
}

function conversion(numerator: number, denominator: number): number | null {
  if (denominator <= 0) return null;
  return Math.round((numerator / denominator) * 10000) / 10000;
}

export type Funnel = {
  visitors?: number;
  trials_started?: number;
  pilots_started?: number;
  paid_programmes?: number;
};

/**
 * Dashboard aggregates from caller supplied data. An empty funnel reports
 * null conversion rates rather than inventing a rate. This site runs no
 * analytics, so the funnel is zero unless real counts are supplied.
 */
export function dashboardSummary(options: {
  package_id: string;
  usage: Usage;
  ledger_entries: LedgerEntry[];
  funnel?: Funnel;
  retention_periods?: RetentionPeriod[];
}) {
  const pkg = getPackage(options.package_id);
  const funnel = options.funnel ?? {};
  const visitors = funnel.visitors ?? 0;
  const trials = funnel.trials_started ?? 0;
  const pilots = funnel.pilots_started ?? 0;
  const paid = funnel.paid_programmes ?? 0;
  const usageVsLimits = {} as Record<
    LimitKey,
    { used: number; limit: number; over: boolean; percent: number | null }
  >;
  for (const key of LIMIT_KEYS) {
    const used = options.usage[key] ?? 0;
    const limit = pkg.limits[key];
    usageVsLimits[key] = {
      used,
      limit,
      over: used > limit,
      percent: limit > 0 ? Math.floor((used * 100) / limit) : null,
    };
  }
  return {
    package: { id: options.package_id, name: pkg.name },
    usage_vs_limits: usageVsLimits,
    retention: retentionScore(options.retention_periods ?? []),
    ledger: ledgerSummary(options.ledger_entries),
    funnel: {
      visitors,
      trials_started: trials,
      pilots_started: pilots,
      paid_programmes: paid,
      conversion: {
        visitor_to_trial: conversion(trials, visitors),
        trial_to_pilot: conversion(pilots, trials),
        pilot_to_paid: conversion(paid, pilots),
        visitor_to_paid: conversion(paid, visitors),
      },
    },
    billing: { billing_enabled: BILLING_ENABLED, real_revenue_cents: 0, next_charge_cents: 0 },
    honesty:
      "No paying customers are claimed. Revenue is zero until a real charge is recorded through billing, which is off.",
  };
}

/** Demonstration ledger only. Derived from the bundled synthetic example. Not real customers. */
export const DEMO_LEDGER: LedgerEntry[] = [
  {
    entry_id: "L1",
    kind: "run",
    period_label: "demo-1",
    recorded_by: "demo",
    note: "Bundled synthetic example.",
    evidence_ref: "golden:examples-report",
    units: 10,
    changes: 5,
    decisions: 50,
    blocked_material: 3,
    late_surfaced: 2,
    incorporated: 2,
  },
  {
    entry_id: "L2",
    kind: "run",
    period_label: "demo-2",
    recorded_by: "demo",
    note: "Second demonstration run.",
    evidence_ref: "demo:second-run",
    units: 4,
    changes: 2,
    decisions: 8,
    blocked_material: 1,
    late_surfaced: 0,
    incorporated: 1,
  },
  {
    entry_id: "L3",
    kind: "pilot_start",
    period_label: "demo-2",
    recorded_by: "demo",
    note: "Pilot start recorded in the ledger.",
    evidence_ref: "",
    units: 0,
    changes: 0,
    decisions: 0,
    blocked_material: 0,
    late_surfaced: 0,
    incorporated: 0,
  },
];

export const DEMO_USAGE: Usage = { programmes: 1, units: 10, changes: 5, pairs: 50, seats: 1 };

export const DEMO_RETENTION_PERIODS: RetentionPeriod[] = [
  { runs: 2, blocked_material: 3, late: 2 },
  { runs: 1, blocked_material: 1, late: 0 },
];
