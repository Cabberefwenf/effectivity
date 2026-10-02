# effectivity

A deterministic as-built effectivity resolver: for every unit and every
engineering change, it decides whether the change is out of effectivity, not yet
reached, incorporable, late, blocked on issued-but-wrong material, or already
incorporated.

```
A change order is not a BOM diff.
It is a claim about which units it applies to,
whether work has already passed the incorporation point,
and whether material already issued is now wrong.
```

Spreadsheets lose this because effectivity, as-built progress, and stores state
live in different places and disagree.

## The six states

| state | meaning |
|---|---|
| `out_of_effectivity` | the unit is not in the change's effectivity range |
| `not_yet_reached` | the unit has not arrived at the incorporation hold point (or has not cleared the hold before it) |
| `incorporable` | the unit is at the incorporation hold point, predecessor closed, nothing blocking |
| `late` | the unit has passed the incorporation hold point and the change is not incorporated |
| `blocked_material` | superseded material is already staged at the work or installed |
| `incorporated` | an incorporation record exists and the predecessor hold is closed |

Exactly these six. Each decision carries the unit id, change id, status, a
stable reason code, and the ids of the rules that fired. The full decision
table is in [docs/state-machine.md](docs/state-machine.md).

## Worked example: the sheet says go, the tool says blocked

Synthetic data from `examples/`. Change `C-1002` is a retrofit of part
`PN-2200` for units `0122` to `0124`, incorporated at hold point `HP030`.
Suppose a tracking sheet shows `C-1002` released for those units. Unit
`U-A02` (hull `0122`) is sitting open at `HP030`, the predecessor hold is
closed, and stores shows 8 of `PN-2200` received. On paper it is ready.

```
units.csv      U-A02,ALPHA,0122,HP030,open,closed
changes.csv    C-1002,0122,0124,HP030,retrofit,PN-2200,PN-2201
material.csv   U-A02,PN-2200,8,0,0      <- received into stores
               U-A02,PN-2200,0,4,0      <- 4 staged at the work
```

The received quantity does not matter. The 4 staged at the work do: they are
the superseded part, already at the point of use.

```
unit_id  change_id  status            reason_code                      rule_ids
U-A02    C-1002     blocked_material  BLOCKED_RETROFIT_WRONG_MATERIAL  R04
```

Remove the 4 staged and the same unit is `incorporable`. Receipt into stores
alone never blocks.

## Run it

```
make demo     # classify examples/ and print every decision plus a count per state
make test     # run the test suite
```

Both create `.venv` on first use. The CLI directly:

```
python -m effectivity --units examples/units.csv --changes examples/changes.csv \
  --material examples/material.csv --incorporations examples/incorporations.csv \
  [--log run-log.jsonl] [--run-at LABEL]
```

`--log` appends one JSON line per run (sequence, rule version, input hash,
counts, decisions); earlier lines are never rewritten. `--run-at` is an
optional label you supply; nothing in the tool reads a clock.

## Where to look

- [LIMITS.md](LIMITS.md): what this is not, and what is not proven.
- [docs/state-machine.md](docs/state-machine.md): the rules, written before the code.
- [docs/adr/0001-effectivity-key.md](docs/adr/0001-effectivity-key.md): how keys and hold points are ordered.
- [docs/adr/0002-no-clock-in-decision.md](docs/adr/0002-no-clock-in-decision.md): why the decision function is pure.
- `tests/`: one file per invariant family; they are the credibility.
