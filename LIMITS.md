# Limits

What this tool is not, and what it does not prove.

## Scope

- It is not a PLM, MES, or ERP.
- It has no CAD or Teamcenter integration. Inputs are four CSV files.
- Data in this repository is synthetic only. Do not feed it export-controlled
  or customer files.
- No customers, yards, or certifications are claimed. Nothing here has been
  validated against a real program.
- A human still signs incorporation. This tool classifies; it does not
  authorize work.

## Key rule

- The effectivity key rule is the one in
  [ADR 0001](docs/adr/0001-effectivity-key.md), not a general hull-number
  parser. Upper-case prefix (0 to 8 letters), digits, at most one upper-case
  letter. Hyphenated lots, multi-letter suffixes, lower case, and date keys are
  rejected, not interpreted.
- Zero padding is not significant (`0123` equals `123`).
- Effectivity ranges cannot span prefixes, and a unit with a different prefix
  than the range is out of effectivity.
- Open-ended ranges are not supported; both bounds are required.

## What the rules assume

- Hold point order is the token order in ADR 0001. If a program's hold point
  names do not sort in process order, classification will be wrong, and no test
  can detect that. Hold points with different prefixes are an error, not an
  ordering.
- `hold_point` is taken as the latest hold point the unit has reached.
  `predecessor_hold_status` is a single per-unit flag for the hold before that
  one. The tool cannot check it against anything.
- `program` is carried but not used for matching.
- `replacement_part` is carried but never used in a decision.
- Material is matched on exact string equality of `unit_id` and part
  (case-sensitive, no normalization). Wrong material means staged plus
  installed quantity of the superseded part greater than zero. It does not
  look at quantities against what the change requires, lot or serial of the
  parts, or whether the staged material is actually the one being replaced
  beyond the part string.
- `use_as_is` never looks at material.
- A unit past the incorporation hold point is `late` even if its current
  `predecessor_hold_status` is open; the flag is only consulted for
  `incorporated` and for units at the point.
- An incorporation record that contradicts an open predecessor is reported as a
  data error reason code; the status is whatever the remaining rules decide.
  The tool does not repair or reject the record.
- Results sort by plain string order of `unit_id` then `change_id`
  (`U-10` sorts before `U-2`).

## Invariants that are not fully encoded as tests

- Invariant 7 (no clock, no network): enforced by a static import allowlist
  and call check on `resolve.py` and `model.py`, plus a run with
  `time`, `socket`, and `open` patched to raise. It is not a proof that
  imported third-party code (pydantic) makes no such calls.
- Invariant 6 (log is append-only): the module only opens the file in append
  mode and tests show prior bytes unchanged after a rerun. The file system is
  not prevented from being edited by someone else. The sequence number is
  derived by reading the file first, so concurrent writers are not safe. The
  log is not tamper-evident (no hash chain).
- Hold point ordering depends on the ADR 0001 naming convention (see above);
  tests check the rule, not whether a real program follows it.
- Rule/doc agreement is tested for rule ids, statuses, and reason codes, not
  for the wording of the conditions in `docs/state-machine.md`.
