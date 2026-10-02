# Working on effectivity

- **One resolver.** All decision logic lives in `src/effectivity/resolve.py`.
  Do not add a second implementation in TypeScript or anywhere else. The web
  page only displays what `api/resolve.py` returns.
- **A decision change is a rule change.** Edit `docs/state-machine.md`, bump
  `RULE_VERSION`, update the tests and `tests/golden/*`, and run
  `npm run gen:rules`. Without a change to decisions, `RULE_VERSION` stays.
- **No clock, network, file system, logging or randomness** in `resolve.py`,
  `model.py`, `service.py`, `report.py` or `tables.py`. Tests enforce the import
  allowlists; do not widen them to make something pass.
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
