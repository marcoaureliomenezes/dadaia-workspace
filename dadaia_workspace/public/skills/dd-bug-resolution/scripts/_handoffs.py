#!/usr/bin/env python3
"""The one lister of the reviewer's verdicts, which only `verdict.py` writes."""

from __future__ import annotations

import json
from pathlib import Path

from _platform import Undecodable, read_text

REVIEWER = "dd-code-reviewer"


def reviewer_records(root: Path) -> list[tuple[Path, dict[str, object]]]:
    """(path, data) of every verdict `verdict.py` wrote under *root*; an unreadable file is skipped."""
    found = []
    for path in root.glob(".dadaia/states/verdicts/*/*.handoff.json"):
        try:
            data = json.loads(read_text(path))
        except (OSError, ValueError, Undecodable):
            continue
        if isinstance(data, dict):
            found.append((path, data))
    return found
