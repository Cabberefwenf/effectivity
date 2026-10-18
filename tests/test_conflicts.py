"""Exactly-one-match (ADR 0004): two live changes on one slot BLOCK the run."""

from __future__ import annotations

from pathlib import Path

import pytest

from builders import change, incorporation, material, unit
from effectivity.conflicts import (
    BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES,
    BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED,
    Supersession,
    find_conflicts,
)
from effectivity.model import Status
from effectivity.resolve import resolve

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples" / "applicability"


def two_live_changes() -> tuple:
    """Two changes, same unit, same superseded part, both incorporable."""

    u = unit()
    c1 = change(change_id="C1")
    c2 = change(change_id="C2", disposition="retrofit", replacement_part="PN-NEW2")
    return u, c1, c2


def test_one_live_change_is_no_conflict() -> None:
    u, c1, _c2 = two_live_changes()
    decisions = resolve([u], [c1], [], [])
    assert find_conflicts(decisions, [c1]) == []


def test_two_live_changes_conflict_with_c01() -> None:
    u, c1, c2 = two_live_changes()
    decisions = resolve([u], [c1, c2], [], [])
    (conflict,) = find_conflicts(decisions, [c1, c2])
    assert conflict.unit_id == "U1"
    assert conflict.supersedes_part == "PN-OLD"
    assert conflict.verdict == "BLOCKED"
    assert conflict.reason_code == BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES
    assert conflict.rule_ids == ("C01",)
    assert [c.change_id for c in conflict.competing] == ["C1", "C2"]
    assert conflict.supersession_edges == ()
    assert all(c.status is Status.INCORPORABLE for c in conflict.competing)


def test_supersession_edge_turns_the_conflict_into_c02_but_never_picks_a_winner() -> None:
    u, c1, c2 = two_live_changes()
    decisions = resolve([u], [c1, c2], [], [])
    edge = Supersession(change_id="C2", supersedes_change_id="C1")
    (conflict,) = find_conflicts(decisions, [c1, c2], [edge])
    assert conflict.reason_code == BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED
    assert conflict.rule_ids == ("C02",)
    assert conflict.supersession_edges == (edge,)
    assert len(conflict.competing) == 2  # both still named; neither is chosen


def test_incorporated_change_is_history_not_a_claim() -> None:
    u, c1, c2 = two_live_changes()
    decisions = resolve([u], [c1, c2], [], [incorporation(True, change_id="C1")])
    assert find_conflicts(decisions, [c1, c2]) == []


def test_out_of_effectivity_change_claims_nothing() -> None:
    u, c1, c2 = two_live_changes()
    far = unit(unit_id="U2", effectivity_key="0999")
    decisions = resolve([far], [c1, c2], [], [])
    assert find_conflicts(decisions, [c1, c2]) == []


def test_different_parts_are_different_slots() -> None:
    u = unit()
    c1 = change(change_id="C1")
    c2 = change(change_id="C2", supersedes_part="PN-OTHER")
    decisions = resolve([u], [c1, c2], [], [])
    assert find_conflicts(decisions, [c1, c2]) == []


def test_use_as_is_never_conflicts() -> None:
    u = unit()
    c1 = change(change_id="C1", disposition="use_as_is", supersedes_part="")
    c2 = change(change_id="C2", disposition="use_as_is", supersedes_part="")
    decisions = resolve([u], [c1, c2], [], [])
    assert find_conflicts(decisions, [c1, c2]) == []


def test_late_and_incorporable_together_still_conflict() -> None:
    u = unit()
    c1 = change(change_id="C1")
    c2 = change(change_id="C2", incorporation_hold_point="HP010")
    decisions = resolve([u], [c1, c2], [], [])
    (conflict,) = find_conflicts(decisions, [c1, c2])
    assert {c.status for c in conflict.competing} == {Status.LATE, Status.INCORPORABLE}


def test_wrong_material_blocks_every_change_on_the_slot() -> None:
    u, c1, c2 = two_live_changes()
    decisions = resolve([u], [c1, c2], [material(staged=1)], [])
    (conflict,) = find_conflicts(decisions, [c1, c2])
    assert {c.status for c in conflict.competing} == {Status.BLOCKED_MATERIAL}


def test_supersession_validation() -> None:
    u, c1, c2 = two_live_changes()
    changes = [c1, c2]
    with pytest.raises(ValueError, match="unknown change"):
        find_conflicts([], changes, [Supersession(change_id="NOPE", supersedes_change_id="C1")])
    with pytest.raises(ValueError, match="itself"):
        find_conflicts([], changes, [Supersession(change_id="C1", supersedes_change_id="C1")])
    with pytest.raises(ValueError, match="duplicate supersession"):
        find_conflicts(
            [], changes,
            [Supersession(change_id="C2", supersedes_change_id="C1"),
             Supersession(change_id="C2", supersedes_change_id="C1")],
        )
    with pytest.raises(ValueError, match="cycle"):
        find_conflicts(
            [], changes,
            [Supersession(change_id="C2", supersedes_change_id="C1"),
             Supersession(change_id="C1", supersedes_change_id="C2")],
        )
    other = change(change_id="C3", supersedes_part="PN-OTHER")
    with pytest.raises(ValueError, match="different parts"):
        find_conflicts([], [*changes, other],
                        [Supersession(change_id="C3", supersedes_change_id="C1")])
    flat = change(change_id="C4", disposition="use_as_is", supersedes_part="")
    with pytest.raises(ValueError, match="use_as_is"):
        find_conflicts([], [*changes, flat],
                        [Supersession(change_id="C4", supersedes_change_id="C1")])


def test_example_dataset_has_five_conflicts() -> None:
    from effectivity.cli import load_table
    from effectivity.model import Change, Incorporation, MaterialState, Unit
    from effectivity.pipeline import run_extended

    units = load_table(EX / "units.csv", Unit)
    changes = load_table(EX / "changes.csv", Change)
    material = load_table(EX / "material.csv", MaterialState)
    incorporations = load_table(EX / "incorporations.csv", Incorporation)
    from effectivity.applicability import ApplicabilityRule

    rules = load_table(EX / "applicability.csv", ApplicabilityRule)
    edges = load_table(EX / "supersession.csv", Supersession)
    report = run_extended(
        units, changes, material, incorporations,
        applicability_rules=rules, supersessions=edges,
    )
    assert len(report["conflicts"]) == 5
    codes = sorted(c["reason_code"] for c in report["conflicts"])
    assert codes == [BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES] * 3 + [
        BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED
    ] * 2
    assert report["blocked"] is True


def test_conflicts_flag_passes_when_no_slot_conflicts() -> None:
    from effectivity.cli import main

    examples = ROOT / "examples"
    args = [
        "--units", str(examples / "units.csv"),
        "--changes", str(examples / "changes.csv"),
        "--material", str(examples / "material.csv"),
        "--incorporations", str(examples / "incorporations.csv"),
        "--conflicts",
    ]
    # Core examples have no two live changes on one slot, so no conflict.
    assert main(args) == 0
