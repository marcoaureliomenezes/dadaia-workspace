#!/usr/bin/env python3
"""The one lister of the reviewer's verdict handoffs."""

from __future__ import annotations

import json
from pathlib import Path

REVIEWER = "dd-code-reviewer"


def reviewer_records(root: Path) -> list[tuple[Path, dict[str, object]]]:
    """(path, data) of every reviewer handoff in the handoff zone and the reaper's hold of it;
    an unreadable file is skipped."""
    found = []
    for path in [*root.glob(".dadaia/handoff/*/*.handoff.json"), *root.glob(".dadaia/reaped/*/.dadaia/handoff/*/*.handoff.json")]:  # fmt: skip
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("agent") == REVIEWER:
            found.append((path, data))
    return found
