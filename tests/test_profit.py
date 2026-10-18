"""Tests for effectivity.profit: packaging, pricing, upgrades, retention,
ledger, dashboard. Shared vectors in tests/profit-vectors.json are also
asserted by lib/profit.test.ts, so the Python and TypeScript
implementations cannot drift apart."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from effectivity import profit

ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads((ROOT / "tests" / "profit-vectors.json").read_text())


def test_profit_module_is_pure_no_clock_fs_network_logging_or_random() -> None:
    tree = ast.parse((ROOT / "src" / "effectivity" / "profit.py").read_text())
    imported = {
        n.module or ""
        for n in ast.walk(tree)
        if isinstance(n, (ast.Import, ast.ImportFrom))
        for n in ([n] if isinstance(n, ast.ImportFrom) else [])
    }
    imported |= {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    assert imported <= {"__future__", "typing"}, imported
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "print", "exec", "eval", "__import__"}


def test_profit_module_never_imports_the_resolver() -> None:
    tree = ast.parse((ROOT / "src" / "effectivity" / "profit.py").read_text())
    imported = {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    imported |= {
        n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
    }
    assert "effectivity.resolve" not in imported
    assert "effectivity.report" not in imported


def test_price_quotes_match_shared_vectors() -> None:
    for vector in VECTORS["price_quotes"]:
        assert profit.price_quote(vector["package_id"], vector["cycle"]) == vector


def test_billing_is_off_and_no_quote_ever_charges() -> None:
    assert profit.BILLING_ENABLED is False
    for package_id in profit.PACKAGE_ORDER:
        for cycle in ("monthly", "annual"):
            quote = profit.price_quote(package_id, cycle)
            assert quote["charge_amount_cents"] == 0
            assert quote["billing_enabled"] is False
            assert quote["status"] == "proposed_not_charged"


def test_price_quote_rejects_unknown_package_and_cycle() -> None:
    with pytest.raises(ValueError):
        profit.price_quote("nope", "monthly")
    with pytest.raises(ValueError):
        profit.price_quote("pilot", "weekly")


def test_annual_price_equals_ten_monthly_payments() -> None:
    for package_id in profit.PACKAGE_ORDER:
        monthly = profit.price_quote(package_id, "monthly")["proposed_cents"]
        annual = profit.price_quote(package_id, "annual")["proposed_cents"]
        assert annual == 10 * monthly


def test_upgrade_kinds_match_shared_vectors() -> None:
    for vector in VECTORS["upgrade_kinds"]:
        path = profit.upgrade_path(vector["current_id"], vector["target_id"])
        assert path["kind"] == vector["kind"]
        assert path["current_id"] == vector["current_id"]
        assert path["target_id"] == vector["target_id"]


def test_upgrade_path_steps_and_limits_change() -> None:
    path = profit.upgrade_path("library", "pilot")
    assert path["steps"][0].startswith("Confirm the move")
    assert path["limits_change"]["units"] == {"from": 50, "to": 250}
    assert path["limits_change"]["seats"] == {"from": 1, "to": 5}
    same = profit.upgrade_path("pilot", "pilot")
    assert same["steps"] == ["No change: the current package already applies."]
    assert same["limits_change"] == {}
    downgrade = profit.upgrade_path("per_programme", "pilot")
    assert any("not a refund" in step for step in downgrade["steps"])


def test_upgrade_eligibility_blocks_over_limit_usage() -> None:
    ok = profit.upgrade_eligibility("library", "pilot", {"units": 10, "changes": 5})
    assert ok["allowed"] is True
    assert ok["blockers"] == []
    blocked = profit.upgrade_eligibility("per_programme", "pilot", {"units": 900})
    assert blocked["allowed"] is False
    assert len(blocked["blockers"]) == 1
    assert "900" in blocked["blockers"][0] and "250" in blocked["blockers"][0]


def test_retention_scores_match_shared_vectors() -> None:
    for vector in VECTORS["retention"]:
        got = profit.retention_score(vector["periods"])
        assert got["score"] == vector["score"]
        assert got["band"] == vector["band"]
        assert got["active_periods"] == vector["active_periods"]
        assert got["value_events"] == vector["value_events"]


def test_retention_caps_and_empty_input() -> None:
    busy = [{"runs": 9, "blocked_material": 99, "late": 99} for _ in range(9)]
    assert profit.retention_score(busy)["score"] == 100
    assert profit.retention_score([]) == {
        "score": 0,
        "band": "dormant",
        "active_periods": 0,
        "periods_supplied": 0,
        "recent_active": False,
        "value_events": 0,
    }


def test_ledger_summary_matches_shared_vectors() -> None:
    vector = VECTORS["ledger"]
    summary = profit.ledger_summary(vector["entries"])
    assert summary["entries"] == vector["summary"]["entries"]
    assert summary["totals"] == vector["summary"]["totals"]
    assert summary["by_kind"] == vector["summary"]["by_kind"]
    assert summary["revenue"]["real_revenue_cents"] == 0
    assert summary["revenue"]["billing_enabled"] is False


def test_ledger_validation_rejects_bad_entries() -> None:
    base = VECTORS["ledger"]["entries"][0]
    assert profit.validate_ledger([dict(base)]) == []
    dup = [dict(base), dict(base)]
    assert any("duplicate" in p for p in profit.validate_ledger(dup))
    no_evidence = dict(base, evidence_ref="")
    assert any("evidence_ref" in p for p in profit.validate_ledger([no_evidence]))
    negative = dict(base, entry_id="X1", blocked_material=-1)
    assert any("blocked_material" in p for p in profit.validate_ledger([negative]))
    bad_kind = dict(base, entry_id="X2", kind="sale")
    assert any("kind" in p for p in profit.validate_ledger([bad_kind]))
    with pytest.raises(ValueError):
        profit.ledger_summary([dict(base), dict(base)])


def test_dashboard_empty_funnel_reports_null_rates_not_estimates() -> None:
    vector = VECTORS["dashboard"]
    summary = profit.dashboard_summary(
        package_id=vector["package_id"],
        usage=vector["usage"],
        ledger_entries=VECTORS["ledger"]["entries"],
    )
    assert summary["funnel"] == {
        "visitors": 0,
        "trials_started": 0,
        "pilots_started": 0,
        "paid_programmes": 0,
        "conversion": {
            "visitor_to_trial": None,
            "trial_to_pilot": None,
            "pilot_to_paid": None,
            "visitor_to_paid": None,
        },
    }
    assert summary["billing"]["real_revenue_cents"] == 0
    assert summary["billing"]["next_charge_cents"] == 0
    assert summary["usage_vs_limits"]["units"]["percent"] == vector["units_percent"]


def test_dashboard_conversion_rates_with_supplied_funnel() -> None:
    summary = profit.dashboard_summary(
        package_id="pilot",
        usage={},
        ledger_entries=[],
        funnel={"visitors": 100, "trials_started": 20, "pilots_started": 5, "paid_programmes": 1},
    )
    assert summary["funnel"]["conversion"] == {
        "visitor_to_trial": 0.2,
        "trial_to_pilot": 0.25,
        "pilot_to_paid": 0.2,
        "visitor_to_paid": 0.01,
    }
    assert summary["retention"]["band"] == "dormant"


def test_dashboard_flags_over_limit_usage() -> None:
    summary = profit.dashboard_summary(
        package_id="library", usage={"units": 51}, ledger_entries=[]
    )
    assert summary["usage_vs_limits"]["units"]["over"] is True
    assert summary["usage_vs_limits"]["units"]["percent"] == 102
