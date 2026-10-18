"""Audit a run log: check every line without rewriting anything.

ADR 0005. The log is append-only and the tool that writes it never reads it
back, so nothing notices a damaged log until someone looks. This module is
that look. It reads a log file and reports each problem with its line
number: bad JSON, a wrong key set, a sequence number that is not the line
index, a malformed input hash, counts that do not match the decisions on
the same line, decisions out of order or duplicated, and a missing final
newline.

What it does not check: whether the decisions are the ones the inputs
would produce. Recomputing that needs the inputs, which the log does not
carry. Re-run the resolver on the inputs and compare the decisions if
that proof is needed. It also does not check that the rule version is
current; rule versions legitimately change across runs, so the versions
seen are reported, not judged.

Read-only: the file is never written. A missing file raises
FileNotFoundError, so the caller can tell "no log" from "bad log".
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from effectivity.log import count_by_status
from effectivity.model import Decision

_HEX64 = re.compile(r"[0-9a-f]{64}", re.ASCII)
_RECORD_KEYS = {"sequence", "rule_version", "input_hash", "run_at", "counts", "decisions"}


def verify_log(path: Path) -> dict[str, Any]:
    """Verify the log at ``path``. Returns a JSON-ready result dict."""

    data = path.read_bytes()
    problems: list[dict[str, Any]] = []
    versions: list[str] = []
    if not data:
        return {"ok": True, "lines": 0, "rule_versions": [], "problems": []}
    lines = data.split(b"\n")
    if lines[-1] != b"":
        problems.append(
            {"line": len(lines), "message": "file does not end with a newline; the last line may be partial"}
        )
        body = lines
    else:
        body = lines[:-1]
    for index, raw in enumerate(body):
        lineno = index + 1
        try:
            record = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            problems.append({"line": lineno, "message": f"line is not valid JSON ({exc})"})
            continue
        if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
            problems.append(
                {
                    "line": lineno,
                    "message": f"record keys must be exactly {sorted(_RECORD_KEYS)}",
                }
            )
            continue
        if record["sequence"] != index:
            problems.append(
                {
                    "line": lineno,
                    "message": f"sequence is {record['sequence']!r}, expected {index}",
                }
            )
        version = record["rule_version"]
        if not isinstance(version, str) or not version:
            problems.append({"line": lineno, "message": "rule_version must be a non-empty string"})
        elif version not in versions:
            versions.append(version)
        digest = record["input_hash"]
        if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None:
            problems.append({"line": lineno, "message": "input_hash must be 64 lowercase hex characters"})
        decisions = record["decisions"]
        if not isinstance(decisions, list):
            problems.append({"line": lineno, "message": "decisions must be a list"})
            continue
        parsed: list[Decision] = []
        for position, row in enumerate(decisions):
            try:
                parsed.append(Decision(**row) if isinstance(row, dict) else Decision.model_validate(row))
            except (ValidationError, TypeError) as exc:
                problems.append(
                    {"line": lineno, "message": f"decisions[{position}] is not a valid decision ({exc})"}
                )
                break
        else:
            keys = [(d.unit_id, d.change_id) for d in parsed]
            if keys != sorted(keys):
                problems.append({"line": lineno, "message": "decisions are not sorted by (unit_id, change_id)"})
            if len(set(keys)) != len(keys):
                problems.append({"line": lineno, "message": "duplicate (unit_id, change_id) in decisions"})
            if record["counts"] != count_by_status(parsed):
                problems.append({"line": lineno, "message": "counts do not match the decisions on this line"})
    return {
        "ok": not problems,
        "lines": len(body),
        "rule_versions": sorted(versions),
        "problems": problems,
    }
