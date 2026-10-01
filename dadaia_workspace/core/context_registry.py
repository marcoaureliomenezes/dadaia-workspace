"""The context registry file read: its entries and the repo slugs they own — one reader for
the resolution authority (``core.invocation``), the layout gate and the doctor."""

from __future__ import annotations

import json
from pathlib import Path


def entries(workspace_root: Path) -> list[dict[str, object]] | None:
    """The context registry's ``contexts`` list, or ``None`` when it cannot be read or is
    not a ``{"contexts": [...]}`` object."""
    registry = workspace_root / ".dadaia" / "states" / "spec_contexts.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None
    contexts = data.get("contexts", []) if isinstance(data, dict) else None
    return [e for e in contexts if isinstance(e, dict)] if isinstance(contexts, list) else None


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
    found = entries(workspace_root)
    if found is None:
        return frozenset("*"), frozenset("*")
    alive = [e for e in found if str(e.get("state", "")).lower() == "alive"]
    every, live = (
        frozenset(s for e in group for s in entry_slugs(e) if isinstance(s, str) and s)
        for group in (found, alive)
    )
    return every, live
