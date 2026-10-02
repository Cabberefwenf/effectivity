"""Invariants 1, 2, 3, 6, 7, the key rule (ADR 0001), and doc/code agreement."""

from __future__ import annotations

import ast
import builtins
import itertools
import random
import re
import socket
import time
from pathlib import Path

import pytest
from builders import change, incorporation, material, unit

from effectivity import RULE_VERSION, Status, resolve
from effectivity.cli import load_table
from effectivity.model import (
    Change,
    IncomparableKeysError,
    Incorporation,
    KeyFormatError,
    MaterialState,
    Unit,
    compare_hold_points,
    key_in_range,
    parse_key,
)
from effectivity.resolve import RULE_TABLE, decide_pair

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "effectivity"
EXAMPLES = ROOT / "examples"

DISPOSITIONS = ["use_as_is", "rework", "scrap", "retrofit"]
# Unit hold position relative to incorporation hold HP020.
HOLDS = [("HP010", "open"), ("HP010", "closed"), ("HP020", "open"), ("HP020", "closed"),
         ("HP030", "open"), ("HP030", "closed")]
PREDECESSORS = ["open", "closed"]
WRONG_QTY = [(0, 0), (3, 0), (0, 3)]  # (staged, installed)
INCORPORATION = [None, False, True]


def full_matrix(key: str):
    """Every combination of the inputs that the rules look at, for one unit key."""
    for disp, (hp, hps), pred, (staged, installed), inc in itertools.product(
        DISPOSITIONS, HOLDS, PREDECESSORS, WRONG_QTY, INCORPORATION
    ):
        u = unit(effectivity_key=key, hold_point=hp, hold_point_status=hps,
                 predecessor_hold_status=pred)
        c = change(disposition=disp, replacement_part="" if disp in ("use_as_is", "scrap") else "PN-NEW")
        m = [material(received=9, staged=staged, installed=installed)]
        i = [] if inc is None else [incorporation(inc)]
        yield u, c, m, i


# --- Invariant 1 -------------------------------------------------------------

@pytest.mark.parametrize("key", ["0099", "0201", "0200A", "X0150", "99"])
def test_unit_outside_range_is_never_anything_but_out_of_effectivity(key: str) -> None:
    seen = 0
    for u, c, m, i in full_matrix(key):
        (d,) = resolve([u], [c], m, i)
        assert d.status is Status.OUT_OF_EFFECTIVITY, (u, c, m, i)
        assert d.rule_ids == ("R01",)
        seen += 1
    assert seen == 4 * 6 * 2 * 3 * 3


@pytest.mark.parametrize("key", ["0100", "0150", "0200"])
def test_range_bounds_are_inclusive(key: str) -> None:
    (d,) = resolve([unit(effectivity_key=key)], [change()], [], [])
    assert d.status is not Status.OUT_OF_EFFECTIVITY


# --- Invariant 2 -------------------------------------------------------------

def test_open_predecessor_never_yields_incorporated_for_any_input() -> None:
    checked = 0
    for u, c, m, i in full_matrix("0150"):
        if u.predecessor_hold_status != "open":
            continue
        (d,) = resolve([u], [c], m, i)
        assert d.status is not Status.INCORPORATED, (u, c, m, i)
        checked += 1
    assert checked > 0


@pytest.mark.parametrize("disposition", DISPOSITIONS)
@pytest.mark.parametrize("hold", HOLDS)
def test_incorporated_record_with_open_predecessor_is_a_data_error(disposition, hold) -> None:
    hp, hps = hold
    u = unit(hold_point=hp, hold_point_status=hps, predecessor_hold_status="open")
    c = change(disposition=disposition)
    (d,) = resolve([u], [c], [], [incorporation(True)])
    assert d.status is not Status.INCORPORATED
    assert d.reason_code == "DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR"
    assert d.rule_ids[0] == "R03" and len(d.rule_ids) == 2
    assert d.rule_ids[1] in {"R04", "R05", "R06", "R07", "R08", "R09", "R10"}


def test_incorporated_with_closed_predecessor_is_incorporated() -> None:
    (d,) = resolve([unit()], [change()], [], [incorporation(True)])
    assert (d.status, d.reason_code, d.rule_ids) == (Status.INCORPORATED, "INCORPORATED", ("R02",))


def test_incorporated_false_row_is_the_same_as_no_row() -> None:
    assert resolve([unit()], [change()], [], [incorporation(False)]) == resolve(
        [unit()], [change()], [], []
    )


def test_out_of_effectivity_wins_over_incorporation_data_error() -> None:
    u = unit(effectivity_key="0999", predecessor_hold_status="open")
    (d,) = resolve([u], [change()], [], [incorporation(True)])
    assert (d.status, d.rule_ids) == (Status.OUT_OF_EFFECTIVITY, ("R01",))


# --- Invariant 3 -------------------------------------------------------------

@pytest.mark.parametrize("disposition", DISPOSITIONS)
@pytest.mark.parametrize(
    "hold", [("HP030", "open"), ("HP030", "closed"), ("HP020", "closed")]
)
@pytest.mark.parametrize("pred", PREDECESSORS)
def test_passed_hold_point_without_incorporation_is_late(disposition, hold, pred) -> None:
    hp, hps = hold
    u = unit(hold_point=hp, hold_point_status=hps, predecessor_hold_status=pred)
    for rows in ([], [incorporation(False)]):
        (d,) = resolve([u], [change(disposition=disposition)], [], rows)
        assert d.status is Status.LATE
        assert d.status is not Status.INCORPORABLE
        assert d.rule_ids == ("R05",)


@pytest.mark.parametrize("disposition", ["rework", "retrofit", "scrap"])
def test_blocked_material_outranks_late(disposition) -> None:
    u = unit(hold_point="HP030", hold_point_status="closed")
    (d,) = resolve([u], [change(disposition=disposition)], [material(staged=1)], [])
    assert d.status is Status.BLOCKED_MATERIAL


def test_full_matrix_status_agrees_with_the_documented_order() -> None:
    """An independent restatement of the doc's decision order, checked on every combination."""
    for u, c, m, i in full_matrix("0150"):
        wrong = sum(r.qty_staged_at_work + r.qty_installed for r in m)
        inc_true = bool(i) and i[0].incorporated
        hp = parse_key(u.hold_point)
        target = parse_key(c.incorporation_hold_point)
        if inc_true and u.predecessor_hold_status == "closed":
            expected = Status.INCORPORATED
        elif wrong > 0 and c.disposition != "use_as_is":
            expected = Status.BLOCKED_MATERIAL
        elif hp > target or (hp == target and u.hold_point_status == "closed"):
            expected = Status.LATE
        elif hp < target or u.predecessor_hold_status == "open":
            expected = Status.NOT_YET_REACHED
        else:
            expected = Status.INCORPORABLE
        (d,) = resolve([u], [c], m, i)
        assert d.status is expected, (u, c, m, i, d)
        assert d.status in set(Status) and len(Status) == 6


# --- Invariant 6: determinism ------------------------------------------------

def test_same_inputs_same_decisions_regardless_of_row_order() -> None:
    units = [unit(unit_id=f"U{n}", effectivity_key=f"{100 + n:04d}") for n in range(8)]
    changes = [change(change_id=f"C{n}") for n in range(3)]
    mats = [material(unit_id=f"U{n}", staged=n % 2) for n in range(8)]
    baseline = resolve(units, changes, mats, [])
    rng = random.Random(7)
    for _ in range(10):
        shuffled = [list(x) for x in (units, changes, mats)]
        for part in shuffled:
            rng.shuffle(part)
        assert resolve(*shuffled, []) == baseline
    keys = [(d.unit_id, d.change_id) for d in baseline]
    assert keys == sorted(keys)


def test_example_data_covers_all_six_states_deterministically() -> None:
    def run() -> tuple:
        return resolve(
            load_table(EXAMPLES / "units.csv", Unit),
            load_table(EXAMPLES / "changes.csv", Change),
            load_table(EXAMPLES / "material.csv", MaterialState),
            load_table(EXAMPLES / "incorporations.csv", Incorporation),
        )

    first = run()
    assert first == run()
    assert {d.status for d in first} == set(Status)
    by_pair = {(d.unit_id, d.change_id): d for d in first}
    assert by_pair[("U-A02", "C-1002")].reason_code == "BLOCKED_RETROFIT_WRONG_MATERIAL"
    assert by_pair[("U-A04", "C-1001")].reason_code == "DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR"
    assert by_pair[("U-B02", "C-2001")].reason_code == "SCRAP_ONLY_NO_INSTALL"
    assert by_pair[("U-A03", "C-1001")].reason_code == "INCORPORABLE_REWORK"  # receipt only


def test_invalid_inputs_raise_instead_of_deciding() -> None:
    with pytest.raises(ValueError, match="duplicate unit_id"):
        resolve([unit(), unit()], [change()], [], [])
    with pytest.raises(ValueError, match="duplicate change_id"):
        resolve([unit()], [change(), change()], [], [])
    with pytest.raises(ValueError, match="duplicate incorporation"):
        resolve([unit()], [change()], [], [incorporation(), incorporation(False)])
    with pytest.raises(ValueError, match="unknown unit"):
        resolve([unit()], [change()], [], [incorporation(unit_id="NOPE")])
    with pytest.raises(ValueError, match="unknown change"):
        resolve([unit()], [change()], [], [incorporation(change_id="NOPE")])
    with pytest.raises(ValueError, match="unknown unit"):
        resolve([unit()], [change()], [material(unit_id="NOPE")], [])
    with pytest.raises(IncomparableKeysError):
        resolve([unit(hold_point="GATE020")], [change()], [], [])


# --- Invariant 7: no clock, network, or I/O in the decision function ----------

ALLOWED_RESOLVE_IMPORTS = {"__future__", "collections.abc", "effectivity.model"}
ALLOWED_MODEL_IMPORTS = {"__future__", "re", "enum", "typing", "pydantic"}
FORBIDDEN_CALLS = {"open", "print", "input", "eval", "exec", "__import__", "compile"}
FORBIDDEN_ATTRS = {"now", "today", "utcnow", "time", "monotonic", "perf_counter", "urlopen", "environ"}


def imported_modules(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.add(node.module or "")
    return found


def test_resolve_imports_only_the_allowlist() -> None:
    assert imported_modules(SRC / "resolve.py") <= ALLOWED_RESOLVE_IMPORTS


def test_model_imports_only_the_allowlist() -> None:
    assert imported_modules(SRC / "model.py") <= ALLOWED_MODEL_IMPORTS


@pytest.mark.parametrize("module", ["resolve.py", "model.py"])
def test_no_clock_or_io_calls_in_decision_modules(module: str) -> None:
    tree = ast.parse((SRC / module).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in FORBIDDEN_CALLS, node.func.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in FORBIDDEN_ATTRS, node.attr


def test_decision_function_takes_no_clock_parameter() -> None:
    import inspect

    for fn in (resolve, decide_pair):
        names = set(inspect.signature(fn).parameters)
        assert not names & {"now", "clock", "today", "timestamp", "run_at", "time"}


def test_resolve_runs_with_clock_network_and_open_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    u, c, m = unit(), change(), material(staged=1)
    expected = resolve([u], [c], [m], [])

    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("decision function touched the clock, network, or a file")

    for owner, name in [(time, "time"), (time, "monotonic"), (time, "perf_counter"),
                        (socket, "socket"), (socket, "create_connection"),
                        (builtins, "open")]:
        monkeypatch.setattr(owner, name, boom)
    assert resolve([u], [c], [m], []) == expected


# --- Doc and code agree -------------------------------------------------------

def test_state_machine_doc_matches_rule_table() -> None:
    doc = (ROOT / "docs" / "state-machine.md").read_text()
    assert f"`{RULE_VERSION}`" in doc
    rows = [line for line in doc.splitlines() if re.match(r"\| R\d\d \|", line)]
    doc_rules = {}
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        status = re.findall(r"`([a-z_]+)`", cells[2])
        doc_rules[cells[0]] = (
            Status(status[0]) if status else None,
            set(re.findall(r"`([A-Z][A-Z_]+)`", cells[3])),
        )
    code_rules = {rid: (st, set(codes)) for rid, (st, codes) in RULE_TABLE.items()}
    assert doc_rules == code_rules


# --- ADR 0001: key rule -------------------------------------------------------

@pytest.mark.parametrize(
    "bad",
    ["", " 123", "123 ", "12 3", "123a", "H-12", "123AB", "ABC", "-1", "123\n",
     "\u0661\u0662\u0663", "ABCDEFGHI1", "12A3", "é12"],
)
def test_malformed_keys_are_rejected_not_coerced(bad: str) -> None:
    with pytest.raises(KeyFormatError):
        parse_key(bad)
    with pytest.raises(ValueError):
        unit(effectivity_key=bad)


@pytest.mark.parametrize(
    "lesser,greater",
    [("99", "100"), ("123", "123A"), ("123A", "123B"), ("123B", "124"), ("0123", "0123A"),
     ("0123Z", "0124"), ("HP010", "HP020"), ("HP099", "HP100")],
)
def test_key_order_table(lesser: str, greater: str) -> None:
    assert parse_key(lesser) < parse_key(greater)
    assert not parse_key(greater) < parse_key(lesser)


def test_zero_padding_is_not_significant() -> None:
    assert parse_key("0123") == parse_key("123")
    assert parse_key("0123A") == parse_key("123A")


def test_suffix_hull_is_inside_range_that_is_not_an_integer_range() -> None:
    lo, hi = parse_key("0123"), parse_key("0124")
    assert key_in_range(parse_key("0123A"), lo, hi)
    assert not key_in_range(parse_key("0124A"), lo, hi)


def test_different_prefix_is_out_of_range_but_incomparable_as_hold_points() -> None:
    assert not key_in_range(parse_key("B0150"), parse_key("0100"), parse_key("0200"))
    with pytest.raises(IncomparableKeysError):
        compare_hold_points(parse_key("HP010"), parse_key("GATE010"))


@pytest.mark.parametrize(
    "lo,hi", [("0200", "0100"), ("A100", "B200"), ("0100", "bad")]
)
def test_bad_change_ranges_are_rejected(lo: str, hi: str) -> None:
    with pytest.raises(ValueError):
        change(effectivity_from=lo, effectivity_to=hi)


def _random_key(rng: random.Random, prefix: str) -> str:
    number = f"{rng.randint(0, 5000):0{rng.randint(4, 6)}d}"
    suffix = rng.choice(["", "", "A", "B", "Z"])
    return f"{prefix}{number}{suffix}"


def _padded(token: str) -> str:
    """Independent oracle: fixed-width padded string, compared as a string."""
    k = parse_key(token)
    return f"{k.prefix}{k.number:012d}{k.suffix}"


def test_generated_keys_order_range_and_roundtrip_properties() -> None:
    rng = random.Random(20260101)
    for _ in range(2000):
        prefix = rng.choice(["", "H", "SN"])
        a, b, k = (_random_key(rng, prefix) for _ in range(3))
        pa, pb, pk = parse_key(a), parse_key(b), parse_key(k)
        # tuple order agrees with the padded-string oracle, both ways
        assert (pa < pb) == (_padded(a) < _padded(b))
        assert (pa == pb) == (_padded(a) == _padded(b))
        # total order: exactly one of <, ==, >
        assert [pa < pb, pa == pb, pa > pb].count(True) == 1
        # range is inclusive and equals the oracle, whichever way the bounds were drawn
        lo, hi = sorted([pa, pb])
        assert key_in_range(lo, lo, hi) and key_in_range(hi, lo, hi)
        assert key_in_range(pk, lo, hi) == (min(_padded(a), _padded(b)) <= _padded(k)
                                            <= max(_padded(a), _padded(b)))
        # a bare number sorts before its lettered variants, which sort before number + 1
        n = parse_key(f"{prefix}{pa.number:06d}")
        assert n < parse_key(f"{prefix}{pa.number:06d}A") < parse_key(f"{prefix}{pa.number + 1:06d}")
        # a different prefix is never in range
        assert not key_in_range(parse_key("Q" + prefix + "0001"), lo, hi)
