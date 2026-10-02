"""Invariant 5: disposition semantics."""

from __future__ import annotations

import re

import pytest
from builders import change, incorporation, material, unit

from effectivity import Status, resolve
from effectivity.resolve import RULE_TABLE

# Reason codes that recommend installing something. Scrap must never emit one.
# (SCRAP_ONLY_NO_INSTALL and BLOCKED_*_MATERIAL contain "INSTALL" as a word of
# negation / past participle, so a substring check would be wrong. Be explicit.)
INSTALL_RECOMMENDING = {"INCORPORABLE_REWORK", "INCORPORABLE_RETROFIT"}

HOLDS = [("HP010", "open"), ("HP020", "open"), ("HP020", "closed"), ("HP030", "open")]


def scrap_codes_across_inputs() -> set[str]:
    codes: set[str] = set()
    for (hp, hps), pred, (staged, installed), inc in [
        (h, p, q, i)
        for h in HOLDS for p in ("open", "closed") for q in [(0, 0), (1, 0), (0, 1)]
        for i in (None, True, False)
    ]:
        u = unit(hold_point=hp, hold_point_status=hps, predecessor_hold_status=pred)
        c = change(disposition="scrap", replacement_part="PN-NEW-SHOULD-BE-IGNORED")
        d = resolve([u], [c], [material(staged=staged, installed=installed)],
                    [] if inc is None else [incorporation(inc)])[0]
        codes.add(d.reason_code)
        assert "PN-NEW" not in d.reason_code
    return codes


def test_scrap_never_carries_an_install_recommending_reason_code() -> None:
    codes = scrap_codes_across_inputs()
    assert not codes & INSTALL_RECOMMENDING
    assert "SCRAP_ONLY_NO_INSTALL" in codes
    # No scrap code is a positive "install" instruction: INSTALL may only appear
    # as NO_INSTALL, never bare.
    for code in codes:
        for word in re.finditer(r"(?<![A-Z])INSTALL(?![A-Z])", code):
            assert code[: word.start()].endswith("NO_"), code


def test_scrap_at_the_point_with_nothing_installed_is_scrap_only() -> None:
    (d,) = resolve([unit()], [change(disposition="scrap", replacement_part="")], [], [])
    assert (d.status, d.reason_code, d.rule_ids) == (
        Status.INCORPORABLE, "SCRAP_ONLY_NO_INSTALL", ("R10",)
    )


def test_scrap_ignores_replacement_part() -> None:
    with_part = resolve([unit()], [change(disposition="scrap", replacement_part="PN-NEW")], [], [])
    without = resolve([unit()], [change(disposition="scrap", replacement_part="")], [], [])
    assert with_part == without


@pytest.mark.parametrize("staged,installed", [(1, 0), (0, 1)])
def test_scrap_with_superseded_material_at_the_work_is_blocked(staged: int, installed: int) -> None:
    (d,) = resolve([unit()], [change(disposition="scrap", replacement_part="")],
                   [material(staged=staged, installed=installed)], [])
    assert (d.status, d.reason_code) == (Status.BLOCKED_MATERIAL, "BLOCKED_SCRAP_WRONG_MATERIAL")


def test_use_as_is_at_the_point_is_incorporable_and_says_no_rework() -> None:
    (d,) = resolve([unit()], [change(disposition="use_as_is", replacement_part="")], [], [])
    assert (d.status, d.reason_code, d.rule_ids) == (
        Status.INCORPORABLE, "INCORPORABLE_USE_AS_IS_NO_REWORK", ("R09",)
    )


def test_use_as_is_never_gets_a_rework_or_retrofit_reason_code() -> None:
    for hp, hps in HOLDS:
        for staged in (0, 3):
            u = unit(hold_point=hp, hold_point_status=hps)
            (d,) = resolve([u], [change(disposition="use_as_is", replacement_part="")],
                           [material(staged=staged)], [])
            assert "REWORK" not in d.reason_code.replace("NO_REWORK", "")
            assert "RETROFIT" not in d.reason_code


def test_rework_and_retrofit_are_distinct_in_every_status_that_names_a_disposition() -> None:
    for staged, hold in [(0, ("HP020", "open")), (1, ("HP020", "open"))]:
        u = unit(hold_point=hold[0], hold_point_status=hold[1])
        (rw,) = resolve([u], [change(disposition="rework")], [material(staged=staged)], [])
        (rt,) = resolve([u], [change(disposition="retrofit")], [material(staged=staged)], [])
        assert rw.status is rt.status
        assert rw.reason_code != rt.reason_code
        assert "REWORK" in rw.reason_code and "RETROFIT" in rt.reason_code


def test_every_reason_code_a_rule_can_emit_is_unique_to_that_rule() -> None:
    seen: dict[str, str] = {}
    for rule_id, (_status, codes) in RULE_TABLE.items():
        for code in codes:
            assert code not in seen, f"{code} emitted by {seen[code]} and {rule_id}"
            assert code == code.upper() and re.fullmatch(r"[A-Z]+(_[A-Z]+)*", code)
            seen[code] = rule_id


@pytest.mark.parametrize("disposition", ["rework", "retrofit"])
def test_incorporable_requires_open_hold_and_closed_predecessor(disposition: str) -> None:
    c = change(disposition=disposition)
    for hp, hps in HOLDS:
        for pred in ("open", "closed"):
            (d,) = resolve([unit(hold_point=hp, hold_point_status=hps,
                                 predecessor_hold_status=pred)], [c], [], [])
            if d.status is Status.INCORPORABLE:
                assert (hp, hps, pred) == ("HP020", "open", "closed")
            if (hp, hps, pred) == ("HP020", "open", "closed"):
                assert d.status is Status.INCORPORABLE


def test_at_the_point_with_open_predecessor_is_not_yet_reached() -> None:
    (d,) = resolve([unit(predecessor_hold_status="open")], [change()], [], [])
    assert (d.status, d.reason_code) == (Status.NOT_YET_REACHED, "NOT_YET_REACHED_PREDECESSOR_OPEN")
