#!/usr/bin/env python3
"""The ONE write path onto the backlog files: read -> apply -> validate -> replace.

Every subcommand of `backlog.py` that writes goes through :func:`commit`. It builds the
candidate bytes, runs the SAME `check` those bytes will be validated by afterwards, and
only then replaces the file atomically (`os.replace` from a temp file beside it). A
concurrent write that landed while the change was being computed is detected by the
file's own (size, mtime) and re-applied once — the backlog is ADDITIVE, so a race
surfaces and retries, it never blocks.

An exit is the atomic pair of a removal and an append. The pair is ordered so a crash
leaves the entry live (recoverable by re-running) rather than lost: the histo record is
written first ONLY after the whole removal has been validated, and the removal lands
last, so the cross-file check in `_backlog_check` sees at worst a duplicate that names
itself.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _backlog_check import document_findings, histo_findings  # noqa: E402
from _backlog_schema import HISTO, LEDGER  # noqa: E402

Items = list[dict[str, Any]]
SCRIPT = Path(__file__).parent / "backlog.py"


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


def _stamp(path: Path) -> tuple[int, int] | None:
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return (info.st_size, info.st_mtime_ns)


def read_active(path: Path) -> Items:
    """The live ``active[]`` of *path*, in document order. A document this script cannot
    read in full refuses the read rather than being silently rewritten without it."""
    if not path.is_file():
        return []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Refusal(
            f"{path.name} is not valid JSON ({exc.msg}) — refusing to rewrite a document "
            "this script cannot read in full",
            f"{SCRIPT} check --specs <specs>",
        ) from exc
    active = document.get("active") if isinstance(document, dict) else None
    if not isinstance(active, list):
        raise Refusal(
            f"{path.name} carries no 'active' array — it is not a backlog-v1 document",
            f"{SCRIPT} check --specs <specs>",
        )
    return active


def serialize(active: Items) -> str:
    return json.dumps({"schema": "backlog-v1", "active": active}, indent=2) + "\n"


def _validated(active: Items) -> str:
    text = serialize(active)
    findings = document_findings(text)
    if findings:
        detail = "; ".join(str(f["message"]) for f in findings[:5])
        raise Refusal(
            f"the resulting {LEDGER} would not pass check — nothing was written ({detail})",
            f"{SCRIPT} check --specs <specs>",
        )
    return text


def _replace(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def commit(path: Path, apply: Callable[[Items], Items]) -> Items:
    """Apply *apply* to *path*'s ``active[]`` and replace the document atomically.

    The candidate bytes are validated BEFORE the replace, so a refused write leaves the
    file byte-identical. When the file changed under the computation, the change is
    re-read and re-applied ONCE; a second concurrent write refuses with a retry `fix:`.
    """
    before = _stamp(path)
    written = apply(read_active(path))
    text = _validated(written)
    if _stamp(path) != before:
        before = _stamp(path)
        written = apply(read_active(path))
        text = _validated(written)
        if _stamp(path) != before:
            raise Refusal(
                f"{path.name} changed twice under this write — nothing was written",
                "re-run this command",
            )
    _replace(path, text)
    return written


def append_histo(path: Path, record: dict[str, Any]) -> None:
    """Append one validated terminal record to the append-only exit ledger. The record
    is validated ALONE — a pre-v6 line already in the file is history, not this write's
    business, and re-validating the whole file would refuse every exit on a repo that
    has one."""
    line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
    findings = histo_findings(line)
    if findings:
        raise Refusal(
            f"the {HISTO} record this exit would write does not pass check — nothing was "
            f"written ({findings[0]['message']})",
            f"{SCRIPT} check --specs <specs>",
        )
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    _replace(path, existing + line)
