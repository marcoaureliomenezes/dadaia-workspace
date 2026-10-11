#!/usr/bin/env python3
"""The one finding record of the ledger validators, and the walk of an append-only archive."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


def finding(code: str, path: str, line: int, message: str, fix: str) -> dict[str, Any]:
    return {"code": code, "verdict": "error", "path": path, "line": line, "message": message,
            "fix": fix}  # fmt: skip


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
    for number, raw in enumerate(text.split("\n"), start=1):
        try:
            messages = problems(json.loads(raw)) if raw.strip() else []
        except json.JSONDecodeError as exc:
            messages = [f"line is not valid JSON: {exc.msg}"]
        if messages:
            out.append(finding(code, path, number, "; ".join(messages), fix(number)))
    return out
