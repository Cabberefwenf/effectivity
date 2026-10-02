# Limits

What this tool is not, and what it does not prove.

## Scope

- It is not a PLM, MES, or ERP.
- It is not CAD or Teamcenter integration. Inputs are four CSV files.
- Data in this repository is synthetic only. Do not feed it export-controlled
  or customer files.
- No customers, yards, or certifications are claimed. Nothing here has been
  validated against a real program or process.
- A human still signs incorporation. This tool classifies; it does not
  authorize work.

## Key rule

- The effectivity key rule is the one in
  [ADR 0001](docs/adr/0001-effectivity-key.md), not a general hull-number
  parser. Upper-case prefix (0 to 8 letters), 1 to 18 digits, at most one
  upper-case letter. Hyphenated lots, multi-letter suffixes, lower case,
  non-ASCII characters, and date keys are rejected, not interpreted.
- Zero padding is not significant (`0123` equals `123`).
- Ranges cannot span prefixes, and a unit whose prefix differs from the range
  is out of effectivity. Open-ended ranges are not supported; both bounds are
  required.

## What the rules assume

- Hold point order is the token order in ADR 0001. If a program's hold point
  names do not sort in process order, classification will be wrong, and no test
  can detect that. Hold points with different prefixes are an error, not an
  ordering.
- `hold_point` is taken as the latest hold point the unit has reached.
  `predecessor_hold_status` is a single per-unit flag for the hold before that
  one. The tool cannot check either against anything.
- `program` is carried but not used for matching.
- `replacement_part` is carried but never used in a decision. A value on a
  `scrap` or `use_as_is` change is ignored, not rejected.
- Material is matched on exact, case-sensitive string equality of `unit_id` and
  part. Part numbers are printable ASCII with no leading or trailing space, so
  a stray space or look-alike character is an error rather than a silent
  non-match. Wrong material means staged plus installed quantity of the
  superseded part greater than zero. The tool does not compare quantities with
  what the change needs and does not see lot, serial, or revision of the parts.
- The same superseded part named by two changes counts as wrong material for
  both.
- `use_as_is` never looks at material.
- An incorporation record is trusted wherever the unit is: if the predecessor is
  closed it yields `incorporated` even for a unit that has not reached the
  change's hold point. A record on a unit outside the change's effectivity is
  hidden by the out-of-effectivity rule and not reported.
- A unit past the incorporation hold point is `late` even if its current
  `predecessor_hold_status` is open; the flag is only consulted for
  `incorporated` and for units at the point.
- An incorporation record that contradicts an open predecessor is reported with
  a data-error reason code; the status is whatever the remaining rules decide.
  That reason code replaces the disposition-specific one, so a rework and a
  retrofit in this situation show the same reason code (the determining rule is
  in `rule_ids`).
- Results sort by plain string order of `unit_id` then `change_id`
  (`U-10` sorts before `U-2`).

## Invariants not fully encoded as tests

- Invariant 7 (no clock, no network): enforced by a static import allowlist and
  call check on `resolve.py` and `model.py`, plus a run with `time`, `socket`,
  and `open` patched to raise, plus subprocess runs under different hash seeds,
  time zones, locales, and working directories. It is not a proof that imported
  third-party code (pydantic) makes no such calls.
- Invariant 6 (log is append-only): the module only appends, builds the whole
  line first, and writes it with one write; tests show prior bytes unchanged
  after a rerun and no change after a failed write. A crash or power loss
  mid-write can still leave a partial line (the next run then refuses to
  append). The sequence number is derived by reading the file first, so
  concurrent writers are not safe. The log is not tamper-evident (no hash chain,
  no signature), and anyone can edit the file.
- Hold point ordering depends on the ADR 0001 naming convention; tests check the
  rule, not whether a real program follows it.
- Rule/doc agreement is tested for rule ids, statuses, and reason codes, not for
  the wording of the conditions in `docs/state-machine.md`.
- The exhaustive test covers a small, hand-chosen domain (24,000 combinations),
  not all inputs. The independent reference was written by the same author as
  the implementation from the same document, so a misreading of the document
  would be in both.
- `tools/mutate.py` applies hand-picked mutants. Killing all of them shows the
  tests notice those changes; it is not a coverage measure.
- CI runs the suite on Python 3.11 and 3.12 only.
