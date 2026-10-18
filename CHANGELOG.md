# Changelog

Rule changes are recorded here with their rule version. Everything else is
listed under the date of the change.

## Unreleased

### Added

- Extended pipeline (ADR 0004, CLI-only): applicability first
  (`effectivity/applicability.py`, rules A01 to A03, optional
  `change_id, program, applies` table with `*` wildcard), then the core
  resolver, then the exactly-one-match conflict pass
  (`effectivity/conflicts.py`, rules C01/C02). Two live changes on one
  slot (same unit, same superseded part) BLOCK the run with exit code 3;
  never latest-wins. An optional supersession table is evidence, not a
  tie-break. `--extended-report` writes the full report with an extended
  input hash. Core decisions, `RULE_VERSION` 1.0.0, the log format, the
  golden files, and the web function are unchanged.
- Decision traces (ADR 0005): `effectivity/trace.py`, one trace per
  pair with one step per rule and the values observed; `--trace` writes
  JSONL. The decision always comes from `decide_pair`.
- Log verification (ADR 0005): `effectivity/verify.py`,
  `--verify-log PATH`, exit 0 clean / 3 problems / 2 missing file.
  Checks shape, sequence, counts, order, and hash format; does not
  recompute decisions and does not make the log tamper-evident.
- Log backup: `tools/backup_log.py` copies a log to a content-hash name
  with a sha256 manifest; same content twice is a no-op, changed content
  writes a new file, and the copy is hashed after writing.
- Docs: ADR 0004, ADR 0005, `docs/applicability.md` (spec plus worked
  example), `docs/standards.md` (ISO 10007, SAE/EIA-649C, AP242 mapping
  with sources; design rationale, not a compliance claim),
  `examples/applicability/` dataset. `docs/state-machine.md` gains a
  pointer to the extensions; its rule table is unchanged.
- Web surface (ADR 0003): Next.js shell and one stateless Python function
  (`api/resolve.py`) over the existing resolver. Rule version unchanged
  (1.0.0); decisions unchanged.
- `effectivity.service` (request handling and caps), `effectivity.tables`
  (shared CSV text parser, also used by the CLI), `effectivity.report`.
- Golden report and table for `examples/`; the function must equal the CLI.
- CI: web lint, format, typecheck, tests, build, end-to-end with axe, secret
  scan, token and rule-drift checks, Vercel function bundle check, mutation check.

### Changed

- `program` is still unused by the core resolver; the extended pipeline
  uses it for applicability. LIMITS says so now.
- `tools/mutate.py` now covers the function's guards and the new layers
  (68 mutants).
- CI actions are pinned by commit and the workflow has least-privilege
  permissions.

## 1.0.0

- First rule version: rules R01 to R10, six states, stable reason codes.
