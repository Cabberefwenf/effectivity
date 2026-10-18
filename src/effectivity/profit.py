"""Profit systems for effectivity: packaging, pricing, upgrades, retention,
ledger of value delivered, and dashboard aggregates.

This module is pure. It reads no clock, filesystem, network, or log, and it
takes no randomness. Every time dependent value (period labels, recorded-at
labels) is supplied by the caller, so the same inputs always give the same
outputs. It never decides a unit/change pair and never imports the resolver.

Honesty rules, enforced by the code, not just by docs:

* Billing is OFF. There is no charge path. ``price_quote`` returns a
  PROPOSED price and ``charge_amount_cents`` is always 0.
* Real revenue is always 0. The ledger records usage and value delivered
  (runs, decisions, blocked material caught, late units surfaced), never
  revenue. Nothing here claims a customer, a sale, or a measured result.
* Money is integer cents. No floats carry money.
* The dashboard only aggregates numbers the caller supplies. With no
  supplied data it reports zeros and null conversion rates, not estimates.
"""

from __future__ import annotations

from typing import Any

BILLING_ENABLED = False

PACKAGE_ORDER = ("library", "pilot", "per_programme")

# Proposed prices only. Annual equals 10 monthly payments. Nothing is
# charged: BILLING_ENABLED is False and price_quote always returns a
# charge of 0.
PACKAGES: dict[str, dict[str, Any]] = {
    "library": {
        "id": "library",
        "name": "Library",
        "tagline": "Read the rules and run the bundled synthetic sample.",
        "monthly_cents": 0,
        "annual_cents": 0,
        "limits": {
            "programmes": 1,
            "units": 50,
            "changes": 10,
            "pairs": 100,
            "seats": 1,
        },
        "features": [
            "Rule text and worked example",
            "Bundled synthetic sample only",
            "No exports beyond the on screen result",
        ],
    },
    "pilot": {
        "id": "pilot",
        "name": "Pilot",
        "tagline": "One programme, one trial period, with a value ledger.",
        "monthly_cents": 49000,
        "annual_cents": 490000,
        "limits": {
            "programmes": 1,
            "units": 250,
            "changes": 50,
            "pairs": 5000,
            "seats": 5,
        },
        "features": [
            "One programme for one trial period",
            "JSON download of each run",
            "Value ledger: runs, blocked material, late units",
            "Dashboard: usage, conversion, retention",
        ],
    },
    "per_programme": {
        "id": "per_programme",
        "name": "Per programme",
        "tagline": "One licence per programme, priced per programme.",
        "monthly_cents": 190000,
        "annual_cents": 1900000,
        "limits": {
            "programmes": 1,
            "units": 1000,
            "changes": 200,
            "pairs": 5000,
            "seats": 25,
        },
        "features": [
            "One licence per programme",
            "JSON and CSV download of each run",
            "Value ledger with evidence references",
            "Dashboard: usage, conversion, retention",
            "Upgrade and downgrade flows with ledger entries",
        ],
    },
}

LIMIT_KEYS = ("programmes", "units", "changes", "pairs", "seats")

LEDGER_KINDS = ("run", "upgrade", "downgrade", "renewal", "pilot_start", "pilot_end", "note")

RETENTION_BANDS = ("strong", "steady", "at_risk", "dormant")


def get_package(package_id: str) -> dict[str, Any]:
    """Return the package definition for a known id, else raise ValueError."""
    try:
        return PACKAGES[package_id]
    except KeyError:
        raise ValueError(f"Unknown package: {package_id}") from None


def price_quote(package_id: str, cycle: str) -> dict[str, Any]:
    """Proposed price for a package and billing cycle.

    ``cycle`` is "monthly" or "annual". The returned quote always has
    ``billing_enabled`` False and ``charge_amount_cents`` 0: quoting is not
    charging, and there is no charge path in this codebase.
    """
    package = get_package(package_id)
    if cycle not in ("monthly", "annual"):
        raise ValueError(f"Unknown billing cycle: {cycle}")
    proposed = package["monthly_cents"] if cycle == "monthly" else package["annual_cents"]
    return {
        "package_id": package_id,
        "cycle": cycle,
        "proposed_cents": proposed,
        "billing_enabled": BILLING_ENABLED,
        "charge_amount_cents": 0,
        "status": "proposed_not_charged",
    }


def _tier_index(package_id: str) -> int:
    return PACKAGE_ORDER.index(get_package(package_id)["id"])


def upgrade_path(current_id: str, target_id: str) -> dict[str, Any]:
    """Ordered steps to move from one package to another.

    Upgrades and downgrades both go through the ledger: the move is
    recorded with a reason before the new limits apply. A downgrade is
    not a refund path; it only changes the limits from the next run.
    """
    current = get_package(current_id)
    target = get_package(target_id)
    if current_id == target_id:
        return {
            "current_id": current_id,
            "target_id": target_id,
            "kind": "same",
            "steps": ["No change: the current package already applies."],
            "limits_change": {},
        }
    direction = "upgrade" if _tier_index(target_id) > _tier_index(current_id) else "downgrade"
    steps = [
        f"Confirm the move from {current['name']} to {target['name']} with a reason.",
        "Check current usage fits inside the target limits.",
        "Record the move in the value ledger with the reason.",
        "Apply the new limits from the next run.",
        "Review the dashboard after the first run on the new package.",
    ]
    if direction == "downgrade":
        steps.insert(
            2,
            "Confirm the downgrade is not a refund: past periods keep their terms.",
        )
    limits_change = {
        key: {"from": current["limits"][key], "to": target["limits"][key]}
        for key in LIMIT_KEYS
        if current["limits"][key] != target["limits"][key]
    }
    return {
        "current_id": current_id,
        "target_id": target_id,
        "kind": direction,
        "steps": steps,
        "limits_change": limits_change,
    }


def upgrade_eligibility(
    current_id: str, target_id: str, usage: dict[str, int]
) -> dict[str, Any]:
    """Whether a move is allowed for the supplied usage.

    A move is blocked only when supplied usage exceeds a target limit.
    Usage keys not in LIMIT_KEYS are ignored. Missing usage keys count
    as zero. The caller supplies usage; this function measures nothing.
    """
    target = get_package(target_id)
    get_package(current_id)
    blockers = [
        f"Usage {key} is {usage.get(key, 0)}, above the {target['name']} limit "
        f"of {target['limits'][key]}."
        for key in LIMIT_KEYS
        if usage.get(key, 0) > target["limits"][key]
    ]
    return {
        "current_id": current_id,
        "target_id": target_id,
        "allowed": not blockers,
        "blockers": blockers,
    }


def retention_score(periods: list[dict[str, int]]) -> dict[str, Any]:
    """Descriptive retention score from caller supplied per period usage.

    Each period is ``{"runs": int, "blocked_material": int, "late": int}``.
    The score describes the supplied usage only. It predicts nothing and
    claims no customer behaviour. Bands: strong >= 80, steady >= 50,
    at risk >= 25, else dormant.
    """
    active_periods = sum(1 for p in periods if p.get("runs", 0) > 0)
    recent_active = bool(periods) and periods[-1].get("runs", 0) > 0
    value_events = sum(p.get("blocked_material", 0) + p.get("late", 0) for p in periods)
    score = min(100, 20 * min(active_periods, 3) + (15 if recent_active else 0) + min(25, 5 * min(value_events, 5)))
    band = "strong" if score >= 80 else "steady" if score >= 50 else "at_risk" if score >= 25 else "dormant"
    return {
        "score": score,
        "band": band,
        "active_periods": active_periods,
        "periods_supplied": len(periods),
        "recent_active": recent_active,
        "value_events": value_events,
    }


def validate_ledger(entries: list[dict[str, Any]]) -> list[str]:
    """Return a list of problems with ledger entries. Empty means valid."""
    problems: list[str] = []
    seen: set[str] = set()
    count_keys = ("units", "changes", "decisions", "blocked_material", "late_surfaced", "incorporated")
    for i, entry in enumerate(entries):
        where = f"entry {i}"
        entry_id = entry.get("entry_id")
        if not isinstance(entry_id, str) or not entry_id:
            problems.append(f"{where}: entry_id must be a non-empty string.")
        elif entry_id in seen:
            problems.append(f"{where}: duplicate entry_id {entry_id}.")
        else:
            seen.add(entry_id)
        if entry.get("kind") not in LEDGER_KINDS:
            problems.append(f"{where}: kind must be one of {', '.join(LEDGER_KINDS)}.")
        if entry.get("kind") == "run" and not entry.get("evidence_ref"):
            problems.append(f"{where}: a run entry needs an evidence_ref.")
        for key in count_keys:
            value = entry.get(key, 0)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                problems.append(f"{where}: {key} must be a non-negative integer.")
    return problems


def ledger_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate a validated ledger into proof of value delivered.

    Revenue is always zero here: billing is off and this ledger never
    records money. The totals are counts of work done and problems
    surfaced, each tied to the entry evidence references.
    """
    problems = validate_ledger(entries)
    if problems:
        raise ValueError("; ".join(problems))
    totals = {
        key: sum(e.get(key, 0) for e in entries)
        for key in ("units", "changes", "decisions", "blocked_material", "late_surfaced", "incorporated")
    }
    by_kind: dict[str, int] = {}
    for entry in entries:
        by_kind[entry["kind"]] = by_kind.get(entry["kind"], 0) + 1
    return {
        "entries": len(entries),
        "totals": totals,
        "by_kind": by_kind,
        "evidence_refs": [e.get("evidence_ref", "") for e in entries if e.get("evidence_ref")],
        "revenue": {
            "real_revenue_cents": 0,
            "claimed_revenue_cents": 0,
            "billing_enabled": BILLING_ENABLED,
        },
    }


def _conversion(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def dashboard_summary(
    *,
    package_id: str,
    usage: dict[str, int],
    ledger_entries: list[dict[str, Any]],
    funnel: dict[str, int] | None = None,
    retention_periods: list[dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Dashboard aggregates from caller supplied data.

    ``funnel`` counts are visitors, trials started, pilots started, and
    paid programmes. They default to zero: this site runs no analytics,
    so an empty funnel reports null conversion rates rather than
    inventing a rate. ``usage`` is compared against the package limits.
    """
    package = get_package(package_id)
    funnel = funnel or {}
    visitors = funnel.get("visitors", 0)
    trials = funnel.get("trials_started", 0)
    pilots = funnel.get("pilots_started", 0)
    paid = funnel.get("paid_programmes", 0)
    usage_vs_limits = {
        key: {
            "used": usage.get(key, 0),
            "limit": package["limits"][key],
            "over": usage.get(key, 0) > package["limits"][key],
            "percent": (usage.get(key, 0) * 100 // package["limits"][key])
            if package["limits"][key] > 0
            else None,
        }
        for key in LIMIT_KEYS
    }
    return {
        "package": {"id": package_id, "name": package["name"]},
        "usage_vs_limits": usage_vs_limits,
        "retention": retention_score(retention_periods or []),
        "ledger": ledger_summary(ledger_entries),
        "funnel": {
            "visitors": visitors,
            "trials_started": trials,
            "pilots_started": pilots,
            "paid_programmes": paid,
            "conversion": {
                "visitor_to_trial": _conversion(trials, visitors),
                "trial_to_pilot": _conversion(pilots, trials),
                "pilot_to_paid": _conversion(paid, pilots),
                "visitor_to_paid": _conversion(paid, visitors),
            },
        },
        "billing": {
            "billing_enabled": BILLING_ENABLED,
            "real_revenue_cents": 0,
            "next_charge_cents": 0,
        },
        "honesty": (
            "No paying customers are claimed. Revenue is zero until a real "
            "charge is recorded through billing, which is off."
        ),
    }
