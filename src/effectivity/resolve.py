"""Pure decision function. No clock, no I/O, no network (ADR 0002).

Rules, ids, and reason codes are defined in docs/state-machine.md; a test
fails if this module and that document disagree.
"""

from __future__ import annotations

from collections.abc import Sequence

from effectivity.model import (
    Change,
    Decision,
    Disposition,
    IncomparableKeysError,
    Incorporation,
    MaterialState,
    Status,
    Unit,
    compare_hold_points,
    key_in_range,
    parse_key,
)

RULE_VERSION = "1.0.0"

# Reason codes (stable strings).
OUT_OF_EFFECTIVITY = "OUT_OF_EFFECTIVITY"
INCORPORATED = "INCORPORATED"
DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR = "DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR"
BLOCKED_REWORK_WRONG_MATERIAL = "BLOCKED_REWORK_WRONG_MATERIAL"
BLOCKED_RETROFIT_WRONG_MATERIAL = "BLOCKED_RETROFIT_WRONG_MATERIAL"
BLOCKED_SCRAP_WRONG_MATERIAL = "BLOCKED_SCRAP_WRONG_MATERIAL"
LATE_HOLD_POINT_PASSED = "LATE_HOLD_POINT_PASSED"
NOT_YET_REACHED_BEFORE_HOLD_POINT = "NOT_YET_REACHED_BEFORE_HOLD_POINT"
NOT_YET_REACHED_PREDECESSOR_OPEN = "NOT_YET_REACHED_PREDECESSOR_OPEN"
INCORPORABLE_REWORK = "INCORPORABLE_REWORK"
INCORPORABLE_RETROFIT = "INCORPORABLE_RETROFIT"
INCORPORABLE_USE_AS_IS_NO_REWORK = "INCORPORABLE_USE_AS_IS_NO_REWORK"
SCRAP_ONLY_NO_INSTALL = "SCRAP_ONLY_NO_INSTALL"

# rule id -> (status it decides, or None for an overlay, reason codes it can emit)
RULE_TABLE: dict[str, tuple[Status | None, tuple[str, ...]]] = {
    "R01": (Status.OUT_OF_EFFECTIVITY, (OUT_OF_EFFECTIVITY,)),
    "R02": (Status.INCORPORATED, (INCORPORATED,)),
    "R03": (None, (DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR,)),
    "R04": (
        Status.BLOCKED_MATERIAL,
        (
            BLOCKED_REWORK_WRONG_MATERIAL,
            BLOCKED_RETROFIT_WRONG_MATERIAL,
            BLOCKED_SCRAP_WRONG_MATERIAL,
        ),
    ),
    "R05": (Status.LATE, (LATE_HOLD_POINT_PASSED,)),
    "R06": (Status.NOT_YET_REACHED, (NOT_YET_REACHED_BEFORE_HOLD_POINT,)),
    "R07": (Status.NOT_YET_REACHED, (NOT_YET_REACHED_PREDECESSOR_OPEN,)),
    "R08": (Status.INCORPORABLE, (INCORPORABLE_REWORK, INCORPORABLE_RETROFIT)),
    "R09": (Status.INCORPORABLE, (INCORPORABLE_USE_AS_IS_NO_REWORK,)),
    "R10": (Status.INCORPORABLE, (SCRAP_ONLY_NO_INSTALL,)),
}

_BLOCKED_BY_DISPOSITION = {
    Disposition.REWORK: BLOCKED_REWORK_WRONG_MATERIAL,
    Disposition.RETROFIT: BLOCKED_RETROFIT_WRONG_MATERIAL,
    Disposition.SCRAP: BLOCKED_SCRAP_WRONG_MATERIAL,
}


def decide_pair(
    unit: Unit,
    change: Change,
    *,
    wrong_material_qty: int,
    incorporation: Incorporation | None,
) -> Decision:
    """Decide one (unit, change) pair.

    `wrong_material_qty` is staged + installed quantity of the change's
    superseded part on this unit. Receipt into stores is not part of it.
    """
    unit_id, change_id = unit.unit_id, change.change_id

    def decision(status: Status, reason: str, *rule_ids: str) -> Decision:
        return Decision(
            unit_id=unit_id,
            change_id=change_id,
            status=status,
            reason_code=reason,
            rule_ids=rule_ids,
        )

    # R01
    if not key_in_range(
        parse_key(unit.effectivity_key),
        parse_key(change.effectivity_from),
        parse_key(change.effectivity_to),
    ):
        return decision(Status.OUT_OF_EFFECTIVITY, OUT_OF_EFFECTIVITY, "R01")

    # R02 / R03
    overlay: tuple[str, ...] = ()
    if incorporation is not None and incorporation.incorporated:
        if unit.predecessor_hold_status == "closed":
            return decision(Status.INCORPORATED, INCORPORATED, "R02")
        overlay = ("R03",)

    def finish(status: Status, reason: str, rule_id: str) -> Decision:
        if overlay:
            reason = DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR
        return decision(status, reason, *overlay, rule_id)

    # R04 (use_as_is is not in the table: it never blocks)
    if wrong_material_qty > 0 and change.disposition in _BLOCKED_BY_DISPOSITION:
        return finish(
            Status.BLOCKED_MATERIAL, _BLOCKED_BY_DISPOSITION[change.disposition], "R04"
        )

    try:
        position = compare_hold_points(
            parse_key(unit.hold_point), parse_key(change.incorporation_hold_point)
        )
    except IncomparableKeysError as exc:
        raise IncomparableKeysError(f"unit {unit_id!r}, change {change_id!r}: {exc}") from exc
    # R05
    if position > 0 or (position == 0 and unit.hold_point_status == "closed"):
        return finish(Status.LATE, LATE_HOLD_POINT_PASSED, "R05")
    # R06
    if position < 0:
        return finish(
            Status.NOT_YET_REACHED, NOT_YET_REACHED_BEFORE_HOLD_POINT, "R06"
        )
    # R07: at the point, open
    if unit.predecessor_hold_status == "open":
        return finish(Status.NOT_YET_REACHED, NOT_YET_REACHED_PREDECESSOR_OPEN, "R07")
    # R08 / R09 / R10: at the point, open, predecessor closed
    if change.disposition is Disposition.REWORK:
        return finish(Status.INCORPORABLE, INCORPORABLE_REWORK, "R08")
    if change.disposition is Disposition.RETROFIT:
        return finish(Status.INCORPORABLE, INCORPORABLE_RETROFIT, "R08")
    if change.disposition is Disposition.USE_AS_IS:
        return finish(Status.INCORPORABLE, INCORPORABLE_USE_AS_IS_NO_REWORK, "R09")
    return finish(Status.INCORPORABLE, SCRAP_ONLY_NO_INSTALL, "R10")


def resolve(
    units: Sequence[Unit],
    changes: Sequence[Change],
    material: Sequence[MaterialState],
    incorporations: Sequence[Incorporation],
) -> tuple[Decision, ...]:
    """Decide every unit x change pair, sorted by (unit_id, change_id)."""
    unit_ids = _unique([u.unit_id for u in units], "unit_id")
    change_ids = _unique([c.change_id for c in changes], "change_id")

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

    decisions = [
        decide_pair(
            unit,
            change,
            wrong_material_qty=wrong_qty.get((unit.unit_id, change.supersedes_part), 0),
            incorporation=incorporation_by_pair.get((unit.unit_id, change.change_id)),
        )
        for unit in units
        for change in changes
    ]
    return tuple(sorted(decisions, key=lambda d: (d.unit_id, d.change_id)))


def _unique(values: list[str], name: str) -> set[str]:
    seen = set(values)
    if len(seen) != len(values):
        raise ValueError(f"duplicate {name} in input")
    return seen
