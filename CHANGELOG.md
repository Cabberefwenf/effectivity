# Changelog

Rule changes are recorded here with their rule version. Everything else is
listed under the date of the change.

## Unreleased

### Added

- Profit systems (ADR 0006, `docs/profit.md`): packaging (Library, Pilot,
  Per programme), proposed pricing only (Pilot $490/month or $4,900/year,
  Per programme $1,900/month or $19,000/year; annual equals 10 monthly
  payments), upgrade and downgrade flows through the ledger with a
  downgrade-is-not-a-refund rule, a descriptive retention score with four
  bands, a value ledger of runs and moves with evidence references, and a
  dashboard showing usage against limits, conversion, retention, and proof
  of value delivered. Canonical logic in `src/effectivity/profit.py`,
  mirrored in `lib/profit.ts`, kept in sync by shared vectors in
  `tests/profit-vectors.json`. Billing is OFF: every quote returns a
  charge of 0, real revenue is always 0, there is no checkout, and no
  customer, sale, or measured result is claimed. Web pages `/packaging`
  (packages plus an upgrade planner) and `/dashboard` (demonstration data
  only), plus end-to-end tests. The profit module never decides a pair.
  Blocked before charging: billing integration, ledger storage decision,
  pilot and refund terms, and approval to charge.
- Web surface (ADR 0003): Next.js shell and one stateless Python function
  (`api/resolve.py`) over the existing resolver. Rule version unchanged
  (1.0.0); decisions unchanged.
- `effectivity.service` (request handling and caps), `effectivity.tables`
  (shared CSV text parser, also used by the CLI), `effectivity.report`.
- Golden report and table for `examples/`; the function must equal the CLI.
- CI: web lint, format, typecheck, tests, build, end-to-end with axe, secret
  scan, token and rule-drift checks, Vercel function bundle check, mutation check.

### Changed

- `tools/mutate.py` now covers the function's guards (61 mutants).
- CI actions are pinned by commit and the workflow has least-privilege
  permissions.

## 1.0.0

- First rule version: rules R01 to R10, six states, stable reason codes.
