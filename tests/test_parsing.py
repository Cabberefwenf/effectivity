"""CSV and model input edge cases. Each is handled by a documented rule or raises a clear error."""

from __future__ import annotations

from pathlib import Path

import pytest
from builders import change, incorporation, material, unit
from pydantic import ValidationError

from effectivity import Status, resolve
from effectivity.cli import load_table, main
from effectivity.model import Change, Incorporation, KeyFormatError, MaterialState, Unit, parse_key

UNITS_H = "unit_id,program,effectivity_key,hold_point,hold_point_status,predecessor_hold_status"
CHANGES_H = ("change_id,effectivity_from,effectivity_to,incorporation_hold_point,"
             "disposition,supersedes_part,replacement_part")
MATERIAL_H = "unit_id,part,qty_received_to_stores,qty_staged_at_work,qty_installed"
INC_H = "unit_id,change_id,incorporated"
GOOD_UNIT = "U1,P,0150,HP020,open,closed"
GOOD_CHANGE = "C1,0100,0200,HP020,rework,PN-OLD,PN-NEW"
GOOD_MATERIAL = "U1,PN-OLD,1,0,0"


def write(tmp_path: Path, name: str, content: str | bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return path


def load_error(tmp_path: Path, model, content: str | bytes) -> str:
    path = write(tmp_path, "t.csv", content)
    with pytest.raises(ValueError) as info:
        load_table(path, model)
    return str(info.value)


# --- Formatting that is accepted by documented rule ---------------------------

@pytest.mark.parametrize(
    "text",
    [
        f"{UNITS_H}\n{GOOD_UNIT}\n",                                   # LF
        f"{UNITS_H}\r\n{GOOD_UNIT}\r\n",                               # CRLF
        f"{UNITS_H}\n{GOOD_UNIT}",                                     # no trailing newline
        f"{UNITS_H}\n\n{GOOD_UNIT}\n\n",                               # blank lines skipped
        "\ufeff" + f"{UNITS_H}\n{GOOD_UNIT}\n",                        # UTF-8 BOM (Excel)
        f'"unit_id","program","effectivity_key","hold_point","hold_point_status",'
        f'"predecessor_hold_status"\n"U1","P","0150","HP020","open","closed"\n',   # quoted
        "program,unit_id,hold_point,effectivity_key,predecessor_hold_status,hold_point_status\n"
        "P,U1,HP020,0150,closed,open\n",                               # column order
    ],
)
def test_equivalent_unit_csv_formats_load_identically(tmp_path: Path, text: str) -> None:
    (row,) = load_table(write(tmp_path, "u.csv", text), Unit)
    assert row == unit()


def test_header_only_table_is_an_empty_table_not_an_error(tmp_path: Path) -> None:
    assert load_table(write(tmp_path, "m.csv", MATERIAL_H + "\n"), MaterialState) == []
    assert load_table(write(tmp_path, "i.csv", INC_H + "\n"), Incorporation) == []


# --- Structure errors ---------------------------------------------------------

def test_empty_file_and_missing_file_are_errors(tmp_path: Path) -> None:
    assert "columns" in load_error(tmp_path, Unit, "")
    with pytest.raises(OSError):
        load_table(tmp_path / "nope.csv", Unit)


def test_duplicate_column_is_an_error_not_last_one_wins(tmp_path: Path) -> None:
    msg = load_error(tmp_path, Unit,
                     UNITS_H + ",program\nU1,P,0150,HP020,open,closed,OTHER\n")
    assert "duplicate column" in msg


def test_missing_and_extra_columns_name_the_problem(tmp_path: Path) -> None:
    msg = load_error(tmp_path, Unit, "unit_id,program\nU1,P\n")
    assert "missing" in msg and "effectivity_key" in msg
    msg = load_error(tmp_path, Unit, UNITS_H + ",notes\n" + GOOD_UNIT + ",x\n")
    assert "unexpected" in msg and "notes" in msg


@pytest.mark.parametrize("header", [UNITS_H.replace("unit_id", "Unit_ID"), UNITS_H.replace("unit_id", " unit_id")])
def test_column_names_are_exact(tmp_path: Path, header: str) -> None:
    load_error(tmp_path, Unit, header + "\n" + GOOD_UNIT + "\n")


def test_short_and_long_rows_report_their_line_number(tmp_path: Path) -> None:
    short = load_error(tmp_path, Unit, f"{UNITS_H}\n{GOOD_UNIT}\nU2,P,0150\n")
    long = load_error(tmp_path, Unit, f"{UNITS_H}\n{GOOD_UNIT},extra\n")
    assert ":3:" in short and ":2:" in long
    assert "wrong number of fields" in short and "wrong number of fields" in long


def test_line_number_is_right_after_blank_lines(tmp_path: Path) -> None:
    assert ":5:" in load_error(tmp_path, Unit, f"{UNITS_H}\n\n{GOOD_UNIT}\n\nU2,P,12-3,HP020,open,closed\n")


def test_non_utf8_and_nul_bytes_are_errors(tmp_path: Path) -> None:
    assert "UTF-8" in load_error(tmp_path, Unit, UNITS_H.encode() + b"\nU1,P,\xff,HP020,open,closed\n")
    load_error(tmp_path, Unit, UNITS_H.encode() + b"\nU1,P,01\x0050,HP020,open,closed\n")


# --- Values --------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["Open", "OPEN", " open", "open ", "opened", "", "1", "true"])
def test_hold_status_must_be_exactly_open_or_closed(tmp_path: Path, bad: str) -> None:
    load_error(tmp_path, Unit, f"{UNITS_H}\nU1,P,0150,HP020,{bad},closed\n")
    load_error(tmp_path, Unit, f"{UNITS_H}\nU1,P,0150,HP020,open,{bad}\n")


@pytest.mark.parametrize("bad", ["True", "TRUE", "1", "0", "yes", "", " true", "false "])
def test_incorporated_must_be_exactly_true_or_false(tmp_path: Path, bad: str) -> None:
    load_error(tmp_path, Incorporation, f"{INC_H}\nU1,C1,{bad}\n")


@pytest.mark.parametrize("bad", ["Rework", "REWORK", "re-work", "", "use as is", "swap"])
def test_disposition_must_be_an_exact_known_value(tmp_path: Path, bad: str) -> None:
    load_error(tmp_path, Change, f"{CHANGES_H}\nC1,0100,0200,HP020,{bad},PN-OLD,PN-NEW\n")


@pytest.mark.parametrize(
    "bad",
    ["-1", "1.5", "2.0", "1e3", " 3", "3 ", "+3", "1_000", "0x10", "", "three", "\u0663", "NaN", "9" * 16],
)
def test_quantities_are_plain_non_negative_integers(tmp_path: Path, bad: str) -> None:
    for column in range(3):
        cells = ["0", "0", "0"]
        cells[column] = bad
        load_error(tmp_path, MaterialState, f"{MATERIAL_H}\nU1,PN-OLD,{','.join(cells)}\n")


def test_quantity_edge_values_are_accepted(tmp_path: Path) -> None:
    (row,) = load_table(write(tmp_path, "m.csv", f"{MATERIAL_H}\nU1,PN-OLD,0,007,{'9' * 15}\n"), MaterialState)
    assert (row.qty_received_to_stores, row.qty_staged_at_work, row.qty_installed) == (0, 7, 10**15 - 1)


@pytest.mark.parametrize("value", [True, 2.0, 1.5, None, [1], -1, 10**15])
def test_programmatic_quantities_must_be_real_ints(value: object) -> None:
    with pytest.raises(ValidationError):
        MaterialState(unit_id="U1", part="P", qty_received_to_stores=value,
                      qty_staged_at_work=0, qty_installed=0)


# --- Identifiers and parts: exact, printable ASCII, no stray whitespace ---------

@pytest.mark.parametrize("bad", [" U1", "U1 ", "U\t1", "U1\n", "\u00dc1", "U\u0431", "", "U\x001"])
def test_ids_must_be_clean_printable_ascii(bad: str) -> None:
    with pytest.raises(ValidationError):
        unit(unit_id=bad)
    with pytest.raises(ValidationError):
        incorporation(unit_id=bad)
    with pytest.raises(ValidationError):
        material(unit_id=bad)


@pytest.mark.parametrize("bad", [" PN-OLD", "PN-OLD ", "PN-OLD\n", "PN\u2011OLD", "PN\u0430OLD"])
def test_part_numbers_with_stray_whitespace_or_lookalike_characters_are_rejected(bad: str) -> None:
    # Otherwise a trailing space would silently stop material from matching.
    with pytest.raises(ValidationError):
        material(part=bad)
    with pytest.raises(ValidationError):
        change(supersedes_part=bad)


def test_part_numbers_may_contain_inner_spaces_and_punctuation() -> None:
    material(part="PN 12/A-3")


def test_part_match_is_exact_and_case_sensitive() -> None:
    (d,) = resolve([unit()], [change()], [material(staged=3, part="pn-old")], [])
    assert d.status is Status.INCORPORABLE


# --- supersedes_part / replacement_part -----------------------------------------

def test_empty_supersedes_part_by_disposition(tmp_path: Path) -> None:
    ok = load_table(write(tmp_path, "c.csv", f"{CHANGES_H}\nC1,0100,0200,HP020,use_as_is,,\n"), Change)
    assert ok[0].supersedes_part == "" and ok[0].replacement_part == ""
    for disp in ("rework", "retrofit", "scrap"):
        assert "supersedes_part" in load_error(tmp_path, Change,
                                               f"{CHANGES_H}\nC1,0100,0200,HP020,{disp},,PN-NEW\n")


@pytest.mark.parametrize("disposition", ["scrap", "use_as_is"])
def test_replacement_part_on_scrap_or_use_as_is_is_ignored_by_decisions(disposition: str) -> None:
    for hold, status in [("HP010", "open"), ("HP020", "open"), ("HP030", "open")]:
        u = unit(hold_point=hold, hold_point_status=status)
        with_part = resolve([u], [change(disposition=disposition, replacement_part="PN-NEW")], [], [])
        without = resolve([u], [change(disposition=disposition, replacement_part="")], [], [])
        assert with_part == without


def test_replacement_part_does_not_count_as_wrong_material_and_is_not_matched() -> None:
    (d,) = resolve([unit()], [change(replacement_part="PN-NEW")],
                   [material(staged=5, part="PN-NEW"), material(installed=5, part="PN-NEW")], [])
    assert d.status is Status.INCORPORABLE


# --- Ranges and keys -------------------------------------------------------------

def test_from_greater_than_to_is_rejected_at_csv_level(tmp_path: Path) -> None:
    msg = load_error(tmp_path, Change, f"{CHANGES_H}\nC1,0200,0100,HP020,rework,PN-OLD,PN-NEW\n")
    assert "must not be greater" in msg
    assert ":2:" in msg


def test_single_unit_range_from_equals_to_is_valid() -> None:
    (d,) = resolve([unit(effectivity_key="0150")], [change(effectivity_from="0150", effectivity_to="0150")], [], [])
    assert d.status is not Status.OUT_OF_EFFECTIVITY
    (d,) = resolve([unit(effectivity_key="0150A")], [change(effectivity_from="0150", effectivity_to="0150")], [], [])
    assert d.status is Status.OUT_OF_EFFECTIVITY


@pytest.mark.parametrize("alias", ["0123A", "123A", "000123A"])
def test_suffix_key_spellings_with_different_padding_are_equivalent(alias: str) -> None:
    assert parse_key(alias) == parse_key("0123A")
    for lo, hi in [(alias, "0124"), ("0123", alias), (alias, alias)]:
        (d,) = resolve([unit(effectivity_key="0123A")], [change(effectivity_from=lo, effectivity_to=hi)], [], [])
        assert d.status is not Status.OUT_OF_EFFECTIVITY
    # "0123" and "123A" are different keys: the suffixed one sorts after
    assert parse_key("0123") != parse_key("123A") and parse_key("0123") < parse_key("123A")
    (d,) = resolve([unit(effectivity_key=alias)], [change(effectivity_from="0123", effectivity_to="0123")], [], [])
    assert d.status is Status.OUT_OF_EFFECTIVITY


@pytest.mark.parametrize("bad", ["\u0663\u0662", "\uff11\uff12\uff13", "H\u0412001", "\u00e9", "\u2167", "1" * 19, "A" * 9 + "1"])
def test_unicode_and_oversized_keys_are_rejected(bad: str) -> None:
    with pytest.raises(KeyFormatError):
        parse_key(bad)


def test_largest_allowed_number_is_accepted_and_orders_correctly() -> None:
    assert parse_key("9" * 18) > parse_key("9" * 17 + "8")


def test_cross_prefix_hold_points_error_names_the_pair() -> None:
    with pytest.raises(ValueError, match="U1.*C1|C1.*U1"):
        resolve([unit(hold_point="GATE020")], [change()], [], [])


def test_cross_prefix_hold_points_for_out_of_range_pair_do_not_raise() -> None:
    (d,) = resolve([unit(effectivity_key="0999", hold_point="GATE020")], [change()], [], [])
    assert d.status is Status.OUT_OF_EFFECTIVITY


# --- CLI ---------------------------------------------------------------------------

def run_cli(tmp_path: Path, units: str, extra: list[str] | None = None) -> int:
    paths = {
        "--units": write(tmp_path, "u.csv", units),
        "--changes": write(tmp_path, "c.csv", f"{CHANGES_H}\n{GOOD_CHANGE}\n"),
        "--material": write(tmp_path, "m.csv", f"{MATERIAL_H}\n{GOOD_MATERIAL}\n"),
        "--incorporations": write(tmp_path, "i.csv", f"{INC_H}\n"),
    }
    argv = [x for k, v in paths.items() for x in (k, str(v))]
    return main(argv + (extra or []))


def test_cli_end_to_end_with_bom_and_crlf(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(tmp_path, "\ufeff" + f"{UNITS_H}\r\n{GOOD_UNIT}\r\n") == 0
    assert "incorporable" in capsys.readouterr().out


def test_cli_duplicate_unit_rows_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(tmp_path, f"{UNITS_H}\n{GOOD_UNIT}\n{GOOD_UNIT}\n") == 2
    assert "duplicate unit_id" in capsys.readouterr().err


def test_cli_failure_creates_no_log_file(tmp_path: Path) -> None:
    log = tmp_path / "run-log.jsonl"
    assert run_cli(tmp_path, f"{UNITS_H}\nU1,P,12-3,HP020,open,closed\n", ["--log", str(log)]) == 2
    assert not log.exists()


def test_cli_run_at_without_log_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as info:
        run_cli(tmp_path, f"{UNITS_H}\n{GOOD_UNIT}\n", ["--run-at", "x"])
    assert info.value.code == 2


def test_cli_unwritable_log_path_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_cli(tmp_path, f"{UNITS_H}\n{GOOD_UNIT}\n", ["--log", str(tmp_path / "no" / "such" / "dir.jsonl")]) == 2
    assert "error:" in capsys.readouterr().err
