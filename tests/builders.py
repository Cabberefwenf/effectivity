"""Small factories so each test states only the fields it cares about."""

from __future__ import annotations

from effectivity.model import Change, Incorporation, MaterialState, Unit

# Defaults: change covers 0100..0200 and incorporates at HP020; the unit is in
# range, sitting open at HP020 with a closed predecessor (i.e. at the point).


def unit(**overrides: str) -> Unit:
    fields = {
        "unit_id": "U1",
        "program": "P",
        "effectivity_key": "0150",
        "hold_point": "HP020",
        "hold_point_status": "open",
        "predecessor_hold_status": "closed",
    }
    return Unit(**{**fields, **overrides})


def change(**overrides: str) -> Change:
    fields = {
        "change_id": "C1",
        "effectivity_from": "0100",
        "effectivity_to": "0200",
        "incorporation_hold_point": "HP020",
        "disposition": "rework",
        "supersedes_part": "PN-OLD",
        "replacement_part": "PN-NEW",
    }
    return Change(**{**fields, **overrides})


def material(
    received: int = 0, staged: int = 0, installed: int = 0, part: str = "PN-OLD", unit_id: str = "U1"
) -> MaterialState:
    return MaterialState(
        unit_id=unit_id,
        part=part,
        qty_received_to_stores=received,
        qty_staged_at_work=staged,
        qty_installed=installed,
    )


def incorporation(incorporated: bool = True, unit_id: str = "U1", change_id: str = "C1") -> Incorporation:
    return Incorporation(unit_id=unit_id, change_id=change_id, incorporated=incorporated)
