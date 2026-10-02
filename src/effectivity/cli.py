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
    """Read a CSV into models. Rules are in docs/state-machine.md ("Input rules").

    UTF-8 with an optional BOM; header must be exactly the model's fields, each
    once, in any order. Any problem raises ValueError naming file and line.
    """
    expected = set(model.model_fields)
    rows: list[M] = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            names = list(reader.fieldnames or [])
            duplicated = sorted({n for n in names if names.count(n) > 1})
            if duplicated:
                raise ValueError(f"{path}: duplicate column(s) {duplicated}")
            missing, unexpected = sorted(expected - set(names)), sorted(set(names) - expected)
            if missing or unexpected:
                raise ValueError(
                    f"{path}: columns must be exactly {sorted(expected)}; "
                    f"missing {missing}, unexpected {unexpected}"
                )
            for row in reader:
                where = f"{path}:{reader.line_num}"
                if None in row or None in row.values():
                    raise ValueError(f"{where}: wrong number of fields")
                try:
                    rows.append(model.model_validate(row))
                except ValidationError as exc:
                    problems = "; ".join(
                        f"{'.'.join(map(str, e['loc'])) or 'row'}: "
                        f"{e['msg'].removeprefix('Value error, ')}"
                        for e in exc.errors()
                    )
                    raise ValueError(f"{where}: {problems}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: not valid UTF-8 ({exc.reason})") from exc
    except csv.Error as exc:
        raise ValueError(f"{path}: malformed CSV ({exc})") from exc
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
    if args.run_at is not None and args.log is None:
        parser.error("--run-at is only stored in the log; it requires --log")

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
