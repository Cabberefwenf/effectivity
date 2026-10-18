"""Back up a run log with a content-hash name and a sha256 manifest.

Run: .venv/bin/python tools/backup_log.py --log run-log.jsonl [--dest backups]

The backup name derives from the content, not the clock: a log whose
SHA-256 is ``ab12...`` backs up to ``<stem>.ab1234567890.jsonl`` next to a
manifest ``<stem>.ab1234567890.jsonl.sha256`` holding the full hash, byte
count, and line count. Backing up the same content twice is a no-op that
prints the existing path; backing up changed content writes a new file,
so old backups are never overwritten. The copy is hashed after writing
and compared to the source, so a short write is caught, not trusted.

Exit codes: 0 backed up (or already backed up), 1 the destination already
holds different content under this name (should not happen without a
hash collision), 2 the log file is missing or unreadable.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def backup_log(log: Path, dest: Path) -> tuple[Path, bool]:
    """Copy ``log`` into ``dest``. Returns (backup path, already_existed)."""

    data = log.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    name = f"{log.stem}.{digest[:12]}.jsonl"
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    manifest = dest / f"{name}.sha256"
    lines = data.count(b"\n")
    manifest_text = f"{digest}  {len(data)} bytes  {lines} lines  source={log.name}\n"
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError(f"{target} holds different content for hash {digest}")
        if manifest.exists() and manifest.read_text() != manifest_text:
            raise ValueError(f"{manifest} does not match {target}")
        manifest.write_text(manifest_text)
        return target, True
    with target.open("xb") as handle:
        written = handle.write(data)
    if written != len(data):
        raise OSError(f"short write to {target}: {written} of {len(data)} bytes")
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise OSError(f"backup {target} does not match the source hash")
    manifest.write_text(manifest_text)
    return target, False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="backup_log.py",
        description="Back up a run log under a content-hash name with a sha256 manifest.",
    )
    parser.add_argument("--log", type=Path, required=True, help="run log to back up")
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="backup directory (default: backups/ next to the log)",
    )
    args = parser.parse_args(argv)
    dest = args.dest if args.dest is not None else args.log.parent / "backups"
    try:
        target, existed = backup_log(args.log, dest)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{'already backed up' if existed else 'backed up'}: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
