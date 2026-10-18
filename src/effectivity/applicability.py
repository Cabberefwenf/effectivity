"""Applicability first: which changes a unit is subject to, before effectivity.

ADR 0004. This module never decides a (unit, change) pair; it only removes
pairs that do not apply. The core decisions (R01 to R10 in
``effectivity.resolve``) are unchanged, and the six states are unchanged.

Applicability answers "does this change concern this unit at all", usually
because of program, variant, or configuration. Effectivity (R01) answers
"is this unit inside this change's serial or hull range". A pair must pass
both: applicability first, then effectivity.

Rules are explicit rows, never inferred:

- A rule names one change and one program, and says whether the change
  applies to that program (rule A01).
- A rule may name program ``"*"`` as a wildcard for every program (rule
  A02). An explicit rule for a program beats the wildcard for that program.
- A change with no rule for a unit's program applies by default (rule A03).

No clock, no network, no randomness. Pure functions of parsed models.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from effectivity.model import Change, Text, Unit

APPLICABILITY_VERSION = "1.0.0"

# Rule ids for the applicability layer. A01/A02/A03 are in docs/applicability.md.
A_EXPLICIT = "A01"
A_WILDCARD = "A02"
A_DEFAULT = "A03"

WILDCARD_PROGRAM = "*"


def _applies_bool(value: Any) -> Any:
    """Accept a real bool or the exact strings 'true' / 'false'; reject the rest."""

    if isinstance(value, bool):
        return value
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError("applies must be exactly 'true' or 'false'")


class ApplicabilityRule(BaseModel):
    """One applicability row: change ``change_id`` applies (or not) to ``program``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: Text
    program: Text
    applies: bool

    @field_validator("applies", mode="before")
    @classmethod
    def _literal_bool(cls, value: Any) -> Any:
        return _applies_bool(value)


def validate_applicability_rules(
    rules: Sequence[ApplicabilityRule],
    changes: Sequence[Change],
    units: Sequence[Unit],
) -> None:
    """Reject rules that contradict the tables they are read against.

    Duplicate (change_id, program) rows are errors: two rows saying
    different things about the same pair would need a tie-break, and this
    system never breaks ties silently. A rule naming an unknown change, or a
    program no unit has (other than the wildcard), is an error, same as an
    incorporation row naming an unknown unit in the core resolver.
    """

    change_ids = {c.change_id for c in changes}
    programs = {u.program for u in units}
    seen: set[tuple[str, str]] = set()
    for rule in rules:
        if rule.change_id not in change_ids:
            raise ValueError(f"applicability rule names unknown change {rule.change_id!r}")
        if rule.program != WILDCARD_PROGRAM and rule.program not in programs:
            raise ValueError(f"applicability rule names unknown program {rule.program!r}")
        key = (rule.change_id, rule.program)
        if key in seen:
            raise ValueError(f"duplicate applicability rule for {key!r}")
        seen.add(key)


def applies_to(
    rules: Sequence[ApplicabilityRule], change_id: str, program: str
) -> tuple[bool, str]:
    """Decide one (change, program) pair. Returns (applies, rule id)."""

    wildcard: ApplicabilityRule | None = None
    for rule in rules:
        if rule.change_id != change_id:
            continue
        if rule.program == program:
            return rule.applies, A_EXPLICIT
        if rule.program == WILDCARD_PROGRAM:
            wildcard = rule
    if wildcard is not None:
        return wildcard.applies, A_WILDCARD
    return True, A_DEFAULT


def applicability_map(
    units: Sequence[Unit],
    changes: Sequence[Change],
    rules: Sequence[ApplicabilityRule],
) -> dict[tuple[str, str], tuple[bool, str]]:
    """Every (unit_id, change_id) pair mapped to (applies, rule id)."""

    validate_applicability_rules(rules, changes, units)
    return {
        (unit.unit_id, change.change_id): applies_to(rules, change.change_id, unit.program)
        for unit in units
        for change in changes
    }


def excluded_pairs(
    units: Sequence[Unit],
    changes: Sequence[Change],
    rules: Sequence[ApplicabilityRule],
) -> list[dict[str, str]]:
    """Pairs applicability removes, sorted, with the rule that removed each one."""

    mapping = applicability_map(units, changes, rules)
    program_by_unit = {u.unit_id: u.program for u in units}
    excluded = []
    for (unit_id, change_id), (applies, rule_id) in sorted(mapping.items()):
        if applies:
            continue
        if rule_id == A_EXPLICIT:
            reason = f"change {change_id} does not apply to program {program_by_unit[unit_id]}"
        else:
            reason = f"change {change_id} does not apply to any program (wildcard rule)"
        excluded.append(
            {"unit_id": unit_id, "change_id": change_id, "rule_id": rule_id, "reason": reason}
        )
    return excluded
