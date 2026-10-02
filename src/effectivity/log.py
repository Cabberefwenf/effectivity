"""Append-only JSONL run log. Never reads the clock (ADR 0002)."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from effectivity.model import (
    Change,
    Decision,
    Incorporation,
    MaterialState,
    Status,
    Unit,
)
from effectivity.resolve import RULE_VERSION


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def input_hash(
    units: Sequence[Unit],
    changes: Sequence[Change],
    material: Sequence[MaterialState],
    incorporations: Sequence[Incorporation],
) -> str:
    """SHA-256 over the four parsed tables.

    Each row is serialized with sorted keys; each table's rows are sorted by
    that serialization, so CSV row order and column order do not matter.
    Duplicate rows are kept (material rows are summed, so they matter).
    """
    tables = {
        "units": units,
        "changes": changes,
        "material": material,
        "incorporations": incorporations,
    }
    payload = {
        name: sorted(_canonical(row.model_dump(mode="json")) for row in rows)
        for name, rows in tables.items()
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def count_by_status(decisions: Sequence[Decision]) -> dict[str, int]:
    """Count per each of the six statuses, zeros included, in canonical order."""
    counted = Counter(d.status for d in decisions)
    return {status.value: counted[status] for status in Status}


def log_line(
    sequence: int,
    digest: str,
    decisions: Sequence[Decision],
    run_at: str | None,
) -> str:
    record = {
        "sequence": sequence,
        "rule_version": RULE_VERSION,
        "input_hash": digest,
        "run_at": run_at,
        "counts": count_by_status(decisions),
        "decisions": [d.model_dump(mode="json") for d in decisions],
    }
    return _canonical(record)


def append_run(
    path: Path,
    digest: str,
    decisions: Sequence[Decision],
    run_at: str | None = None,
) -> int:
    """Append one line to the log and return its sequence number (0-based line index).

    The file is read once to find the next index, then opened in append mode
    only. Existing lines are never rewritten. Not safe against concurrent
    writers (see LIMITS.md).
    """
    sequence = 0
    if path.exists():
        existing = path.read_bytes()
        if existing and not existing.endswith(b"\n"):
            raise ValueError(f"{path} does not end with a newline; refusing to append")
        sequence = existing.count(b"\n")
    line = log_line(sequence, digest, decisions, run_at)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
    return sequence
