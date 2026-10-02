# Changelog

Rule changes are recorded here with their rule version. Everything else is
listed under the date of the change.

## Unreleased

### Added

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
