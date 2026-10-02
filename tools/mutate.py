"""Hand-picked mutation check. Run: .venv/bin/python tools/mutate.py

Copies the repo to a temp dir, applies each mutation (one at a time) to a
source file, runs the suite there, and reports whether the suite failed
(mutant killed). Deterministic; exits 1 if any mutant survives. These are
mutants chosen by hand, not a coverage measure.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R, M, L, C, S, T = "resolve.py", "model.py", "log.py", "cli.py", "service.py", "tables.py"

# (name, file, old, new); old must occur in the file, first occurrence is replaced.
MUTANTS: list[tuple[str, str, str, str]] = [
    ("range: lower bound exclusive", M, "return lower <= key <= upper", "return lower < key <= upper"),
    ("range: upper bound exclusive", M, "return lower <= key <= upper", "return lower <= key < upper"),
    ("range: no upper bound", M, "return lower <= key <= upper", "return lower <= key"),
    ("range: no lower bound", M, "return lower <= key <= upper", "return key <= upper"),
    ("range: from/to swapped", R, "parse_key(change.effectivity_from),\n        parse_key(change.effectivity_to),",
     "parse_key(change.effectivity_to),\n        parse_key(change.effectivity_from),"),
    ("range: from > to accepted", M, "if lower > upper:", "if lower > upper and False:"),
    ("key: number compared as string", M, "Key(prefix, int(number), suffix)", "Key(prefix, number, suffix)"),
    ("key: suffix dropped from order", M, "Key(prefix, int(number), suffix)", "Key(prefix, int(number), '')"),
    ("hold: comparison sign flipped", M, "return (left > right) - (left < right)", "return (left < right) - (left > right)"),
    ("hold: cross-prefix not an error", M, "    if left.prefix != right.prefix:\n        raise", "    if False:\n        raise"),
    ("R01 removed", R, "    if not key_in_range(", "    if False and not key_in_range("),
    ("R02: predecessor ignored", R, 'if unit.predecessor_hold_status == "closed":\n            return', "if True:\n            return"),
    ("R02: incorporated=false counts", R, "if incorporation is not None and incorporation.incorporated:", "if incorporation is not None:"),
    ("R03: data error not flagged", R, '        overlay = ("R03",)', "        overlay = ()"),
    ("R03: reason not overridden", R, "        if overlay:\n            reason = DATA_ERROR_INCORPORATED_OPEN_PREDECESSOR\n", ""),
    ("R04: threshold > 1", R, "if wrong_material_qty > 0 and", "if wrong_material_qty > 1 and"),
    ("R04: threshold >= 0", R, "if wrong_material_qty > 0 and", "if wrong_material_qty >= 0 and"),
    ("material: receipt counted as staged", R, "row.qty_staged_at_work + row.qty_installed",
     "row.qty_received_to_stores + row.qty_staged_at_work + row.qty_installed"),
    ("material: installed-only does not block", R, "row.qty_staged_at_work + row.qty_installed", "row.qty_staged_at_work"),
    ("material: staged-only does not block", R, "row.qty_staged_at_work + row.qty_installed", "row.qty_installed"),
    ("material: duplicate rows overwrite", R, "wrong_qty.get(key, 0) + row.", "row."),
    ("material: matched on part only", R, "key = (row.unit_id, row.part)", 'key = ("", row.part)'),
    ("material: lookup ignores unit", R, "wrong_qty.get((unit.unit_id, change.supersedes_part), 0)", "wrong_qty.get((unit.unit_id, change.replacement_part), 0)"),
    ("use_as_is blocks", R, "    Disposition.SCRAP: BLOCKED_SCRAP_WRONG_MATERIAL,\n", "    Disposition.SCRAP: BLOCKED_SCRAP_WRONG_MATERIAL,\n    Disposition.USE_AS_IS: BLOCKED_REWORK_WRONG_MATERIAL,\n"),
    ("scrap not blocked by material", R, "    Disposition.SCRAP: BLOCKED_SCRAP_WRONG_MATERIAL,\n", ""),
    ("scrap recommends install", R, "SCRAP_ONLY_NO_INSTALL, \"R10\")", "INCORPORABLE_REWORK, \"R10\")"),
    ("retrofit incorporable code = rework", R, "INCORPORABLE_RETROFIT, \"R08\")", "INCORPORABLE_REWORK, \"R08\")"),
    ("retrofit blocked code = rework", R, "Disposition.RETROFIT: BLOCKED_RETROFIT_WRONG_MATERIAL", "Disposition.RETROFIT: BLOCKED_REWORK_WRONG_MATERIAL"),
    ("use_as_is code says rework", R, "INCORPORABLE_USE_AS_IS_NO_REWORK, \"R09\")", "INCORPORABLE_REWORK, \"R09\")"),
    ("R05: open-at-point counts as passed", R, "if position > 0 or (", "if position >= 0 or ("),
    ("R05: closed-at-point not late", R, '(position == 0 and unit.hold_point_status == "closed")', "False"),
    ("R05: past point not late", R, "if position > 0 or (", "if (position > 100) or ("),
    ("R06: at-point counts as before", R, "    if position < 0:", "    if position <= 0:"),
    ("R07 removed", R, '    if unit.predecessor_hold_status == "open":\n        return finish(Status.NOT_YET_REACHED, NOT_YET_REACHED_PREDECESSOR_OPEN', '    if False:\n        return finish(Status.NOT_YET_REACHED, NOT_YET_REACHED_PREDECESSOR_OPEN'),
    ("output not sorted", R, "return tuple(sorted(decisions, key=lambda d: (d.unit_id, d.change_id)))", "return tuple(decisions)"),
    ("output sorted by change first", R, "key=lambda d: (d.unit_id, d.change_id)", "key=lambda d: (d.change_id, d.unit_id)"),
    ("duplicate unit not detected", R, "if len(seen) != len(values):", "if False:"),
    ("duplicate incorporation not detected", R, "        if pair in incorporation_by_pair:", "        if False:"),
    ("unknown incorporation unit ignored", R, "        if record.unit_id not in unit_ids:", "        if False:"),
    ("clock import in decision module", R, "from collections.abc import Sequence", "import datetime\nfrom collections.abc import Sequence"),
    ("input: negative quantity accepted", M, "0 <= value < 10**15", "value < 10**15"),
    ("input: float quantity accepted", M, "    raise ValueError(f\"{value!r}: quantity must be an integer", "    return value\n    raise ValueError(f\"{value!r}: quantity must be an integer"),
    ("input: part whitespace accepted", M, 'return value if value == "" else _text(value)', "return value"),
    ("input: incorporated 'True' accepted", M, 'if value == "true":', 'if str(value).lower() == "true":'),
    ("log: overwrite instead of append", L, 'path.open("ab", buffering=0)', 'path.open("wb", buffering=0)'),
    ("log: hash depends on row order", L, "sorted(_canonical(row.model_dump(mode=\"json\")) for row in rows)", "[_canonical(row.model_dump(mode=\"json\")) for row in rows]"),
    ("log: hash ignores incorporations", L, '        "incorporations": incorporations,\n', ""),
    ("log: rule_version missing", L, '        "rule_version": RULE_VERSION,\n', ""),
    ("log: no newline terminator", L, '+ "\\n").encode("utf-8")', ').encode("utf-8")'),
    ("log: sequence fixed at 0", L, "sequence = existing.count(b\"\\n\")", "sequence = 0"),
    ("log: run_at defaulted to a string", L, "    run_at: str | None = None,\n) -> int:", "    run_at: str | None = 'now',\n) -> int:"),
    ("tables: BOM not handled", T, 'text.removeprefix("\\ufeff")', "text"),
    ("tables: duplicate column allowed", T, "        if duplicated:", "        if False:"),
    ("tables: short rows accepted", T, "if None in row or None in row.values():", "if False:"),
    # The web function's guards: each cap, the method check and the no-store header must be pinned by a test.
    ("service: body cap off by one", S, "if len(raw) > MAX_BODY_BYTES:", "if len(raw) > MAX_BODY_BYTES + 1:"),
    ("service: Content-Length cap removed", S, "    if length > MAX_BODY_BYTES:", "    if False and length > MAX_BODY_BYTES:"),
    ("service: row cap ignored", S, "max_rows=MAX_ROWS[name])", "max_rows=None)"),
    ("service: pair cap off by one", S, "> MAX_PAIRS:", "> MAX_PAIRS + 1:"),
    ("service: GET accepted", S, 'if environ.get("REQUEST_METHOD") != "POST":', 'if False:'),
    ("service: response cacheable", S, '("Cache-Control", "no-store")', '("Cache-Control", "public")'),
    ("service: sniffing allowed", S, '("X-Content-Type-Options", "nosniff")', '("X-Content-Type-Options", "")'),
]


def main() -> int:
    survivors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(
            ".venv", ".git", "__pycache__", ".pytest_cache", "*.egg-info",
            "node_modules", ".next", ".vercel", "test-results", "playwright-report", "screenshots",
        ))
        env = {"PYTHONPATH": str(work / "src"), "PATH": "/usr/bin:/bin"}
        baseline = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"],
            cwd=work, env=env, capture_output=True, text=True,
        )
        if baseline.returncode != 0:
            print("unmutated copy does not pass; fix that first\n" + baseline.stdout[-2000:])
            return 2
        for name, fname, old, new in MUTANTS:
            path = work / "src" / "effectivity" / fname
            original = path.read_text()
            if old not in original:
                print(f"BAD MUTANT (pattern not found): {name}")
                return 2
            path.write_text(original.replace(old, new, 1))
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"],
                    cwd=work, env=env, capture_output=True, text=True,
                )
            finally:
                path.write_text(original)
            killed = result.returncode != 0
            print(f"{'killed  ' if killed else 'SURVIVED'} {name}")
            if not killed:
                survivors.append(name)
    print(f"\n{len(MUTANTS) - len(survivors)}/{len(MUTANTS)} killed")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
