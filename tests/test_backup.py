"""Backup tool: content-hash name, manifest, no overwrite, hash-checked copy."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from builders import change, unit
from effectivity.cli import main
from effectivity.log import append_run, input_hash
from effectivity.resolve import resolve

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
TOOL = ROOT / "tools" / "backup_log.py"


def _make_log(tmp_path: Path) -> Path:
    log = tmp_path / "run-log.jsonl"
    decisions = resolve([unit()], [change()], [], [])
    append_run(log, input_hash([unit()], [change()], [], []), decisions)
    return log


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args], capture_output=True, text=True, check=False
    )


def test_backup_writes_copy_and_manifest(tmp_path: Path) -> None:
    log = _make_log(tmp_path)
    dest = tmp_path / "backups"
    done = _run("--log", str(log), "--dest", str(dest))
    assert done.returncode == 0, done.stderr
    digest = hashlib.sha256(log.read_bytes()).hexdigest()
    name = f"run-log.{digest[:12]}.jsonl"
    assert (dest / name).read_bytes() == log.read_bytes()
    manifest = (dest / f"{name}.sha256").read_text()
    assert manifest.startswith(digest)
    assert f"{len(log.read_bytes())} bytes" in manifest
    assert "1 lines" in manifest
    assert "backed up" in done.stdout


def test_backup_twice_is_a_noop(tmp_path: Path) -> None:
    log = _make_log(tmp_path)
    dest = tmp_path / "backups"
    assert _run("--log", str(log), "--dest", str(dest)).returncode == 0
    before = sorted(p.name for p in dest.iterdir())
    done = _run("--log", str(log), "--dest", str(dest))
    assert done.returncode == 0
    assert "already backed up" in done.stdout
    assert sorted(p.name for p in dest.iterdir()) == before


def test_backup_of_changed_log_writes_a_new_file(tmp_path: Path) -> None:
    log = _make_log(tmp_path)
    dest = tmp_path / "backups"
    assert _run("--log", str(log), "--dest", str(dest)).returncode == 0
    decisions = resolve([unit()], [change()], [], [])
    append_run(log, input_hash([unit()], [change()], [], []), decisions)
    assert _run("--log", str(log), "--dest", str(dest)).returncode == 0
    assert len(list(dest.glob("run-log.*.jsonl"))) == 2


def test_backup_missing_log_is_exit_2(tmp_path: Path) -> None:
    done = _run("--log", str(tmp_path / "nope.jsonl"))
    assert done.returncode == 2
    assert "error:" in done.stderr


def test_backup_default_dest_is_next_to_the_log(tmp_path: Path) -> None:
    log = _make_log(tmp_path)
    done = subprocess.run(
        [sys.executable, str(TOOL), "--log", str(log)],
        capture_output=True, text=True, check=False, cwd=tmp_path,
    )
    assert done.returncode == 0, done.stderr
    assert (tmp_path / "backups").is_dir()
    assert len(list((tmp_path / "backups").glob("run-log.*.jsonl"))) == 1
