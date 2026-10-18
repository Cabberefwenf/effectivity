"""Command line: python -m effectivity --units ... --changes ... --material ... --incorporations ...

Modes:

- Core (default): classify every unit x change pair into one of six
  effectivity states and print the table. ``--log`` appends one JSONL line
  for the core run; ``--trace`` writes one JSON trace per pair.
- Extended (any of ``--applicability``, ``--supersession``, ``--conflicts``,
  ``--extended-report``): applicability first, then the core resolver,
  then the exactly-one-match conflict pass (ADR 0004). The printed table
  shows the pairs that apply; excluded pairs and conflicts are printed
  after it. ``--log`` still records the core run over all four tables;
  ``--extended-report`` records the full extended run, including its
  extended input hash. Conflicts make the run exit 3 (BLOCKED).
- Verify (``--verify-log``): audit a run log without changing it; exit 0
  when it checks out, 3 when it does not.

Exit codes: 0 ok (or BLOCKED-free extended run), 2 bad input or bad
usage, 3 conflicts BLOCKED or log verification failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from effectivity.applicability import ApplicabilityRule
from effectivity.conflicts import Supersession
from effectivity.log import append_run, count_by_status, input_hash
from effectivity.model import (
    Change,
    Decision,
    Incorporation,
    MaterialState,
    Unit,
)
from effectivity.pipeline import kept_decisions, run_extended
from effectivity.resolve import RULE_VERSION, resolve
from effectivity.tables import parse_csv
from effectivity.trace import trace_all, trace_selected
from effectivity.verify import verify_log

M = TypeVar("M", bound=BaseModel)


def load_table(path: Path, model: type[M]) -> list[M]:
    """Read a CSV file into models (UTF-8, optional BOM). See `parse_csv` for the rules."""
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: not valid UTF-8 ({exc.reason})") from exc
    return parse_csv(text, model, str(path))


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


def format_extended(report: dict) -> str:
    """Applicability exclusions and conflicts, printed after the table."""

    lines = [""]
    excluded = report["applicability"]["excluded"]
    if report["inputs"]["applicability_rules"]:
        lines.append(f"applicability: {len(excluded)} pair(s) excluded by "
                     f"{report['inputs']['applicability_rules']} rule(s)")
        for row in excluded:
            lines.append(f"  {row['unit_id']} {row['change_id']} excluded "
                         f"({row['rule_id']}): {row['reason']}")
    conflicts = report["conflicts"]
    if conflicts:
        lines.append(f"conflicts: {len(conflicts)} slot(s) BLOCKED")
        for conflict in conflicts:
            competing = ", ".join(c["change_id"] for c in conflict["competing"])
            lines.append(
                f"  {conflict['unit_id']} {conflict['supersedes_part']} "
                f"{conflict['reason_code']} ({','.join(conflict['rule_ids'])}): {competing}"
            )
    else:
        lines.append("conflicts: none")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m effectivity",
        description="Classify every unit x change pair into one of six effectivity states.",
    )
    parser.add_argument("--units", type=Path)
    parser.add_argument("--changes", type=Path)
    parser.add_argument("--material", type=Path)
    parser.add_argument("--incorporations", type=Path)
    parser.add_argument("--log", type=Path, help="append one JSONL line per core run to this file")
    parser.add_argument(
        "--run-at",
        help="opaque label stored verbatim in the log; never parsed, never read from a clock",
    )
    parser.add_argument(
        "--applicability",
        type=Path,
        help="optional CSV of applicability rules (change_id, program, applies); enables extended mode",
    )
    parser.add_argument(
        "--supersession",
        type=Path,
        help="optional CSV of supersession edges (change_id, supersedes_change_id); enables extended mode",
    )
    parser.add_argument(
        "--conflicts",
        action="store_true",
        help="enable the exactly-one-match conflict pass; enables extended mode",
    )
    parser.add_argument(
        "--extended-report",
        type=Path,
        help="write the full extended report (decisions, exclusions, conflicts, hashes) as JSON; enables extended mode",
    )
    parser.add_argument(
        "--trace",
        type=Path,
        help="write one JSON decision trace per decided pair to this file",
    )
    parser.add_argument(
        "--verify-log",
        type=Path,
        help="audit a run log without changing it; cannot be combined with other flags",
    )
    args = parser.parse_args(argv)

    if args.verify_log is not None:
        combined = [
            args.units, args.changes, args.material, args.incorporations,
            args.log, args.run_at, args.applicability, args.supersession,
            args.extended_report, args.trace,
        ]
        if any(value is not None for value in combined) or args.conflicts:
            parser.error("--verify-log cannot be combined with other flags")
        try:
            result = verify_log(args.verify_log)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if result["ok"]:
            versions = ", ".join(result["rule_versions"]) or "(none)"
            print(f"verified: {result['lines']} line(s), rule version(s): {versions}")
            return 0
        for problem in result["problems"]:
            print(f"verify: line {problem['line']}: {problem['message']}", file=sys.stderr)
        return 3

    if args.run_at is not None and args.log is None:
        parser.error("--run-at is only stored in the log; it requires --log")
    tables = [args.units, args.changes, args.material, args.incorporations]
    if any(value is None for value in tables):
        parser.error("the four tables --units, --changes, --material, --incorporations are required")
    extended = bool(
        args.applicability is not None
        or args.supersession is not None
        or args.conflicts
        or args.extended_report is not None
    )

    try:
        units = load_table(args.units, Unit)
        changes = load_table(args.changes, Change)
        material = load_table(args.material, MaterialState)
        incorporations = load_table(args.incorporations, Incorporation)
        applicability_rules = (
            load_table(args.applicability, ApplicabilityRule) if args.applicability else []
        )
        supersessions = (
            load_table(args.supersession, Supersession) if args.supersession else []
        )
        if extended:
            report = run_extended(
                units, changes, material, incorporations,
                applicability_rules=applicability_rules,
                supersessions=supersessions,
            )
            decisions = kept_decisions(report)
        else:
            decisions = resolve(units, changes, material, incorporations)
            report = None
        if args.log is not None:
            append_run(
                args.log,
                input_hash(units, changes, material, incorporations),
                resolve(units, changes, material, incorporations) if extended else decisions,
                args.run_at,
            )
        if args.trace is not None:
            if extended:
                pairs = {(d.unit_id, d.change_id) for d in decisions}
                traces = trace_selected(units, changes, material, incorporations, pairs)
            else:
                traces = trace_all(units, changes, material, incorporations)
            args.trace.write_text(
                "".join(json.dumps(t, sort_keys=True) + "\n" for t in traces), encoding="utf-8"
            )
        if args.extended_report is not None and report is not None:
            args.extended_report.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(format_table(decisions))
    if report is not None:
        print(format_extended(report))
        if report["blocked"]:
            return 3
    return 0
