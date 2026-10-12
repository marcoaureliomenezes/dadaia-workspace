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
from collections.abc import Callable
from pathlib import Path
from typing import Any

import _commit
import _jsonl
from _backlog_check import pair_findings
from _backlog_schema import HISTO, LEDGER
from _ledger import private_refusal, replace
from _refusal import Refusal
from _specs import script

Items = list[dict[str, Any]]
SCRIPT = script(Path(__file__).parent / "backlog.py")


def read_active(path: Path) -> Items:
    """The live ``active[]`` of *path*, in document order. A document this script cannot
    read in full refuses the read rather than being silently rewritten without it."""
    if not path.is_file():
        return []
    document = _jsonl.parse_object(path.read_text(encoding="utf-8"), f"{SCRIPT} check")
    active = document.get("active")
    if not isinstance(active, list):
        raise Refusal(
            f"{path.name} carries no 'active' array — it is not a backlog-v1 document",
            f"{SCRIPT} check",
        )
    return active


def commit(
    specs: Path, apply: Callable[[Items], Items], record: dict[str, Any] | None = None
) -> Items:
    """Apply *apply* to ``active[]`` and, with *record*, append that one exit to the histo.

    The candidate PAIR is checked BEFORE either write (`_commit.commit` is the loop), so a
    refused write leaves both files byte-identical.
    """
    path = specs / LEDGER
    appended = _jsonl.serialize([record] if record else [])

    def validate(written: Items, before: Items, old: str, _moved: Items) -> str:
        new = [*(i for i in written if i not in before), *([record] if record else [])]
        why = private_refusal(new, path)
        if why is not None:
            raise Refusal(*why)
        text = json.dumps({"schema": "backlog-v1", "active": written}, indent=2) + "\n"
        if findings := pair_findings(text, old + appended):
            detail = "; ".join(str(f["message"]) for f in findings[:5])
            raise Refusal(
                f"the resulting {LEDGER} + {HISTO} would not pass check — nothing was written "
                f"({detail})",
                f"{SCRIPT} check",
            )
        return text

    return _commit.commit(
        path, read_active, apply, validate, replace, specs / HISTO,
        (lambda old, _moved: old + appended) if record else None,
    )  # fmt: skip
