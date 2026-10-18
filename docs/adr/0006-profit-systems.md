# ADR 0006: Profit systems (packaging, pricing, upgrades, retention, ledger, dashboard)

## Status

Accepted. Billing OFF. No charge path. No merge without approval.

## Context

Effectivity classifies unit and change pairs. The resolver is the product.
Around it, a programme needs packaging, a price to quote, a way to move
between packages, a way to keep using it, a record of value delivered, and
a dashboard that shows usage, conversion, and retention. Those are profit
systems, and they must not touch decisions: a pricing or retention change
must never change a six state classification.

## Decision

1. **Canonical profit logic lives in `src/effectivity/profit.py`.** It is a
   pure module: no clock, filesystem, network, logging, or randomness. Every
   time dependent value is supplied by the caller. It never imports the
   resolver and never decides a pair.
2. **The web mirrors it in `lib/profit.ts`.** The two implementations are
   kept in sync by shared vectors in `tests/profit-vectors.json`, asserted
   by `tests/test_profit.py` and `lib/profit.test.ts`. If a vector changes,
   both suites must be updated together.
3. **Packaging:** three packages, in order Library, Pilot, Per programme.
   Library is the reference tier. Pilot is one programme for one trial
   period. Per programme is one licence per programme. Limits are stated
   per package in `docs/profit.md`.
4. **Pricing is proposed only.** Quotes return a proposed price in integer
   cents, `billing_enabled` False, `charge_amount_cents` 0, and status
   `proposed_not_charged`. Annual equals 10 monthly payments. There is no
   checkout, no payment form, and no charge path anywhere in this codebase.
5. **Upgrade and downgrade flows** go through the ledger. Steps: confirm
   with a reason, check usage fits the target limits, record the move in
   the ledger, apply new limits from the next run, review the dashboard
   after the first run on the new package. A downgrade is not a refund.
   A move is blocked only when supplied usage exceeds a target limit.
6. **Retention** is a descriptive score from supplied per period usage:
   active periods, recent activity, and value events (blocked material
   caught plus late units surfaced). Bands: strong 80 or more, steady 50
   or more, at risk 25 or more, else dormant. It predicts nothing.
7. **The value ledger** records runs, upgrades, downgrades, renewals, and
   pilot starts and ends. Each run entry needs an `evidence_ref` back to
   the run it records. Entry ids are unique. Counts are non-negative
   integers. The ledger never records money: real revenue is always 0.
8. **The dashboard** aggregates only caller supplied data. With an empty
   funnel it reports null conversion rates, not estimates. This site runs
   no analytics, so the funnel is zero unless real counts are supplied.
   The dashboard states plainly that no paying customers are claimed.
9. **Demo data is labeled demo data.** The web dashboard renders a ledger
   built from the bundled synthetic example plus a second demonstration
   run. It is not real customers, real programmes, or real revenue.

## What this ADR does not decide

No billing provider, no checkout, no accounts, no stored customer data,
and no live charges. Any of those needs its own ADR and its own approval,
plus a separate decision about what may be stored and where.

## Consequences

- Profit changes cannot change classifications, because the profit module
  has no path to the resolver.
- Prices can be quoted in a conversation or a proposal without implying a
  charge, because quoting and charging are separate and charging does not
  exist here.
- The ledger gives a programme a checkable record of value delivered:
  runs, decisions, blocked material caught, late units surfaced.
- Before any charge: billing integration, a storage decision for ledger
  entries, terms for pilots and refunds, and approval.
