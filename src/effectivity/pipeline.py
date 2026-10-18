"""Extended pipeline: applicability filter, core resolve, conflict pass.

ADR 0004. Order matters and is fixed:

1. Validate the optional applicability and supersession tables.
2. Run the core resolver (R01 to R10) on every pair. Its decisions are
   never rewritten by this pipeline.
3. Drop pairs applicability excludes. Excluded pairs are listed, not
   silently hidden: the report carries them with the rule that excluded
   each one.
4. Run the conflict pass over the pairs that remain. A conflict BLOCKs
   the run; it does not pick a winner.

The report carries both hashes: ``input_hash`` is the core hash over the
four tables (identical to the core run log, so an extended run stays
linked to its core run), and ``extended_input_hash`` also covers the
applicability and supersession tables, so two runs with different
applicability rules can never share a hash.

No clock, no network, no randomness. Pure functions of parsed models.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from effectivity.applicability import (
    APPLICABILITY_VERSION,
    ApplicabilityRule,
    applicability_map,
    excluded_pairs,
)
from effectivity.conflicts import (
    CONFLICT_VERSION,
    Conflict,
    Supersession,
    find_conflicts,
)
from effectivity.log import input_hash
from effectivity.model import Change, Decision, Incorporation, MaterialState, Unit
from effectivity.resolve import RULE_VERSION, resolve

PIPELINE_VERSION = "1.0.0"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def extended_input_hash(
    units: Sequence[Unit],
    changes: Sequence[Change],
    material: Sequence[MaterialState],
    incorporations: Sequence[Incorporation],
    applicability_rules: Sequence[ApplicabilityRule] = (),
    supersessions: Sequence[Supersession] = (),
) -> str:
    """SHA-256 over the core hash plus the two optional tables, row order free."""

    payload = {
        "core_input_hash": input_hash(units, changes, material, incorporations),
        "applicability": sorted(
            _canonical(r.model_dump(mode="json")) for r in applicability_rules
        ),
        "supersession": sorted(_canonical(e.model_dump(mode="json")) for e in supersessions),
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def run_extended(
    units: Sequence[Unit],
    changes: Sequence[Change],
    material: Sequence[MaterialState],
    incorporations: Sequence[Incorporation],
    *,
    applicability_rules: Sequence[ApplicabilityRule] = (),
    supersessions: Sequence[Supersession] = (),
) -> dict[str, Any]:
    """Run the extended pipeline and return a JSON-ready report."""

    mapping = applicability_map(units, changes, applicability_rules)
    all_decisions = resolve(units, changes, material, incorporations)
    kept = [d for d in all_decisions if mapping[(d.unit_id, d.change_id)][0]]
    conflicts: list[Conflict] = find_conflicts(kept, changes, supersessions)
    return {
        "pipeline_version": PIPELINE_VERSION,
        "rule_version": RULE_VERSION,
        "applicability_version": APPLICABILITY_VERSION,
        "conflict_version": CONFLICT_VERSION,
        "input_hash": input_hash(units, changes, material, incorporations),
        "extended_input_hash": extended_input_hash(
            units, changes, material, incorporations, applicability_rules, supersessions
        ),
        "inputs": {
            "units": len(units),
            "changes": len(changes),
            "material": len(material),
            "incorporations": len(incorporations),
            "applicability_rules": len(applicability_rules),
            "supersession_edges": len(supersessions),
        },
        "applicability": {
            "rules": [r.model_dump(mode="json") for r in applicability_rules],
            "excluded": excluded_pairs(units, changes, applicability_rules),
        },
        "decisions": [d.model_dump(mode="json") for d in kept],
        "conflicts": [c.model_dump(mode="json") for c in conflicts],
        "blocked": bool(conflicts),
    }


def kept_decisions(report: dict[str, Any]) -> list[Decision]:
    """Rebuild the kept decisions of an extended report as Decision models."""

    return [Decision(**d) for d in report["decisions"]]
