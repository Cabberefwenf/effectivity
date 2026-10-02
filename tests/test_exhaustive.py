"""Exhaustive cross-check of the state machine against an independent reference.

The reference below is written from docs/state-machine.md as a plain ordered
decision table over abstract features. It does not import `resolve`, the rule
table, or any key parsing: every concrete key and hold point in the domains has
its expected relation hard-coded by hand.
"""

from __future__ import annotations

import itertools

import pytest
from builders import change, incorporation, material, unit

from effectivity import Status, resolve
from effectivity.resolve import RULE_TABLE

# --- Domains (small, but every boundary is in them) ---------------------------

# Change range is 0123 .. 0125A inclusive; hand-written expectation per key.
KEYS = {
    "0122": False,    # just below from
    "0123": True,     # exactly from
    "123": True,      # from, written without padding
    "0123A": True,    # suffix variant just above from
    "0124": True,     # inside
    "0125": True,     # just below to
    "0125A": True,    # exactly to
    "0125B": False,   # just above to
    "0126": False,    # above to
    "B0124": False,   # other series, numerically inside
}
# Incorporation hold point is HP020. Hand-written position of the unit's hold.
HOLDS = {
    "HP010": -1, "HP019A": -1, "HP2": -1,
    "HP020": 0, "HP20": 0, "HP0020": 0,
    "HP020A": 1, "HP021": 1, "HP030": 1, "HP100": 1,   # HP100 > HP20 numerically
}
HOLD_STATUSES = ["open", "closed"]
PREDECESSORS = ["open", "closed"]
DISPOSITIONS = ["use_as_is", "rework", "scrap", "retrofit"]
MATERIALS = {   # name -> (received, staged, installed)
    "none": None,
    "receipt_only": (5, 0, 0),
    "staged": (0, 3, 0),
    "installed": (0, 0, 2),
    "mix": (4, 1, 1),
}
INCORPORATIONS = {"absent": None, "true": True, "false": False}


# --- Reference implementation: a straight ordered decision table --------------

def reference(in_range, pos, hold_status, pred, disposition, wrong, inc):
    """Return (status, reason_code, rule_ids). Written from the doc, row by row."""
    flagged = inc == "true" and pred == "open"
    passed = pos > 0 or (pos == 0 and hold_status == "closed")
    d = disposition.upper()

    def r(status, reason, rule):
        if flagged:
            return (status, "DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR", ("R03", rule))
        return (status, reason, (rule,))

    if not in_range:
        return ("out_of_effectivity", "OUT_OF_EFFECTIVITY", ("R01",))
    if inc == "true" and pred == "closed":
        return ("incorporated", "INCORPORATED", ("R02",))
    if wrong and disposition in ("rework", "retrofit", "scrap"):
        return r("blocked_material", f"BLOCKED_{d}_WRONG_MATERIAL", "R04")
    if passed:
        return r("late", "LATE_HOLD_POINT_PASSED", "R05")
    if pos < 0:
        return r("not_yet_reached", "NOT_YET_REACHED_BEFORE_HOLD_POINT", "R06")
    if pred == "open":
        return r("not_yet_reached", "NOT_YET_REACHED_PREDECESSOR_OPEN", "R07")
    if disposition in ("rework", "retrofit"):
        return r("incorporable", f"INCORPORABLE_{d}", "R08")
    if disposition == "use_as_is":
        return r("incorporable", "INCORPORABLE_USE_AS_IS_NO_REWORK", "R09")
    return r("incorporable", "SCRAP_ONLY_NO_INSTALL", "R10")


def cases():
    changes = {
        d: change(
            effectivity_from="0123", effectivity_to="0125A", incorporation_hold_point="HP020",
            disposition=d, replacement_part="PN-NEW" if d in ("rework", "retrofit") else "",
        )
        for d in DISPOSITIONS
    }
    for key, hold, hs, pred in itertools.product(KEYS, HOLDS, HOLD_STATUSES, PREDECESSORS):
        u = unit(effectivity_key=key, hold_point=hold, hold_point_status=hs,
                 predecessor_hold_status=pred)
        for disp, (mname, mrow), (iname, ival) in itertools.product(
            DISPOSITIONS, MATERIALS.items(), INCORPORATIONS.items()
        ):
            mats = [] if mrow is None else [material(*mrow)]
            incs = [] if ival is None else [incorporation(ival)]
            wrong = mrow is not None and (mrow[1] + mrow[2]) > 0
            yield (u, changes[disp], mats, incs,
                   dict(key=key, hold=hold, hs=hs, pred=pred, disp=disp, mat=mname, inc=iname),
                   reference(KEYS[key], HOLDS[hold], hs, pred, disp, wrong, iname))


ALL = list(cases())
SIX = {s.value for s in Status}
INSTALL_RECOMMENDING = {"INCORPORABLE_REWORK", "INCORPORABLE_RETROFIT"}


def test_domain_size_is_what_the_doc_of_this_test_says() -> None:
    assert len(ALL) == 10 * 10 * 2 * 2 * 4 * 5 * 3 == 24000


def test_resolve_equals_independent_reference_on_every_combination() -> None:
    mismatches = []
    for u, c, mats, incs, label, expected in ALL:
        (d,) = resolve([u], [c], mats, incs)
        got = (d.status.value, d.reason_code, d.rule_ids)
        if got != expected:
            mismatches.append((label, got, expected))
    assert not mismatches, mismatches[:5]


def test_every_state_and_every_rule_is_reachable_in_the_domain() -> None:
    assert {e[0] for *_, e in ALL} == SIX
    fired = {rid for *_, e in ALL for rid in e[2]}
    assert fired == set(RULE_TABLE)
    codes = {e[1] for *_, e in ALL}
    assert codes == {c for _, cs in RULE_TABLE.values() for c in cs}


def test_invariants_1_to_6_hold_on_every_combination() -> None:
    for u, c, mats, incs, label, _expected in ALL:
        (d,) = resolve([u], [c], mats, incs)
        status, code = d.status.value, d.reason_code
        in_range = KEYS[label["key"]]
        wrong = bool(mats) and (mats[0].qty_staged_at_work + mats[0].qty_installed) > 0
        disp = label["disp"]
        assert status in SIX

        # 1. outside the range: out_of_effectivity and nothing else
        if not in_range:
            assert status == "out_of_effectivity", label
        else:
            assert status != "out_of_effectivity", label

        # 2. open predecessor: never incorporated; the contradiction is surfaced
        if label["pred"] == "open":
            assert status != "incorporated", label
            if in_range and label["inc"] == "true":
                assert code == "DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR", label

        # 3. passed the hold point and not incorporated: late, unless blocked
        pos = HOLDS[label["hold"]]
        passed = pos > 0 or (pos == 0 and label["hs"] == "closed")
        if in_range and passed and status != "incorporated":
            blocked = wrong and disp != "use_as_is"
            assert status == ("blocked_material" if blocked else "late"), label
            assert status != "incorporable", label

        # 4. receipt alone never blocks
        if label["mat"] in ("none", "receipt_only"):
            assert status != "blocked_material", label
        if status == "blocked_material":
            assert wrong, label

        # 5. dispositions
        if disp == "scrap":
            assert code not in INSTALL_RECOMMENDING, label
            if status == "incorporable":
                assert code == "SCRAP_ONLY_NO_INSTALL", label
        if disp == "use_as_is":
            assert status != "blocked_material", label
            assert "R04" not in d.rule_ids, label
            assert "REWORK" not in code.replace("NO_REWORK", ""), label
        # (a data-error overlay replaces the code; the determining rule stays in rule_ids)
        if (disp in ("rework", "retrofit") and status in ("blocked_material", "incorporable")
                and "R03" not in d.rule_ids):
            assert disp.upper() in code, label
            assert ("RETROFIT" in code) == (disp == "retrofit"), label

        # 6. same inputs, same decision
        assert resolve([u], [c], mats, incs) == (d,), label

        # structure: rule ids are real, the last one decides the status, codes belong to rules
        assert d.rule_ids[-1] in RULE_TABLE
        decided, codes_of_rule = RULE_TABLE[d.rule_ids[-1]]
        assert decided is d.status
        if "R03" in d.rule_ids:
            assert d.rule_ids[0] == "R03" and len(d.rule_ids) == 2
            assert code in RULE_TABLE["R03"][1]
        else:
            assert len(d.rule_ids) == 1 and code in codes_of_rule


@pytest.mark.parametrize("disposition", DISPOSITIONS)
def test_whole_table_in_one_call_matches_per_pair_calls(disposition: str) -> None:
    """resolve over many units and changes equals the per-pair decisions, sorted."""
    pairs = [(u, c, m, i, lab, exp) for u, c, m, i, lab, exp in ALL
             if lab["disp"] == disposition and lab["mat"] == "staged" and lab["inc"] == "absent"]
    units = []
    for n, (u, *_rest) in enumerate(pairs):
        units.append(u.model_copy(update={"unit_id": f"U{n:04d}"}))
    c = pairs[0][1]
    mats = [material(0, 3, 0, unit_id=u.unit_id) for u in units]
    got = resolve(units, [c], mats, [])
    assert [(d.status.value, d.reason_code, d.rule_ids) for d in got] == [p[5] for p in pairs]
