"""Invariant 4 and the material matching rule (design guidance)."""

from __future__ import annotations

import pytest
from builders import change, material, unit

from effectivity import Status, resolve

AT_POINT = {}  # default unit sits open at HP020 with a closed predecessor


@pytest.mark.parametrize("disposition", ["rework", "retrofit", "scrap"])
def test_receipt_to_stores_alone_does_not_block(disposition: str) -> None:
    (d,) = resolve([unit()], [change(disposition=disposition)], [material(received=50)], [])
    assert d.status is Status.INCORPORABLE
    assert "R04" not in d.rule_ids


@pytest.mark.parametrize("disposition", ["rework", "retrofit"])
@pytest.mark.parametrize("staged,installed", [(1, 0), (0, 1), (5, 5)])
def test_staged_or_installed_superseded_qty_blocks_rework_and_retrofit(
    disposition: str, staged: int, installed: int
) -> None:
    (d,) = resolve(
        [unit()], [change(disposition=disposition)],
        [material(received=9, staged=staged, installed=installed)], [],
    )
    assert d.status is Status.BLOCKED_MATERIAL
    assert d.rule_ids == ("R04",)
    assert d.reason_code == f"BLOCKED_{disposition.upper()}_WRONG_MATERIAL"


@pytest.mark.parametrize("disposition", ["rework", "retrofit", "scrap"])
def test_wrong_material_blocks_even_before_the_unit_reaches_the_hold_point(disposition: str) -> None:
    u = unit(hold_point="HP010")
    (d,) = resolve([u], [change(disposition=disposition)], [material(staged=1)], [])
    assert d.status is Status.BLOCKED_MATERIAL


def test_duplicate_material_rows_are_summed() -> None:
    rows = [material(received=5), material(staged=1), material(received=2)]
    (d,) = resolve([unit()], [change()], rows, [])
    assert d.status is Status.BLOCKED_MATERIAL


def test_zero_staged_rows_across_duplicates_still_do_not_block() -> None:
    rows = [material(received=5), material(received=7)]
    (d,) = resolve([unit()], [change()], rows, [])
    assert d.status is Status.INCORPORABLE


@pytest.mark.parametrize(
    "row",
    [
        material(staged=9, part="PN-OTHER"),        # different part
        material(staged=9, unit_id="U2"),           # different unit
        material(staged=9, part="pn-old"),          # match is exact, case-sensitive
        material(staged=9, part="PN-NEW"),          # replacement part is not wrong material
    ],
)
def test_only_the_superseded_part_on_this_unit_counts(row) -> None:
    other = unit(unit_id="U2", effectivity_key="0999")
    (d, _) = resolve([unit(), other], [change()], [row], [])
    assert d.unit_id == "U1" and d.status is Status.INCORPORABLE


@pytest.mark.parametrize("staged,installed", [(0, 0), (4, 0), (0, 4), (2, 2)])
@pytest.mark.parametrize("hold", [("HP010", "open"), ("HP020", "open"), ("HP020", "closed"), ("HP030", "open")])
def test_use_as_is_never_blocks_on_material(staged: int, installed: int, hold: tuple[str, str]) -> None:
    hp, hps = hold
    (d,) = resolve(
        [unit(hold_point=hp, hold_point_status=hps)],
        [change(disposition="use_as_is", replacement_part="")],
        [material(received=3, staged=staged, installed=installed)],
        [],
    )
    assert d.status is not Status.BLOCKED_MATERIAL
    assert "R04" not in d.rule_ids


def test_use_as_is_with_empty_supersedes_part_is_allowed_and_rework_is_not() -> None:
    change(disposition="use_as_is", supersedes_part="", replacement_part="")
    for disposition in ("rework", "retrofit", "scrap"):
        with pytest.raises(ValueError, match="supersedes_part"):
            change(disposition=disposition, supersedes_part="")
