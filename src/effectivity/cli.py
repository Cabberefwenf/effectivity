"""Command line: python -m effectivity --units ... --changes ... --material ... --incorporations ..."""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from effectivity.log import append_run, count_by_status, input_hash
from effectivity.model import (
    Change,
    Decision,
    Incorporation,
    MaterialState,
    Unit,
)
from effectivity.resolve import RULE_VERSION, resolve

M = TypeVar("M", bound=BaseModel)


def load_table(path: Path, model: type[M]) -> list[M]:
    """Read a CSV whose header is exactly the model's fields (any order)."""
    expected = set(model.model_fields)
    required = {name for name, f in model.model_fields.items() if f.is_required()}
    rows: list[M] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = set(reader.fieldnames or [])
        if not required <= header or not header <= expected:
            raise ValueError(
                f"{path}: columns {sorted(header)} do not match {sorted(expected)}"
            )
        for line_no, row in enumerate(reader, start=2):
            if None in row or None in row.values():
                raise ValueError(f"{path}:{line_no}: wrong number of fields")
            try:
                rows.append(model.model_validate(row))
            except ValidationError as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return rows


def format_table(decisions: Sequence[Decision]) -> str:
    """Per-decision rows, then a count per each of the six states."""
    headers = ("unit_id", "change_id", "status", "reason_code", "rule_ids")
    body = [
        (d.unit_id, d.change_id, d.status.value, d.reason_code, ",".join(d.rule_ids))
        for d in decisions
    ]
    widths = [max(len(r[i]) for r in [headers, *body]) for i in range(len(headers))]

    def line(cells: Sequence[str]) -> str:
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths, strict=True)).rstrip()

    out = [line(headers), line(["-" * w for w in widths])]
    out += [line(r) for r in body]
    counts = count_by_status(decisions)
    width = max(len(name) for name in counts)
    out += ["", f"rule_version {RULE_VERSION}", "", f"{'state'.ljust(width)}  count"]
    out += [f"{name.ljust(width)}  {count:>5}" for name, count in counts.items()]
    out.append(f"{'total'.ljust(width)}  {len(decisions):>5}")
    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m effectivity",
        description="Classify every unit x change pair into one of six effectivity states.",
    )
    parser.add_argument("--units", type=Path, required=True)
    parser.add_argument("--changes", type=Path, required=True)
    parser.add_argument("--material", type=Path, required=True)
    parser.add_argument("--incorporations", type=Path, required=True)
    parser.add_argument("--log", type=Path, help="append one JSONL line per run to this file")
    parser.add_argument(
        "--run-at",
        help="opaque label stored verbatim in the log; never parsed, never read from a clock",
    )
    args = parser.parse_args(argv)

    try:
        units = load_table(args.units, Unit)
        changes = load_table(args.changes, Change)
        material = load_table(args.material, MaterialState)
        incorporations = load_table(args.incorporations, Incorporation)
        decisions = resolve(units, changes, material, incorporations)
        if args.log is not None:
            append_run(
                args.log,
                input_hash(units, changes, material, incorporations),
                decisions,
                args.run_at,
            )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_table(decisions))
    return 0
