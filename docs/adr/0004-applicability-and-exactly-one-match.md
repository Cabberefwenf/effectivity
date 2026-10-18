# ADR 0004: Applicability first, exactly-one-match conflicts

Status: Accepted (core rule version still 1.0.0; core decisions unchanged)

## Context

The core resolver answers one question per (unit, change) pair: given the
unit's effectivity key, hold position, material, and incorporation record,
which of six states applies. Two questions sit outside it, and users kept
needing both:

1. **Applicability.** `program` was carried on the unit but never used for
   matching. A change written for one program was evaluated for every
   unit in range, including units of programs it was never meant for. In
   configuration management, applicability ("does this change concern
   this unit at all") comes before effectivity ("is this unit inside the
   change's range"). The tool had only the second half.
2. **Competing changes.** Two changes can claim the same slot: the same
   unit, the same superseded part, both live. The core resolver reports
   both, correctly, as separate decisions. But a shop floor handed two
   live changes for one slot needs one answer: which one do I build? The
   worst answer a tool can give there is a silent one, picking the
   newest, the highest revision, or the first row and hiding that a
   choice was made.

## Decision

- **Applicability first.** An optional applicability table
  (`change_id, program, applies`) filters pairs before anything else.
  An explicit rule for a program decides for that program (A01); a
  wildcard rule for `*` decides for programs with no explicit rule (A02);
  a change with no rule applies by default (A03). Excluded pairs are
  listed in the report with the rule that excluded them. Full spec:
  [docs/applicability.md](../applicability.md).
- **Exactly-one-match, else BLOCKED.** After the core pass, live
  decisions are grouped by slot (unit, superseded part). Live means
  `not_yet_reached`, `incorporable`, `late`, or `blocked_material`.
  `out_of_effectivity` claims nothing; `incorporated` is history, not a
  claim. A slot with exactly one live change is fine. A slot with more
  than one is BLOCKED: the run names every competing change and exits 3.
  Never latest-wins, never highest-revision-wins, never first-row-wins.
- **Supersession is evidence, not a tie-break.** An optional supersession
  table may declare that one change replaces another. If the superseded
  change is still live, the slot is still BLOCKED (C02), because the
  declaration alone does not prove the old change is done. Only an
  incorporated record proves that, and incorporated decisions are not
  live. A conflict with no supersession edge is C01.
- **The core is untouched.** R01 to R10, the six states, `RULE_VERSION`
  1.0.0, the log format, the golden files, and the web function are all
  unchanged. The extended pipeline is a separate layer
  (`effectivity/applicability.py`, `effectivity/conflicts.py`,
  `effectivity/pipeline.py`) that filters pairs, calls the core resolver,
  and groups its decisions. It has its own versions
  (`APPLICABILITY_VERSION`, `CONFLICT_VERSION`, `PIPELINE_VERSION`) and
  its own report, with an extended input hash that also covers the two
  optional tables.

## Alternatives considered

- **Latest-wins.** Rejected. Picking the newest change hides the fact
  that two live changes claim one slot, which is exactly the condition
  that causes wrong parts to be installed. A human must dispose of the
  loser: incorporate it, withdraw it, or narrow its range. The tool
  reports the conflict; it does not resolve it.
- **Auto-supersede.** Rejected for the same reason. A supersession row
  is a claim about intent; treating it as proof would let a typo retire
  a live change.
- **A seventh status for conflicts.** Rejected. The six-state invariant
  is load-bearing: tests, the log format, the golden files, and the web
  schema all assume exactly six. A conflict is a property of a run, not
  of one pair, so it belongs in its own report section with its own
  verdict, not in the per-pair taxonomy.
- **Applicability as a column on the changes table.** Rejected. It would
  change the four-table contract, break every existing CSV and the
  golden files, and force one applicability value per change instead of
  one per (change, program).

## Consequences

- Extended runs exit 3 when any slot is BLOCKED. CI and scripts must
  treat 3 as "blocked", not as success and not as a crash.
- `--log` still records the core run over the four tables. The extended
  report (`--extended-report`) is the record of the extended run,
  including its extended input hash. The two are linked by the shared
  core `input_hash`.
- The web function does not run the extended pipeline. It serves the
  core resolver only; the extended pipeline is CLI-only for now.
- The conflict pass is not part of the core invariants. It is covered by
  its own tests and mutants instead.
