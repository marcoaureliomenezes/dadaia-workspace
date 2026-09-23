#!/usr/bin/env python3
"""The ONE write path onto the audit files: resolve -> apply -> validate -> replace.

`disposition` rewrites one finding's governance triple in the FINDINGS.jsonl it lives
in; `close` appends one record to the archive and deletes the directory. Both build the
candidate bytes, run the SAME `check` they will be validated by, then `os.replace`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _audit_check import findings_findings, histo_findings  # noqa: E402
from _audit_schema import AUDITS, FINDINGS, HISTO  # noqa: E402

SCRIPT = Path(__file__).parent / "audit.py"


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


def audit_dir(specs: Path, audit: str, fix: str) -> Path:
    """Resolve one live audit directory, or refuse naming the ones that exist.

    *audit* is operator input naming a directory `close` DELETES, so it is CONFINED
    before it is read: the fully resolved target must sit strictly inside the resolved
    ``specs/audits/``. One containment rule covers every escape shape — ``..``
    traversal, an absolute path, and a symlink out of the tree (CWE-22/CWE-59).
    """
    audits = (specs / AUDITS).resolve()
    target = (audits / audit).resolve()
    if target != audits and target.is_relative_to(audits) and (target / FINDINGS).is_file():
        return target
    live = sorted(
        child.name
        for child in (audits.iterdir() if audits.is_dir() else [])
        if child.is_dir() and child.name != "_archive"
    )
    raise Refusal(
        f"{audit!r} does not name a live audit with a {FINDINGS} under specs/{AUDITS}/. "
        f"Live audits: {', '.join(live) or '(none)'}",
        fix,
    )


def read_findings(directory: Path) -> list[dict[str, Any]]:
    """Every record of *directory*'s FINDINGS.jsonl, or a refusal naming the bad line."""
    text = (directory / FINDINGS).read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise Refusal(
                f"specs/{AUDITS}/{directory.name}/{FINDINGS} line {number} is not valid "
                f"JSON ({exc.msg}) — refusing to rewrite a file this script cannot read "
                "in full",
                f"{SCRIPT} check --specs <specs>",
            ) from exc
    return records


def serialize(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records)


def _replace(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_findings(directory: Path, records: list[dict[str, Any]]) -> None:
    """Replace *directory*'s FINDINGS.jsonl with *records*, validated first."""
    text = serialize(records)
    problems = findings_findings(text, f"{AUDITS}/{directory.name}/{FINDINGS}")
    if problems:
        raise Refusal(
            f"the resulting {FINDINGS} would not pass check — nothing was written "
            f"({problems[0]['message']})",
            f"{SCRIPT} check --specs <specs>",
        )
    _replace(directory / FINDINGS, text)


def append_histo(specs: Path, record: dict[str, Any]) -> None:
    """Append one validated terminal record to the append-only archive. The record is
    validated ALONE — a pre-v6 line already in the file is history, not this write's
    business."""
    line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
    problems = histo_findings(line)
    if problems:
        raise Refusal(
            f"the {HISTO} record this close would write does not pass check — nothing "
            f"was written ({problems[0]['message']})",
            f"{SCRIPT} check --specs <specs>",
        )
    path = specs / HISTO
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    _replace(path, existing + line)
