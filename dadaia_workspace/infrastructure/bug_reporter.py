"""Bug reporter — persists detected errors to .dadaia/bugs/reported.json."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path


def _git_context(workspace_root: Path, lines: int = 3) -> str:
    """Return last N git log lines from workspace root, or empty string."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{lines}"],
            capture_output=True,
            text=True,
            cwd=workspace_root,
            timeout=3,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _bugs_path(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "bugs" / "reported.json"


def _load(path: Path) -> list[dict]:  # type: ignore[type-arg]
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
        except Exception:
            return []
    return []


def _save(path: Path, entries: list[dict]) -> None:  # type: ignore[type-arg]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def append_entry(workspace_root: Path, entry: dict) -> None:  # type: ignore[type-arg]
    """Atomically append one entry to reported.json."""
    path = _bugs_path(workspace_root)
    entries = _load(path)
    entries.append(entry)
    _save(path, entries)


def report_exception(
    workspace_root: Path,
    command: str,
    exc: BaseException,
) -> None:
    """Capture an unexpected CLI exception and persist it."""
    entry: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "reported_at": datetime.now(UTC).isoformat(),
        "source": "cli-exception",
        "command": command,
        "exception_type": type(exc).__name__,
        "message": str(exc),
        "traceback_tail": "".join(traceback.format_exception(exc))[-1000:],
        "git_context": _git_context(workspace_root),
        "status": "open",
    }
    with contextlib.suppress(Exception):
        append_entry(workspace_root, entry)


def load_open_bugs(workspace_root: Path) -> list[dict]:  # type: ignore[type-arg]
    """Return all entries with status='open'."""
    path = _bugs_path(workspace_root)
    return [e for e in _load(path) if e.get("status") == "open"]


def mark_bugs_in_release(workspace_root: Path, bug_ids: list[str]) -> None:
    """Set status='in_release' for the given bug IDs. Atomic."""
    path = _bugs_path(workspace_root)
    entries = _load(path)
    for entry in entries:
        if entry.get("id") in bug_ids:
            entry["status"] = "in_release"
    _save(path, entries)


def report_doctor_finding(
    workspace_root: Path,
    source: str,
    finding: str,
) -> None:
    """Persist a doctor [missing]/[drift]/[fail]/[warn] finding."""
    entry: dict[str, object] = {
        "id": str(uuid.uuid4()),
        "reported_at": datetime.now(UTC).isoformat(),
        "source": source,
        "command": f"dadaia {source.replace('-', ' ')}",
        "exception_type": None,
        "message": finding,
        "traceback_tail": None,
        "git_context": _git_context(workspace_root),
        "status": "open",
    }
    with contextlib.suppress(Exception):
        append_entry(workspace_root, entry)
