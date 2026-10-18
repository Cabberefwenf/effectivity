"""Log verification (ADR 0005): audit a run log without changing it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from builders import change, unit
from effectivity.cli import main
from effectivity.log import append_run, input_hash
from effectivity.resolve import resolve
from effectivity.verify import verify_log

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
ARGS = [
    "--units", str(EXAMPLES / "units.csv"),
    "--changes", str(EXAMPLES / "changes.csv"),
    "--material", str(EXAMPLES / "material.csv"),
    "--incorporations", str(EXAMPLES / "incorporations.csv"),
]


def _write_log(tmp_path: Path, runs: int = 2) -> Path:
    log = tmp_path / "run-log.jsonl"
    assert main([*ARGS, "--log", str(log)]) == 0
    if runs == 2:
        assert main([*ARGS, "--log", str(log), "--run-at", "label"]) == 0
    return log


def test_verify_ok_on_a_real_log(tmp_path: Path) -> None:
    log = _write_log(tmp_path)
    result = verify_log(log)
    assert result == {
        "ok": True,
        "lines": 2,
        "rule_versions": ["1.0.0"],
        "problems": [],
    }


def test_verify_empty_log_is_ok(tmp_path: Path) -> None:
    log = tmp_path / "empty.jsonl"
    log.write_bytes(b"")
    assert verify_log(log)["ok"] is True


def test_verify_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        verify_log(tmp_path / "nope.jsonl")


def test_verify_catches_bad_json(tmp_path: Path) -> None:
    log = _write_log(tmp_path, runs=1)
    log.write_bytes(log.read_bytes() + b"not json\n")
    result = verify_log(log)
    assert result["ok"] is False
    assert result["problems"][0]["line"] == 2
    assert "not valid JSON" in result["problems"][0]["message"]


def test_verify_catches_sequence_break(tmp_path: Path) -> None:
    log = _write_log(tmp_path)
    lines = log.read_text().splitlines()
    rec = json.loads(lines[1])
    rec["sequence"] = 7
    log.write_text(lines[0] + "\n" + json.dumps(rec) + "\n")
    result = verify_log(log)
    assert result["ok"] is False
    assert any("sequence is 7, expected 1" in p["message"] for p in result["problems"])


def test_verify_catches_counts_that_do_not_match(tmp_path: Path) -> None:
    log = _write_log(tmp_path, runs=1)
    rec = json.loads(log.read_text())
    rec["counts"]["incorporated"] += 1
    log.write_text(json.dumps(rec) + "\n")
    result = verify_log(log)
    assert result["ok"] is False
    assert any("counts do not match" in p["message"] for p in result["problems"])


def test_verify_catches_unsorted_and_duplicated_decisions(tmp_path: Path) -> None:
    log = _write_log(tmp_path, runs=1)
    rec = json.loads(log.read_text())
    rec["decisions"] = list(reversed(rec["decisions"]))
    log.write_text(json.dumps(rec) + "\n")
    result = verify_log(log)
    assert result["ok"] is False
    assert any("not sorted" in p["message"] for p in result["problems"])
    rec["decisions"] = rec["decisions"][:1] * 2 + rec["decisions"][1:]
    rec["decisions"] = sorted(rec["decisions"], key=lambda d: (d["unit_id"], d["change_id"]))
    log.write_text(json.dumps(rec) + "\n")
    result = verify_log(log)
    assert result["ok"] is False
    assert any("duplicate" in p["message"] for p in result["problems"])


def test_verify_catches_missing_newline_and_wrong_keys(tmp_path: Path) -> None:
    log = _write_log(tmp_path, runs=1)
    log.write_bytes(log.read_bytes().rstrip(b"\n"))
    result = verify_log(log)
    assert result["ok"] is False
    assert any("does not end with a newline" in p["message"] for p in result["problems"])
    log.write_text('{"sequence": 0}\n')
    result = verify_log(log)
    assert result["ok"] is False
    assert any("record keys must be" in p["message"] for p in result["problems"])


def test_verify_does_not_rewrite_the_file(tmp_path: Path) -> None:
    log = _write_log(tmp_path)
    before = log.read_bytes()
    verify_log(log)
    assert log.read_bytes() == before


def test_cli_verify_log_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = _write_log(tmp_path)
    assert main(["--verify-log", str(log)]) == 0
    assert "verified: 2 line(s)" in capsys.readouterr().out
    log.write_bytes(log.read_bytes() + b"garbage\n")
    assert main(["--verify-log", str(log)]) == 3
    assert "verify: line 3" in capsys.readouterr().err


def test_cli_verify_log_cannot_combine_with_tables() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--verify-log", "x.jsonl", "--units", "u.csv"])
    assert exc.value.code == 2


def test_cli_verify_log_missing_file_is_exit_2(tmp_path: Path) -> None:
    assert main(["--verify-log", str(tmp_path / "nope.jsonl")]) == 2


def test_verify_accepts_a_log_with_two_rule_versions(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    decisions = resolve([unit()], [change()], [], [])
    digest = input_hash([unit()], [change()], [], [])
    append_run(log, digest, decisions)
    append_run(log, digest, decisions)
    lines = log.read_text().splitlines()
    rec = json.loads(lines[1])
    rec["rule_version"] = "9.9.9"
    log.write_text(lines[0] + "\n" + json.dumps(rec) + "\n")
    result = verify_log(log)
    assert result["ok"] is True
    assert result["rule_versions"] == ["1.0.0", "9.9.9"]
