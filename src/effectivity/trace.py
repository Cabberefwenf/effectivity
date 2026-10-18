"""Per-pair decision traces: why a decision came out the way it did.

ADR 0005. The decision in every trace comes from ``decide_pair``; the trace
only explains it. Each step records one rule, whether it was evaluated,
whether it matched, and the values observed when it was checked. A reader
can replay the trace against the inputs without trusting the code: the
observed values are the raw inputs to each predicate, and the matched
flags follow the returned ``rule_ids`` exactly (R03 is an overlay, so it
can match alongside the terminal rule).

A trace is evidence, not a second decision function. Nothing here
re-implements R01 to R10; the predicates (``key_in_range``,
``compare_hold_points``) are the same helpers the resolver uses.

No clock, no network, no randomness. Pure functions of parsed models.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from effectivity.model import (
    Change,
    Incorporation,
    IncomparableKeysError,
    MaterialState,
    Unit,
    compare_hold_points,
    key_in_range,
    parse_key,
)
from effectivity.resolve import decide_pair

_RULES = ("R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10")


def trace_pair(
    unit: Unit,
    change: Change,
    *,
    wrong_material_qty: int,
    incorporation: Incorporation | None,
) -> dict[str, Any]:
    """Trace one (unit, change) pair. Raises exactly when ``decide_pair`` raises."""

    decision = decide_pair(
        unit, change, wrong_material_qty=wrong_material_qty, incorporation=incorporation
    )
    rule_ids = decision.rule_ids
    terminal = rule_ids[-1]
    after_r01 = "R01" not in rule_ids
    after_r02 = after_r01 and "R02" not in rule_ids
    in_range = key_in_range(
        parse_key(unit.effectivity_key),
        parse_key(change.effectivity_from),
        parse_key(change.effectivity_to),
    )
    position: int | str | None = None
    if after_r01:
        try:
            position = compare_hold_points(
                parse_key(unit.hold_point), parse_key(change.incorporation_hold_point)
            )
        except IncomparableKeysError:
            # The decision never reached a rule that compares hold points
            # (it stopped at R02), so the trace reports the comparison as
            # not made instead of failing where the resolver succeeded.
            position = "incomparable"
    incorporation_seen = "none" if incorporation is None else str(incorporation.incorporated).lower()
    observed: dict[str, dict[str, Any]] = {
        "R01": {
            "unit_key": unit.effectivity_key,
            "effectivity_from": change.effectivity_from,
            "effectivity_to": change.effectivity_to,
            "in_range": in_range,
        },
        "R02": {
            "incorporation": incorporation_seen,
            "predecessor_hold_status": unit.predecessor_hold_status,
        },
        "R03": {
            "incorporation": incorporation_seen,
            "predecessor_hold_status": unit.predecessor_hold_status,
        },
        "R04": {"wrong_material_qty": wrong_material_qty, "disposition": change.disposition.value},
        "R05": {
            "hold_point": unit.hold_point,
            "incorporation_hold_point": change.incorporation_hold_point,
            "position": position,
            "hold_point_status": unit.hold_point_status,
        },
        "R06": {
            "hold_point": unit.hold_point,
            "incorporation_hold_point": change.incorporation_hold_point,
            "position": position,
        },
        "R07": {"predecessor_hold_status": unit.predecessor_hold_status},
        "R08": {"disposition": change.disposition.value},
        "R09": {"disposition": change.disposition.value},
        "R10": {"disposition": change.disposition.value},
    }
    evaluated = {
        "R01": True,
        "R02": after_r01,
        "R03": after_r01,
        "R04": after_r02,
        "R05": after_r02,
        "R06": after_r02,
        "R07": after_r02,
        "R08": after_r02,
        "R09": after_r02,
        "R10": after_r02,
    }
    steps = []
    for rule in _RULES:
        if rule == "R03":
            matched = "R03" in rule_ids
        else:
            matched = terminal == rule
        steps.append(
            {"rule": rule, "evaluated": evaluated[rule], "matched": matched,
             "observed": observed[rule]}
        )
    return {
        "unit_id": unit.unit_id,
        "change_id": change.change_id,
        "decision": decision.model_dump(mode="json"),
        "steps": steps,
    }


def _aggregate(
    units: Sequence[Unit],
    changes: Sequence[Change],
    material: Sequence[MaterialState],
    incorporations: Sequence[Incorporation],
) -> tuple[dict[tuple[str, str], Incorporation], dict[tuple[str, str], int]]:
    """The same input aggregation ``resolve`` performs, with the same errors."""

    unit_ids = set()
    for unit in units:
        if unit.unit_id in unit_ids:
            raise ValueError(f"duplicate unit_id in input")
        unit_ids.add(unit.unit_id)
    change_ids = set()
    for change in changes:
        if change.change_id in change_ids:
            raise ValueError(f"duplicate change_id in input")
        change_ids.add(change.change_id)
    incorporation_by_pair: dict[tuple[str, str], Incorporation] = {}
    for record in incorporations:
        if record.unit_id not in unit_ids:
            raise ValueError(f"incorporation names unknown unit {record.unit_id!r}")
        if record.change_id not in change_ids:
            raise ValueError(f"incorporation names unknown change {record.change_id!r}")
        pair = (record.unit_id, record.change_id)
        if pair in incorporation_by_pair:
            raise ValueError(f"duplicate incorporation row for {pair!r}")
        incorporation_by_pair[pair] = record
    wrong_qty: dict[tuple[str, str], int] = {}
    for row in material:
        if row.unit_id not in unit_ids:
            raise ValueError(f"material row names unknown unit {row.unit_id!r}")
        key = (row.unit_id, row.part)
        wrong_qty[key] = wrong_qty.get(key, 0) + row.qty_staged_at_work + row.qty_installed
    return incorporation_by_pair, wrong_qty


def trace_selected(
    units: Sequence[Unit],
    changes: Sequence[Change],
    material: Sequence[MaterialState],
    incorporations: Sequence[Incorporation],
    pairs: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Trace exactly the given (unit_id, change_id) pairs, sorted."""

    incorporation_by_pair, wrong_qty = _aggregate(units, changes, material, incorporations)
    traces = [
        trace_pair(
            unit,
            change,
            wrong_material_qty=wrong_qty.get((unit.unit_id, change.supersedes_part), 0),
            incorporation=incorporation_by_pair.get((unit.unit_id, change.change_id)),
        )
        for unit in units
        for change in changes
        if (unit.unit_id, change.change_id) in pairs
    ]
    return sorted(traces, key=lambda t: (t["unit_id"], t["change_id"]))


def trace_all(
    units: Sequence[Unit],
    changes: Sequence[Change],
    material: Sequence[MaterialState],
    incorporations: Sequence[Incorporation],
) -> list[dict[str, Any]]:
    """Trace every (unit, change) pair, sorted by (unit_id, change_id)."""

    pairs = {(u.unit_id, c.change_id) for u in units for c in changes}
    return trace_selected(units, changes, material, incorporations, pairs)
