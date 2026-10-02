"""One JSON-ready report of a run. The CLI log and the web function both use it."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from effectivity.log import count_by_status, input_hash
from effectivity.model import Change, Incorporation, MaterialState, Unit
from effectivity.resolve import RULE_VERSION, resolve


def build_report(
    units: Sequence[Unit],
    changes: Sequence[Change],
    material: Sequence[MaterialState],
    incorporations: Sequence[Incorporation],
) -> dict[str, Any]:
    """Resolve and describe the run: rule version, input hash, counts, decisions."""
    decisions = resolve(units, changes, material, incorporations)
    return {
        "rule_version": RULE_VERSION,
        "input_hash": input_hash(units, changes, material, incorporations),
        "inputs": {
            "units": len(units),
            "changes": len(changes),
            "material": len(material),
            "incorporations": len(incorporations),
        },
        "counts": count_by_status(decisions),
        "decisions": [d.model_dump(mode="json") for d in decisions],
    }
