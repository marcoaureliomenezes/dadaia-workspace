"""The context registry file read: its entries and the repo slugs they own — one reader for
the resolution authority (``core.invocation``), the layout gate and the doctor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from dadaia_workspace.core.exceptions import SchemaVersionError

# The keys every ``contexts`` row carries for the store to build its model from; the
# tolerant readers (:func:`entries`) ask none of them.
ROW_KEYS = ("name", "state", "repo_slug", "repo_url", "created_at")


def read(path: Path) -> dict[str, object]:
    """THE registry parse: the ``{"contexts": [...]}`` object at *path*. Absent, unparseable
    or any other shape (``{}`` included) is unreadable, never empty: :class:`SchemaVersionError`."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, RecursionError, ValueError):  # too deep a nest is unreadable too
        data = None
    if not isinstance(data, dict) or not isinstance(data.get("contexts"), list):
        shape = '{"contexts": [...]}'
        raise SchemaVersionError(
            f"{path} is not one {shape} object.",
            f"Operator action: rewrite {path} as one {shape} object",
        )
    return data


def entries(workspace_root: Path) -> list[dict[str, object]]:
    """The context registry's ``contexts`` rows; raises :class:`SchemaVersionError` (:func:`read`)."""
    found = read(workspace_root / ".dadaia" / "states" / "spec_contexts.json")["contexts"]
    return [e for e in cast("list[object]", found) if isinstance(e, dict)]


def entry_slugs(entry: dict[str, object]) -> tuple[object, ...]:
    """A registry entry's repo slugs, unvalidated: the main one (falsy when absent) first."""
    associated = entry.get("associated_repos")
    listed = associated if isinstance(associated, list) else []
    return (
        entry.get("repo_slug") or entry.get("repo"),
        *(a.get("slug") for a in listed if isinstance(a, dict)),
    )


def registered_slugs(workspace_root: Path) -> tuple[frozenset[str], frozenset[str]]:
    """What ``repos/`` and ``worktrees/`` admit: every repo slug of every registered context,
    then of every ALIVE one; an unreadable registry admits all (``*``), never nothing."""
    try:
        found = entries(workspace_root)
    except SchemaVersionError:
        return frozenset("*"), frozenset("*")
    alive = [e for e in found if str(e.get("state", "")).lower() == "alive"]
    every, live = (
        frozenset(s for e in group for s in entry_slugs(e) if isinstance(s, str) and s)
        for group in (found, alive)
    )
    return every, live
