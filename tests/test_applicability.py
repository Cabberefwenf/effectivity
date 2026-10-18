"""Applicability first (ADR 0004): explicit, wildcard, default, validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from builders import change, unit
from effectivity.applicability import (
    A_DEFAULT,
    A_EXPLICIT,
    A_WILDCARD,
    ApplicabilityRule,
    applicability_map,
    applies_to,
    excluded_pairs,
    validate_applicability_rules,
)
from effectivity.cli import load_table, main
from effectivity.model import Change, Incorporation, MaterialState, Unit
from effectivity.pipeline import run_extended

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples" / "applicability"


def rule(change_id: str, program: str, applies: str) -> ApplicabilityRule:
    return ApplicabilityRule(change_id=change_id, program=program, applies=applies)


def test_default_applies_when_no_rule_names_the_change() -> None:
    assert applies_to([], "C1", "P") == (True, A_DEFAULT)


def test_explicit_rule_decides() -> None:
    rules = [rule("C1", "P", "false")]
    assert applies_to(rules, "C1", "P") == (False, A_EXPLICIT)
    assert applies_to(rules, "C1", "Q") == (True, A_DEFAULT)


def test_wildcard_applies_to_every_program() -> None:
    rules = [rule("C1", "*", "false")]
    assert applies_to(rules, "C1", "P") == (False, A_WILDCARD)
    assert applies_to(rules, "C1", "Q") == (False, A_WILDCARD)
    assert applies_to(rules, "C2", "P") == (True, A_DEFAULT)


def test_explicit_rule_beats_the_wildcard_for_its_program() -> None:
    rules = [rule("C1", "*", "false"), rule("C1", "P", "true")]
    assert applies_to(rules, "C1", "P") == (True, A_EXPLICIT)
    assert applies_to(rules, "C1", "Q") == (False, A_WILDCARD)


def test_applies_must_be_exactly_true_or_false() -> None:
    with pytest.raises(ValueError, match="applies"):
        ApplicabilityRule(change_id="C1", program="P", applies="yes")
    with pytest.raises(ValueError, match="applies"):
        ApplicabilityRule(change_id="C1", program="P", applies="True")
    with pytest.raises(ValueError, match="applies"):
        ApplicabilityRule(change_id="C1", program="P", applies=1)


def test_duplicate_rule_for_the_same_pair_is_an_error() -> None:
    changes = [change()]
    units = [unit()]
    rules = [rule("C1", "P", "true"), rule("C1", "P", "false")]
    with pytest.raises(ValueError, match="duplicate applicability"):
        validate_applicability_rules(rules, changes, units)


def test_rule_naming_unknown_change_or_program_is_an_error() -> None:
    with pytest.raises(ValueError, match="unknown change"):
        validate_applicability_rules([rule("NOPE", "P", "true")], [change()], [unit()])
    with pytest.raises(ValueError, match="unknown program"):
        validate_applicability_rules([rule("C1", "NOPE", "true")], [change()], [unit()])


def test_excluded_pairs_name_the_rule_and_reason() -> None:
    changes = [change()]
    units = [unit(), unit(unit_id="U2", program="Q")]
    rules = [rule("C1", "Q", "false")]
    excluded = excluded_pairs(units, changes, rules)
    assert excluded == [
        {
            "unit_id": "U2",
            "change_id": "C1",
            "rule_id": A_EXPLICIT,
            "reason": "change C1 does not apply to program Q",
        }
    ]


def test_extended_run_drops_excluded_pairs_but_keeps_the_rest() -> None:
    units = load_table(EX / "units.csv", Unit)
    changes = load_table(EX / "changes.csv", Change)
    material = load_table(EX / "material.csv", MaterialState)
    incorporations = load_table(EX / "incorporations.csv", Incorporation)
    rules = load_table(EX / "applicability.csv", ApplicabilityRule)
    report = run_extended(units, changes, material, incorporations, applicability_rules=rules)
    kept = {(d["unit_id"], d["change_id"]) for d in report["decisions"]}
    assert ("U-Y1", "C-X2") not in kept
    assert ("U-Y1", "C-X1") in kept
    assert report["applicability"]["excluded"] == [
        {
            "unit_id": "U-Y1",
            "change_id": "C-X2",
            "rule_id": A_EXPLICIT,
            "reason": "change C-X2 does not apply to program Q",
        }
    ]
    assert report["blocked"] is True  # the example also carries conflicts
    assert report["input_hash"] != report["extended_input_hash"]


def test_extended_hash_moves_when_an_applicability_rule_changes() -> None:
    units = [unit()]
    changes = [change()]
    base = run_extended(units, changes, [], [], applicability_rules=[])
    other = run_extended(
        units, changes, [], [], applicability_rules=[rule("C1", "P", "false")]
    )
    assert base["extended_input_hash"] != other["extended_input_hash"]
    assert base["input_hash"] == other["input_hash"]
    assert other["decisions"] == []
    assert len(other["applicability"]["excluded"]) == 1


def test_cli_extended_example_exits_3_with_blocked_in_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = [
        "--units", str(EX / "units.csv"),
        "--changes", str(EX / "changes.csv"),
        "--material", str(EX / "material.csv"),
        "--incorporations", str(EX / "incorporations.csv"),
        "--applicability", str(EX / "applicability.csv"),
        "--supersession", str(EX / "supersession.csv"),
        "--extended-report", str(tmp_path / "report.json"),
    ]
    assert main(args) == 3
    out = capsys.readouterr().out
    assert "BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED (C02)" in out
    assert "BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES (C01)" in out
    assert "U-Y1 C-X2 excluded (A01)" in out
    import json

    report = json.loads((tmp_path / "report.json").read_text())
    assert report["blocked"] is True
    assert len(report["conflicts"]) == 5


def test_applicability_map_is_deterministic_under_row_order() -> None:
    units = [unit(), unit(unit_id="U2", program="Q")]
    changes = [change(), change(change_id="C2")]
    rules = [rule("C1", "Q", "false"), rule("C2", "*", "false")]
    first = applicability_map(units, changes, rules)
    assert applicability_map(list(reversed(units)), list(reversed(changes)), list(reversed(rules))) == first
