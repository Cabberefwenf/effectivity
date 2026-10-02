"""Invariant 6: run log is append-only, hashed, versioned; CLI behaviour."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
from builders import change, incorporation, material, unit

from effectivity import RULE_VERSION, resolve
from effectivity.cli import main
from effectivity.log import append_run, input_hash

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
ARGS = [
    "--units", str(EX / "units.csv"),
    "--changes", str(EX / "changes.csv"),
    "--material", str(EX / "material.csv"),
    "--incorporations", str(EX / "incorporations.csv"),
]


def run(tmp_path: Path, extra: list[str]) -> bytes:
    log = tmp_path / "run-log.jsonl"
    assert main([*ARGS, "--log", str(log), *extra]) == 0
    return log.read_bytes()


def test_rerun_appends_a_new_line_and_leaves_the_prior_line_byte_identical(tmp_path: Path) -> None:
    first = run(tmp_path, [])
    second = run(tmp_path, [])
    assert second.startswith(first)
    assert len(first.splitlines()) == 1 and len(second.splitlines()) == 2
    a, b = (json.loads(x) for x in second.splitlines())
    assert (a["sequence"], b["sequence"]) == (0, 1)
    assert a["input_hash"] == b["input_hash"]
    assert a["decisions"] == b["decisions"] and a["counts"] == b["counts"]
    assert a["rule_version"] == b["rule_version"] == RULE_VERSION


def test_run_at_is_null_unless_given_and_does_not_change_the_hash(tmp_path: Path) -> None:
    run(tmp_path, [])
    run(tmp_path, ["--run-at", "2026-10-02T09:00:00-04:00 (caller label)"])
    lines = [json.loads(x) for x in (tmp_path / "run-log.jsonl").read_text().splitlines()]
    assert lines[0]["run_at"] is None
    assert lines[1]["run_at"] == "2026-10-02T09:00:00-04:00 (caller label)"
    assert lines[0]["input_hash"] == lines[1]["input_hash"]
    assert lines[0]["decisions"] == lines[1]["decisions"]


def test_log_line_contents(tmp_path: Path) -> None:
    (line,) = run(tmp_path, []).splitlines()
    rec = json.loads(line)
    assert set(rec) == {"sequence", "rule_version", "input_hash", "run_at", "counts", "decisions"}
    assert len(rec["input_hash"]) == 64
    assert set(rec["counts"]) == {
        "out_of_effectivity", "not_yet_reached", "incorporable", "late",
        "blocked_material", "incorporated",
    }
    assert sum(rec["counts"].values()) == len(rec["decisions"]) == 50
    assert set(rec["decisions"][0]) == {"unit_id", "change_id", "status", "reason_code", "rule_ids"}


def test_a_prior_line_is_never_rewritten_even_when_inputs_change(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    u, c = unit(), change()
    d1 = resolve([u], [c], [], [])
    d2 = resolve([u], [c], [material(staged=1)], [])
    h1 = input_hash([u], [c], [], [])
    h2 = input_hash([u], [c], [material(staged=1)], [])
    append_run(log, h1, d1)
    before = log.read_bytes()
    assert append_run(log, h2, d2) == 1
    assert log.read_bytes().startswith(before)
    assert h1 != h2


def test_input_hash_ignores_row_order_but_not_content() -> None:
    units = [unit(unit_id=f"U{n}", effectivity_key=f"{100 + n:04d}") for n in range(6)]
    mats = [material(unit_id=f"U{n}", received=n) for n in range(6)]
    base = input_hash(units, [change()], mats, [incorporation(unit_id="U1")])
    rng = random.Random(1)
    for _ in range(5):
        rng.shuffle(units)
        rng.shuffle(mats)
        assert input_hash(units, [change()], mats, [incorporation(unit_id="U1")]) == base
    assert input_hash(units, [change()], mats, [incorporation(False, unit_id="U1")]) != base
    assert input_hash(units, [change(disposition="scrap")], mats, [incorporation(unit_id="U1")]) != base


def test_refuses_to_append_to_a_log_without_a_trailing_newline(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    log.write_bytes(b'{"partial":')
    with pytest.raises(ValueError, match="newline"):
        append_run(log, "0" * 64, [])
    assert log.read_bytes() == b'{"partial":'


def test_cli_output_is_deterministic_and_shows_all_six_states(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(ARGS) == 0
    first = capsys.readouterr().out
    assert main(ARGS) == 0
    assert capsys.readouterr().out == first
    for state in ("out_of_effectivity", "not_yet_reached", "incorporable", "late",
                  "blocked_material", "incorporated"):
        counts = [ln for ln in first.splitlines() if ln.startswith(state + " ")]
        assert counts and int(counts[-1].split()[-1]) > 0, state


def test_cli_reports_bad_input_with_exit_code_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "units.csv"
    bad.write_text(
        "unit_id,program,effectivity_key,hold_point,hold_point_status,predecessor_hold_status\n"
        "U1,P,12-3,HP010,open,closed\n"
    )
    args = [*ARGS]
    args[1] = str(bad)
    assert main(args) == 2
    assert "malformed key" in capsys.readouterr().err
    bad.write_text("unit_id,program\nU1,P\n")
    assert main(args) == 2
