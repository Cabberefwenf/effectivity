"""Invariant 6: run log is append-only, hashed, versioned; CLI behaviour."""

from __future__ import annotations

import csv
import io
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest
from builders import change, incorporation, material, unit

from effectivity import RULE_VERSION, resolve
from effectivity import log as log_module
from effectivity.cli import load_table, main
from effectivity.log import append_run, input_hash
from effectivity.model import Change, Disposition, Incorporation, MaterialState, Unit

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


# --- Hardening: hash, partial writes, rule version, environment independence ---

TABLES = {
    "units": ("units.csv", Unit),
    "changes": ("changes.csv", Change),
    "material": ("material.csv", MaterialState),
    "incorporations": ("incorporations.csv", Incorporation),
}


def load_examples() -> dict[str, list]:
    return {name: load_table(EX / fname, model) for name, (fname, model) in TABLES.items()}


def example_hash(tables: dict[str, list]) -> str:
    return input_hash(tables["units"], tables["changes"], tables["material"], tables["incorporations"])


def reformat(text: str, variant: int) -> str:
    """Rewrite a CSV with different column order, quoting, line endings, BOM, blank lines, row order."""
    rows = list(csv.reader(io.StringIO(text)))
    header, body = rows[0], rows[1:]
    order = list(range(len(header)))
    if variant % 2:
        order.reverse()
    if variant >= 2:
        body.reverse()
    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_ALL if variant >= 1 else csv.QUOTE_MINIMAL,
                        lineterminator="\r\n" if variant >= 2 else "\n")
    writer.writerow([header[i] for i in order])
    for n, row in enumerate(body):
        writer.writerow([row[i] for i in order])
        if variant >= 3 and n % 2:
            out.write("\r\n")
    return ("\ufeff" if variant >= 3 else "") + out.getvalue()


@pytest.mark.parametrize("variant", [1, 2, 3, 4])
def test_input_hash_is_independent_of_csv_formatting_and_row_order(tmp_path: Path, variant: int) -> None:
    baseline = example_hash(load_examples())
    for name, (fname, _model) in TABLES.items():
        (tmp_path / fname).write_bytes(reformat((EX / fname).read_text(), variant).encode("utf-8"))
    args = [x for flag, (fname, _m) in zip(
        ("--units", "--changes", "--material", "--incorporations"), TABLES.values(), strict=True)
        for x in (flag, str(tmp_path / fname))]
    log = tmp_path / "l.jsonl"
    assert main([*args, "--log", str(log)]) == 0
    assert json.loads(log.read_text())["input_hash"] == baseline


def _changed(field: str, value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    return {"open": "closed", "closed": "open", "rework": "retrofit", "retrofit": "rework",
            "scrap": "use_as_is", "use_as_is": "scrap"}.get(value, value + "9" if field.endswith(("key", "from", "to", "hold_point")) else value + "X")


def test_input_hash_changes_when_any_single_value_in_any_row_changes() -> None:
    base = load_examples()
    baseline = example_hash(base)
    seen = {baseline}
    for name, rows in base.items():
        for index, row in enumerate(rows):
            for field in type(row).model_fields:
                new_value = _changed(field, getattr(row, field))
                assert new_value != getattr(row, field), (name, field)
                variant = {k: list(v) for k, v in base.items()}
                if field == "disposition":
                    new_value = Disposition(new_value)
                values = {f: getattr(row, f) for f in type(row).model_fields}
                variant[name][index] = type(row).model_construct(**{**values, field: new_value})
                h = example_hash(variant)
                assert h != baseline, (name, index, field)
                seen.add(h)
    assert len(seen) == 1 + sum(len(r) * len(type(r[0]).model_fields) for r in base.values() if r)


def test_input_hash_changes_when_a_row_is_added_removed_or_duplicated() -> None:
    base = load_examples()
    baseline = example_hash(base)
    for name, rows in base.items():
        for variant_rows in (rows[:-1], rows + [rows[0]]):
            variant = {**base, name: variant_rows}
            assert example_hash(variant) != baseline, name


def test_input_hash_does_not_move_a_value_between_tables() -> None:
    a = input_hash([unit()], [change()], [], [])
    b = input_hash([], [change()], [], [])
    assert a != b


def test_rule_version_change_changes_the_log_line(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    before = run(tmp_path, [])
    monkeypatch.setattr(log_module, "RULE_VERSION", "9.9.9")
    after = run(tmp_path, [])
    old, new = after.splitlines()[0], after.splitlines()[1]
    assert old + b"\n" == before
    assert json.loads(new)["rule_version"] == "9.9.9"
    assert json.loads(old)["rule_version"] == RULE_VERSION
    assert json.loads(new)["input_hash"] == json.loads(old)["input_hash"]
    assert new != old


class _Handle:
    def __init__(self, writes: list[bytes], result: int | None, error: Exception | None) -> None:
        self.writes, self.result, self.error = writes, result, error

    def __enter__(self) -> "_Handle":
        return self

    def __exit__(self, *_a: object) -> None:
        return None

    def write(self, data: bytes) -> int:
        if self.error:
            raise self.error
        self.writes.append(data)
        return len(data) if self.result is None else self.result


def test_a_log_line_is_one_write_of_a_whole_newline_terminated_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    writes: list[bytes] = []
    real_open = Path.open
    modes: list[str] = []

    def spy(self: Path, mode: str = "r", *a: object, **k: object):
        if self.name == "l.jsonl" and "a" in mode:
            modes.append(mode)
            return _Handle(writes, None, None)
        return real_open(self, mode, *a, **k)

    monkeypatch.setattr(Path, "open", spy)
    append_run(tmp_path / "l.jsonl", "0" * 64, resolve([unit()], [change()], [], []))
    assert modes == ["ab"]
    assert len(writes) == 1 and writes[0].endswith(b"\n") and writes[0].count(b"\n") == 1
    json.loads(writes[0])


def test_failed_write_leaves_existing_log_untouched_and_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log = tmp_path / "l.jsonl"
    append_run(log, "0" * 64, [])
    before = log.read_bytes()
    real_open = Path.open

    def failing(self: Path, mode: str = "r", *a: object, **k: object):
        if "a" in mode:
            return _Handle([], None, OSError("disk full"))
        return real_open(self, mode, *a, **k)

    monkeypatch.setattr(Path, "open", failing)
    with pytest.raises(OSError, match="disk full"):
        append_run(log, "1" * 64, [])
    monkeypatch.undo()
    assert log.read_bytes() == before


def test_short_write_is_reported_as_an_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    real_open = Path.open
    monkeypatch.setattr(
        Path, "open",
        lambda self, mode="r", *a, **k: _Handle([], 5, None) if "a" in mode else real_open(self, mode, *a, **k),
    )
    with pytest.raises(OSError, match="short write"):
        append_run(tmp_path / "l.jsonl", "0" * 64, [])


def test_failure_before_the_write_does_not_create_the_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom(*_a: object, **_k: object) -> str:
        raise RuntimeError("cannot serialize")

    monkeypatch.setattr(log_module, "log_line", boom)
    log = tmp_path / "l.jsonl"
    with pytest.raises(RuntimeError):
        append_run(log, "0" * 64, [])
    assert not log.exists()


@pytest.mark.parametrize("label", ["a\nb", 'quote " and \\ backslash', "tab\there", "\u00e9\u4e2d\U0001f600", "\ud800", ""])
def test_run_at_is_stored_verbatim_on_exactly_one_line(tmp_path: Path, label: str) -> None:
    log = tmp_path / "l.jsonl"
    append_run(log, "0" * 64, [], run_at=label)
    append_run(log, "0" * 64, [])
    raw = log.read_bytes()
    assert raw.count(b"\n") == 2
    first = json.loads(raw.splitlines()[0])
    assert first["run_at"] == label


def test_log_creates_the_file_at_sequence_zero_and_continues_from_existing_lines(tmp_path: Path) -> None:
    log = tmp_path / "l.jsonl"
    assert append_run(log, "0" * 64, []) == 0
    log.write_bytes(log.read_bytes() + b"not json at all\n\n")
    assert append_run(log, "0" * 64, []) == 3


def test_decisions_in_the_log_match_the_printed_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (line,) = run(tmp_path, []).splitlines()
    printed = capsys.readouterr().out
    for d in json.loads(line)["decisions"]:
        assert f"{d['unit_id']}" in printed and d["reason_code"] in printed


def _cli_output(cwd: Path, env_extra: dict[str, str]) -> bytes:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONHASHSEED", "TZ", "LC_ALL")}
    env.update(env_extra)
    args = [x for flag, name in zip(
        ("--units", "--changes", "--material", "--incorporations"), TABLES.values(), strict=True)
        for x in (flag, str(EX / name[0]))]
    result = subprocess.run([sys.executable, "-m", "effectivity", *args], cwd=cwd, env=env,
                            capture_output=True, check=True)
    return result.stdout


def test_output_is_identical_across_hash_seeds_locales_time_zones_and_working_directories(tmp_path: Path) -> None:
    other_dir = tmp_path / "elsewhere"
    other_dir.mkdir()
    outputs = {
        _cli_output(ROOT, {"PYTHONHASHSEED": "0"}),
        _cli_output(ROOT, {"PYTHONHASHSEED": "1"}),
        _cli_output(other_dir, {"PYTHONHASHSEED": "12345"}),
        _cli_output(other_dir, {"PYTHONHASHSEED": "random", "TZ": "Pacific/Kiritimati", "LC_ALL": "C"}),
    }
    assert len(outputs) == 1
    assert b"blocked_material" in outputs.pop()


def test_run_at_defaults_to_null_when_not_given(tmp_path: Path) -> None:
    log = tmp_path / "l.jsonl"
    append_run(log, "0" * 64, [])
    assert json.loads(log.read_text())["run_at"] is None
