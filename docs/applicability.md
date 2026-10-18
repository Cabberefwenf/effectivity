# Applicability and conflicts (extended pipeline)

ADR 0004. This is the spec for the extended pipeline. The core resolver
(R01 to R10, six states) is specified in
[docs/state-machine.md](state-machine.md) and is unchanged by anything
here.

## Order

1. Read the four core tables, plus the optional applicability and
   supersession tables.
2. Run the core resolver on every (unit, change) pair.
3. Drop pairs applicability excludes. Excluded pairs are listed, not
   silently hidden.
4. Group the remaining live decisions by slot and report conflicts.
   A conflict BLOCKs the run; it never picks a winner.

## Applicability

Applicability answers "does this change concern this unit at all".
Effectivity (R01) answers "is this unit inside this change's range". A
pair must pass both.

### Input table

`applicability.csv`, columns exactly:

```
change_id,program,applies
```

- `change_id`: must name a known change.
- `program`: must name a program some unit has, or `*` for every program.
- `applies`: exactly `true` or `false`. `True`, `1`, `yes`, and empty
  are errors, same as `incorporated` in the core tables.

Rules:

- Duplicate (change_id, program) rows are errors. Two rows saying
  different things about the same pair would need a tie-break, and this
  system never breaks ties silently.
- A rule naming an unknown change or an unknown program is an error.
- A header-only file is valid and means no rules: everything applies.

### Rules

| id | condition | effect |
|---|---|---|
| A01 | An explicit rule names this (change, program) | That rule decides: applies or excluded |
| A02 | No explicit rule, but a wildcard rule names this change for `*` | The wildcard rule decides |
| A03 | No rule names this change for this program | The change applies by default |

A01 beats A02 for its program. A02 covers every program the change has
no explicit rule for.

## Conflicts (exactly-one-match)

A slot is (unit, superseded part). Group the live decisions by slot.

Live means the decision still claims work: `not_yet_reached`,
`incorporable`, `late`, `blocked_material`. `out_of_effectivity` claims
nothing for this unit. `incorporated` is history, not a claim, which is
what makes supersession usable: when an old change is incorporated and
its replacement is live, the replacement is the one live change, so
there is no conflict.

`use_as_is` changes claim no slot (they supersede nothing) and never
conflict. Two changes for different superseded parts are different slots
and never conflict.

| id | condition | verdict | reason code |
|---|---|---|---|
| C01 | More than one live change on a slot, no supersession edge among them | BLOCKED | BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES |
| C02 | More than one live change on a slot, with a supersession edge among them | BLOCKED | BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED |

C02 exists because a supersession declaration is evidence, not proof.
If the superseded change is still live, the slot is still blocked. Only
an incorporated record proves the old change is done.

### Supersession input table

`supersession.csv`, columns exactly:

```
change_id,supersedes_change_id
```

`change_id` replaces `supersedes_change_id`. Validation:

- Both ends must name known changes.
- A change cannot supersede itself.
- The same edge twice is an error.
- Cycles are errors.
- Both ends must claim the same superseded part: supersession is about
  one slot.
- An edge involving a `use_as_is` change is an error: it claims no slot.

## Report

`--extended-report PATH` writes JSON:

- `pipeline_version`, `rule_version`, `applicability_version`,
  `conflict_version`.
- `input_hash`: the core hash over the four tables, identical to the
  core run log, so an extended run stays linked to its core run.
- `extended_input_hash`: also covers the applicability and supersession
  tables, so two runs with different applicability rules never share a
  hash.
- `applicability`: the rules given, and the excluded pairs with the
  rule that excluded each one.
- `decisions`: the kept decisions, in core order.
- `conflicts`: each conflict with its competing changes (each carrying
  its core decision) and its supersession edges.
- `blocked`: true when any conflict exists.

## Worked example

`examples/applicability/` carries a small dataset: three units in two
programs, five changes, one applicability rule (`C-X2` does not apply to
program `Q`), one supersession edge (`C-X2` replaces `C-X1`). Every unit
sits open at the incorporation hold point, so every applicable change
is incorporable and every shared slot conflicts.

```
python -m effectivity --units examples/applicability/units.csv \
  --changes examples/applicability/changes.csv \
  --material examples/applicability/material.csv \
  --incorporations examples/applicability/incorporations.csv \
  --applicability examples/applicability/applicability.csv \
  --supersession examples/applicability/supersession.csv
```

Output (exit code 3, BLOCKED):

```
unit_id  change_id  status        reason_code                       rule_ids
-------  ---------  ------------  --------------------------------  --------
U-X1     C-X1       incorporable  INCORPORABLE_REWORK               R08
U-X1     C-X2       incorporable  INCORPORABLE_RETROFIT             R08
U-X1     C-X3       incorporable  INCORPORABLE_USE_AS_IS_NO_REWORK  R09
U-X1     C-X4       incorporable  INCORPORABLE_REWORK               R08
U-X1     C-X5       incorporable  INCORPORABLE_RETROFIT             R08
U-X2     C-X1       incorporable  INCORPORABLE_REWORK               R08
U-X2     C-X2       incorporable  INCORPORABLE_RETROFIT             R08
U-X2     C-X3       incorporable  INCORPORABLE_USE_AS_IS_NO_REWORK  R09
U-X2     C-X4       incorporable  INCORPORABLE_REWORK               R08
U-X2     C-X5       incorporable  INCORPORABLE_RETROFIT             R08
U-Y1     C-X1       incorporable  INCORPORABLE_REWORK               R08
U-Y1     C-X3       incorporable  INCORPORABLE_USE_AS_IS_NO_REWORK  R09
U-Y1     C-X4       incorporable  INCORPORABLE_REWORK               R08
U-Y1     C-X5       incorporable  INCORPORABLE_RETROFIT             R08

rule_version 1.0.0

state               count
out_of_effectivity      0
not_yet_reached         0
incorporable           14
late                    0
blocked_material        0
incorporated            0
total                  14

applicability: 1 pair(s) excluded by 1 rule(s)
  U-Y1 C-X2 excluded (A01): change C-X2 does not apply to program Q
conflicts: 5 slot(s) BLOCKED
  U-X1 PN-9000 BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED (C02): C-X1, C-X2
  U-X1 PN-9200 BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES (C01): C-X4, C-X5
  U-X2 PN-9000 BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED (C02): C-X1, C-X2
  U-X2 PN-9200 BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES (C01): C-X4, C-X5
  U-Y1 PN-9200 BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES (C01): C-X4, C-X5
```

Read it as: `U-Y1` escapes the `PN-9000` conflict because `C-X2` does
not apply to program `Q` (A01), leaving `C-X1` the only live change on
that slot. `U-X1` and `U-X2` stay BLOCKED on `PN-9000` even though
`C-X2` is declared to replace `C-X1` (C02): the declaration does not
prove `C-X1` is done. Nothing on `PN-9200` is superseded, so those
slots are C01. To clear a slot, dispose of the loser: incorporate it,
withdraw the change, or narrow its range or applicability, then re-run.
