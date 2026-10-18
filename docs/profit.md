# Profit systems

Packaging, proposed pricing, upgrade flows, retention, ledger of value
delivered, and dashboard. Spec for `src/effectivity/profit.py` and its web
mirror `lib/profit.ts`. The two are kept in sync by the shared vectors in
`tests/profit-vectors.json`. Billing is OFF. No charge path exists.

## Packages

| Package | Proposed monthly | Proposed annual | Programmes | Units | Changes | Pairs | Seats |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Library | $0 | $0 | 1 | 50 | 10 | 100 | 1 |
| Pilot | $490 | $4,900 | 1 | 250 | 50 | 5,000 | 5 |
| Per programme | $1,900 | $19,000 | 1 per licence | 1,000 | 200 | 5,000 | 25 |

Annual equals 10 monthly payments. Library is the reference tier: rule
text, worked example, and the bundled synthetic sample only. Pilot is one
programme for one trial period, with JSON download of each run, a value
ledger, and the dashboard. Per programme is one licence per programme,
with JSON and CSV download, a ledger with evidence references, the
dashboard, and upgrade and downgrade flows.

## Pricing rules

- Prices are PROPOSED only. A quote returns `proposed_cents`,
  `billing_enabled` False, `charge_amount_cents` 0, and status
  `proposed_not_charged`.
- Money is integer cents. No floats carry money.
- Quoting is not charging. There is no checkout, no payment form, and no
  charge path in this codebase.
- Real revenue is always 0 until a real charge is recorded through
  billing, which is off. Nothing in the ledger, dashboard, or copy claims
  a customer, a sale, or a measured result.

## Upgrade and downgrade flows

Order: Library, then Pilot, then Per programme. Moving up is an upgrade.
Moving down is a downgrade. Staying put is a no-op.

Steps, in order:

1. Confirm the move with a reason.
2. Check current usage fits inside the target limits.
3. For a downgrade, confirm it is not a refund: past periods keep their terms.
4. Record the move in the value ledger with the reason.
5. Apply the new limits from the next run.
6. Review the dashboard after the first run on the new package.

A move is blocked only when supplied usage exceeds a target limit. The
blocker message names the usage and the limit.

## Retention

Descriptive score from caller supplied per period usage. Each period is
`{runs, blocked_material, late}`.

- Score = min(100, 20 * min(active periods, 3) + 15 if the last period
  had runs + min(25, 5 * min(value events, 5))).
- Value events = blocked material caught + late units surfaced, summed
  over supplied periods.
- Bands: strong 80 or more, steady 50 or more, at risk 25 or more, else
  dormant.
- The score describes supplied usage only. It predicts nothing and claims
  no customer behaviour.

## Value ledger

An entry is:

```
entry_id, kind, period_label, recorded_by, note, evidence_ref,
units, changes, decisions, blocked_material, late_surfaced, incorporated
```

Kinds: run, upgrade, downgrade, renewal, pilot_start, pilot_end, note.

Rules:

- `entry_id` is a non-empty string, unique across the ledger.
- A `run` entry needs an `evidence_ref` back to the run it records, for
  example a run log hash or sequence.
- All counts are non-negative integers.
- The ledger never records money. Its summary reports `real_revenue_cents`
  0 and `claimed_revenue_cents` 0.
- The ledger proves work done and problems surfaced: runs, decisions,
  blocked material caught, late units surfaced, incorporations recorded.

The ledger is a pure data structure. This codebase stores no ledger
entries: the caller keeps them. Any future storage needs its own ADR.

## Dashboard

`dashboard_summary` aggregates caller supplied data:

- Usage against the package limits: used, limit, over flag, and percent.
  Percent is integer floor division, or null when the limit is zero.
- Ledger summary: entries, totals, counts by kind, evidence references.
- Funnel: visitors, trials started, pilots started, paid programmes, and
  four conversion rates. A rate is null when its denominator is zero.
  This site runs no analytics, so the funnel is zero unless real counts
  are supplied. A zero funnel reports no rate, not an estimated rate.
- Retention score and band from supplied periods.
- Billing: `billing_enabled` False, `real_revenue_cents` 0,
  `next_charge_cents` 0.
- An honesty line: no paying customers are claimed.

The web dashboard at `/dashboard` renders these aggregates from a labeled
demonstration ledger built from the bundled synthetic example plus a
second demonstration run. It is not real customers, real programmes, or
real revenue.

## What is still blocked before charging

- A billing provider integration, with its own ADR and approval.
- A storage decision for ledger entries and funnel counts: what is kept,
  where, for how long, and who can read it.
- Terms for pilots, renewals, downgrades, and refunds.
- Approval to charge. Nothing in this change is that approval.
