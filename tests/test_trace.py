"""Decision traces (ADR 0005): the trace explains, never re-decides."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from builders import change, incorporation, material, unit
from effectivity.cli import load_table, main
from effectivity.model import Change, Incorporation, MaterialState, Unit
from effectivity.resolve import decide_pair, resolve
from effectivity.trace import trace_all, trace_pair

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"


def test_trace_terminal_rule_matches_the_decision() -> None:
    cases = [
        (unit(effectivity_key="0999"), change(), 0, None, "R01"),
        (unit(), change(), 0, incorporation(True), "R02"),
        (unit(predecessor_hold_status="open"), change(), 0, incorporation(True), "R07"),
        (unit(), change(), 1, None, "R04"),
        (unit(hold_point="HP030", hold_point_status="closed"), change(), 0, None, "R05"),
        (unit(hold_point="HP010"), change(), 0, None, "R06"),
        (unit(), change(disposition="use_as_is"), 0, None, "R09"),
        (unit(), change(disposition="scrap", replacement_part=""), 0, None, "R10"),
    ]
    for u, c, qty, inc, terminal in cases:
        trace = trace_pair(u, c, wrong_material_qty=qty, incorporation=inc)
        decision = decide_pair(u, c, wrong_material_qty=qty, incorporation=inc)
        assert trace["decision"] == decision.model_dump(mode="json")
        matched = [s["rule"] for s in trace["steps"] if s["matched"]]
        if terminal == "R07" and inc is not None:
            assert matched == ["R03", "R07"]
            assert trace["decision"]["reason_code"] == "DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR"
        else:
            assert matched == [terminal], (u, c, qty, inc)


def test_trace_marks_unevaluated_rules_after_a_terminal_match() -> None:
    trace = trace_pair(
        unit(effectivity_key="0999"), change(), wrong_material_qty=0, incorporation=None
    )
    by_rule = {s["rule"]: s for s in trace["steps"]}
    assert by_rule["R01"]["evaluated"] is True and by_rule["R01"]["matched"] is True
    assert all(by_rule[r]["evaluated"] is False for r in ("R02", "R03", "R04", "R05", "R10"))
    assert by_rule["R01"]["observed"]["in_range"] is False


def test_trace_observed_values_are_the_predicate_inputs() -> None:
    trace = trace_pair(unit(), change(), wrong_material_qty=3, incorporation=None)
    by_rule = {s["rule"]: s for s in trace["steps"]}
    assert by_rule["R04"]["observed"] == {"wrong_material_qty": 3, "disposition": "rework"}
    assert by_rule["R05"]["observed"]["position"] == 0
    assert by_rule["R01"]["observed"]["in_range"] is True


def test_trace_all_agrees_with_resolve_on_the_examples() -> None:
    units = load_table(EX / "units.csv", Unit)
    changes = load_table(EX / "changes.csv", Change)
    mats = load_table(EX / "material.csv", MaterialState)
    incs = load_table(EX / "incorporations.csv", Incorporation)
    decisions = resolve(units, changes, mats, incs)
    traces = trace_all(units, changes, mats, incs)
    assert len(traces) == len(decisions)
    for trace, decision in zip(traces, decisions, strict=True):
        assert trace["decision"] == decision.model_dump(mode="json")
        assert trace["unit_id"] == decision.unit_id
        assert trace["change_id"] == decision.change_id


def test_trace_covers_every_terminal_rule_on_a_matrix() -> None:
    seen: set[str] = set()
    for disp, hp, hps, pred, staged, inc in itertools.product(
        ["use_as_is", "rework", "scrap", "retrofit"],
        ["HP010", "HP020", "HP030"],
        ["open", "closed"],
        ["open", "closed"],
        [0, 1],
        [None, False, True],
    ):
        u = unit(hold_point=hp, hold_point_status=hps, predecessor_hold_status=pred)
        c = change(disposition=disp, replacement_part="" if disp in ("use_as_is", "scrap") else "PN-NEW")
        inc_row = None if inc is None else incorporation(inc)
        trace = trace_pair(u, c, wrong_material_qty=staged, incorporation=inc_row)
        terminal = trace["decision"]["rule_ids"][-1]
        matched = [s["rule"] for s in trace["steps"] if s["matched"]]
        seen.update(matched)
        assert matched[-1] == terminal
        assert trace["decision"]["rule_ids"] == (
            [r for r in ("R03", terminal) if r in matched] if "R03" in matched else [terminal]
        )
    assert seen == {"R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10"}


def test_trace_file_written_by_cli(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    args = [
        "--units", str(EX / "units.csv"),
        "--changes", str(EX / "changes.csv"),
        "--material", str(EX / "material.csv"),
        "--incorporations", str(EX / "incorporations.csv"),
        "--trace", str(trace_path),
    ]
    assert main(args) == 0
    rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert len(rows) == 50
    assert all(set(row) == {"unit_id", "change_id", "decision", "steps"} for row in rows)
    assert all(len(row["steps"]) == 10 for row in rows)


def test_trace_raises_where_the_resolver_raises() -> None:
    with pytest.raises(ValueError, match="different prefixes"):
        trace_pair(
            unit(hold_point="GATE020"), change(), wrong_material_qty=0, incorporation=None
        )
