# State machine

Rule version: `1.0.0` (`effectivity.resolve.RULE_VERSION`). This document is
written first; the implementation must match it, and a test fails if the rule
ids, statuses, or reason codes below drift from the code.

Every (unit, change) pair is evaluated. Output is sorted by `unit_id`, then
`change_id`. Each decision carries: `unit_id`, `change_id`, `status`,
`reason_code`, `rule_ids`.

## Statuses

Exactly six, no others:
`out_of_effectivity`, `not_yet_reached`, `incorporable`, `late`,
`blocked_material`, `incorporated`.

## Input semantics (design choices that are not obvious from the column names)

- **Effectivity**: inclusive range on the ordered key defined in
  [ADR 0001](adr/0001-effectivity-key.md).
- **Hold position**: the unit's `hold_point` is the latest hold point reached;
  `hold_point_status` says whether it is still open there. Compared with the
  change's `incorporation_hold_point` using the same ordering (ADR 0001):
  `<` not arrived; `==` and open: at the point; `==` and closed: passed;
  `>` passed.
- **`predecessor_hold_status`** is the status of the hold point immediately
  before the unit's recorded `hold_point`. It is a per-unit flag; there is no
  hold point table to look it up in.
- **Wrong material** for a pair = the sum, over all material rows with
  `unit_id == unit` and `part == change.supersedes_part` (exact string match),
  of `qty_staged_at_work + qty_installed`. Wrong material exists when the sum
  is `> 0`. `qty_received_to_stores` is never counted: material in stores is
  not material at the work.
- **Incorporation record**: at most one row per (unit, change). A row with
  `incorporated = false` means "not incorporated", same as no row.
- **`replacement_part`** is carried but never read by the resolver. For `scrap`
  it is ignored by definition.
- **`program`** is carried but not used for matching.
- **`use_as_is`** never looks at material.

## Decision order

First terminal match wins. R03 is not terminal: it annotates and evaluation
continues.

| id | condition | status | reason code(s) |
|---|---|---|---|
| R01 | Unit key is outside the change's inclusive range (or has a different prefix) | `out_of_effectivity` | `OUT_OF_EFFECTIVITY` |
| R02 | Incorporation record says incorporated and `predecessor_hold_status` is closed | `incorporated` | `INCORPORATED` |
| R03 | Incorporation record says incorporated but `predecessor_hold_status` is open (data error). Never yields `incorporated`. Evaluation continues at R04; the final reason code is replaced by this one and R03 is listed first in `rule_ids` | (none, overlay) | `DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR` |
| R04 | Disposition is `rework`, `retrofit`, or `scrap`, and wrong material > 0 | `blocked_material` | `BLOCKED_REWORK_WRONG_MATERIAL`, `BLOCKED_RETROFIT_WRONG_MATERIAL`, `BLOCKED_SCRAP_WRONG_MATERIAL` |
| R05 | Unit has passed the incorporation hold point (and R02/R04 did not match) | `late` | `LATE_HOLD_POINT_PASSED` |
| R06 | Unit hold point is before the incorporation hold point | `not_yet_reached` | `NOT_YET_REACHED_BEFORE_HOLD_POINT` |
| R07 | Unit is at the incorporation hold point (open) and `predecessor_hold_status` is open | `not_yet_reached` | `NOT_YET_REACHED_PREDECESSOR_OPEN` |
| R08 | At the point (open), predecessor closed, not blocked, disposition `rework` or `retrofit` | `incorporable` | `INCORPORABLE_REWORK`, `INCORPORABLE_RETROFIT` |
| R09 | At the point (open), predecessor closed, disposition `use_as_is` | `incorporable` | `INCORPORABLE_USE_AS_IS_NO_REWORK` |
| R10 | At the point (open), predecessor closed, disposition `scrap`, no superseded material staged or installed | `incorporable` | `SCRAP_ONLY_NO_INSTALL` |

Notes:

- R04 before R05 is invariant 3: wrong material staged or installed outranks
  lateness.
- R04 does not depend on hold position. Wrong material at the work blocks even
  a unit that has not yet arrived at the incorporation hold point.
- `use_as_is` skips R04 entirely, so it can never be `blocked_material`.
- `scrap` and `incorporable`: this means "the scrap-only action may be
  taken". It is never an install recommendation. No scrap decision ever carries
  an install-recommending reason code, and `replacement_part` plays no part.
- `rework` and `retrofit` keep separate reason codes in R04 and R08. They are
  different dispositions and are never collapsed.
- R05 applies to `use_as_is` too: a unit past the hold point with no
  incorporation record is `late` whatever the disposition.
- R05 is evaluated on hold position alone. A unit past the incorporation hold
  point whose current `predecessor_hold_status` is open is still `late`; the
  predecessor flag only gates R02 (incorporated) and R07 (at the point).

## Data error handling (R03)

An incorporations row with `incorporated = true` on a unit whose
`predecessor_hold_status` is open is contradictory: invariant 2 says that
change cannot be incorporated there. The resolver does not return
`incorporated`. Because only six statuses exist, it falls through to R04..R10
and the status is whatever those rules decide. The reason code is
`DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR` and `rule_ids` is
`[R03, <determining rule>]`. The data-error reason code overrides the
determining rule's own reason code, so the problem stays visible in the output.
R03 is never reached for a pair already settled by R01.

## Inputs that stop the run instead of producing a decision

These raise errors; they are not decisions:

- malformed key, hold point, or range (ADR 0001);
- duplicate `unit_id` in units, duplicate `change_id` in changes, duplicate
  (`unit_id`, `change_id`) in incorporations;
- incorporation row naming an unknown unit or change; material row naming an
  unknown unit;
- hold points with different prefixes compared for an in-effectivity pair;
- negative quantities, unknown enum values, missing or extra CSV columns,
  `incorporated` not literally `true` or `false`.

## Invariants and where they are tested

| # | invariant | rule(s) | test file |
|---|---|---|---|
| 1 | Outside range is always `out_of_effectivity` | R01 | `test_invariants.py` |
| 2 | Open predecessor never yields `incorporated` | R02, R03 | `test_invariants.py` |
| 3 | Passed hold point, not incorporated: `late`, unless blocked | R04, R05 | `test_invariants.py` |
| 4 | Receipt to stores alone never blocks | R04 | `test_material.py` |
| 5 | Disposition semantics (scrap, use_as_is, rework vs retrofit) | R04, R08-R10 | `test_dispositions.py` |
| 6 | Deterministic; append-only log with input hash and rule version | all | `test_invariants.py`, `test_log.py` |
| 7 | No clock, no network, no I/O in the decision function | all | `test_invariants.py` (static import and call check) |
