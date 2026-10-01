#!/usr/bin/env python3
"""The ONE write path onto the backlog files: read -> apply -> validate -> replace.

Every write goes through :func:`commit`: build the candidate bytes, run the SAME `check`
they will be validated by, then `os.replace` atomically. A concurrent write is detected
by the file's own (size, mtime) and re-applied once — a race surfaces and retries.

An exit is a removal plus an append: the PAIR is checked first, then the histo record is
written and the removal lands last, so a crash leaves the entry live rather than lost.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _backlog_check import pair_findings  # noqa: E402
from _backlog_schema import HISTO, LEDGER  # noqa: E402
from _ledger import private_refusal, replace, stamp  # noqa: E402
from _specs import script  # noqa: E402

Items = list[dict[str, Any]]
SCRIPT = script(Path(__file__).parent / "backlog.py")


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


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
            f"{SCRIPT} check",
        ) from exc
    active = document.get("active") if isinstance(document, dict) else None
    if not isinstance(active, list):
        raise Refusal(
            f"{path.name} carries no 'active' array — it is not a backlog-v1 document",
            f"{SCRIPT} check",
        )
    return active


def serialize(active: Items) -> str:
    return json.dumps({"schema": "backlog-v1", "active": active}, indent=2) + "\n"


def _validated(
    specs: Path, active: Items, histo: str, before: Items, record: dict[str, Any] | None
) -> str:
    for item in [*(i for i in active if i not in before), *([record] if record else [])]:
        why = private_refusal(item, specs)
        if why is not None:
            raise Refusal(*why)
    text = serialize(active)
    findings = pair_findings(text, histo)
    if findings:
        detail = "; ".join(str(f["message"]) for f in findings[:5])
        raise Refusal(
            f"the resulting {LEDGER} + {HISTO} would not pass check — nothing was written "
            f"({detail})",
            f"{SCRIPT} check",
        )
    return text


def commit(
    specs: Path, apply: Callable[[Items], Items], record: dict[str, Any] | None = None
) -> Items:
    """Apply *apply* to ``active[]`` and, with *record*, append that one exit to the histo.

    The candidate PAIR is checked BEFORE either write, so a refused write leaves both
    files byte-identical. When the document changed under the computation, the change is
    re-read and re-applied ONCE; a second concurrent write refuses with a retry `fix:`.
    """
    path, histo = specs / LEDGER, specs / HISTO
    line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" if record else ""
    candidate = (histo.read_text(encoding="utf-8") if histo.is_file() else "") + line
    before = stamp(path)
    active = read_active(path)
    written = apply(active)
    text = _validated(specs, written, candidate, active, record)
    if stamp(path) != before:
        before = stamp(path)
        active = read_active(path)
        written = apply(active)
        text = _validated(specs, written, candidate, active, record)
        if stamp(path) != before:
            raise Refusal(
                f"{path.name} changed twice under this write — nothing was written",
                "re-run this command",
            )
    if line:
        replace(histo, candidate)
    replace(path, text)
    return written
