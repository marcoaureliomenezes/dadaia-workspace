#!/usr/bin/env python3
"""The one finding record of the ledger validators, and the walk of an append-only archive."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import _jsonl
from _refusal import spell_fix

Check = Callable[[Path], list[dict[str, Any]]]


def finding(code: str, path: str, line: int, message: str, fix: str) -> dict[str, Any]:
    return {"code": code, "verdict": "error", "path": path, "line": line, "message": message,
            "fix": fix}  # fmt: skip


def info(code: str, path: str, line: int, message: str) -> dict[str, Any]:
    """A listing row: it asks nothing of anyone, so it carries no fix."""
    return {"code": code, "verdict": "info", "path": path, "line": line, "message": message}


def decodable(code: str) -> Callable[[Check], Check]:
    """Make a ``check(specs)`` report a file that is not UTF-8 as one finding of *code*."""

    def wrap(check: Check) -> Check:
        def run(specs: Path) -> list[dict[str, Any]]:
            try:
                return check(specs)
            except _jsonl.Undecodable as bad:
                root, path = specs.resolve(), bad.path.resolve()
                rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
                return [finding(code, rel, bad.line, "the file is not valid UTF-8", bad.fix)]

        return run

    return wrap


def print_text(findings: list[dict[str, Any]]) -> None:
    """Each finding of the check verbs' text mode, its fix on the line after it."""
    for found in findings:
        print(
            f"{found['code']} {found['verdict']} {found['path']}:{found['line']} {found['message']}"
        )
        if found.get("fix"):
            print(spell_fix(found["fix"]))


def histo_findings(
    text: str,
    path: str,
    code: str,
    problems: Callable[[Any], list[str]],
    fix: Callable[[int], str],
) -> list[dict[str, Any]]:
    """One finding per line of the archive *text* that is not JSON or whose record has
    *problems*; *fix* names the act for a line number."""
    out: list[dict[str, Any]] = []
    for number, record, why in _jsonl.walk(text):
        messages = [f"line is not valid JSON: {why}"] if why else problems(record)
        if messages:
            out.append(finding(code, path, number, "; ".join(messages), fix(number)))
    return out
