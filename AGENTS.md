# Working on effectivity

- **One resolver.** All decision logic lives in `src/effectivity/resolve.py`.
  Do not add a second implementation in TypeScript or anywhere else. The web
  page only displays what `api/resolve.py` returns. The extended pipeline
  (`applicability.py`, `conflicts.py`, `pipeline.py`) filters pairs and
  groups decisions; it never re-decides a pair.
- **A decision change is a rule change.** Edit `docs/state-machine.md`, bump
  `RULE_VERSION`, update the tests and `tests/golden/*`, and run
  `npm run gen:rules`. Without a change to decisions, `RULE_VERSION` stays.
  New rule ids use `A` (applicability) and `C` (conflict) prefixes so the
  `R`-rule generator and doc/code checks keep working.
- **No clock, network, file system, logging or randomness** in `resolve.py`,
  `model.py`, `service.py`, `report.py` or `tables.py`. Tests enforce the import
  allowlists; do not widen them to make something pass. The new
  `applicability.py`, `conflicts.py`, `pipeline.py`, and `trace.py` follow
  the same rule. `verify.py` reads log files (it is the audit layer, like
  `log.py`); `tools/backup_log.py` is a script, not package code.
- **Request bodies are never stored or logged.** No `print`, `logging`,
  telemetry or error reporter that could see a body.
- **Caps live in two places** (`service.py`, `lib/limits.ts`). Change both; a
  test compares them.
- **Colours are tokens.** No raw hex or `rgb()` outside `app/globals.css` and the
  image routes (`npm run check:tokens`). Status is never colour alone.
- **Copy:** plain, no em dashes, no claims about customers or results, and
  the banner sentence stays exact.
- **Commits:** `type(scope): subject` (feat, fix, docs, test, ci, chore).
- **Before pushing:** `make test`, `make mutate`, `npm run verify`,
  `npm run test:e2e`.
