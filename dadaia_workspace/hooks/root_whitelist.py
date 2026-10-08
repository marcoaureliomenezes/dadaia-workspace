"""PreToolUse layout gate: a write that creates an entry ``workspace_layout.verdict`` judges
``slop`` — at the root, ``.dadaia/``, a closed-canon zone, ``repos/`` or ``worktrees/`` —
is blocked; the doctor asks the same function and reports existing slop. Fails open.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import context_registry, invocation, workspace_layout, workspace_resolver
from dadaia_workspace.core.cli_line import mkdir_line
from dadaia_workspace.hooks import _common


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """The block reason when ANY write target lands a slop entry, else ``None``."""
    name = str(payload.get("tool_name") or "")
    if name not in _common.WRITE_TOOLS - {"NotebookEdit"}:
        return None

    raw_paths = _common.target_paths(payload)
    if not raw_paths:
        return None
    anchor = invocation.resolve_root(cwd=Path.cwd(), target_path=None)
    raw = payload.get("agent_type")  # Claude Code sets it inside a subagent; CWE-22
    plain = isinstance(raw, str) and _AGENT_RE.fullmatch(raw) and raw not in (".", "..")
    agent = str(raw) if plain else "main-thread"
    return next(filter(None, (_root_violation(anchor, p, agent) for p in raw_paths)), None)


#: One path segment: no separator; `.` and `..` refused beside it.
_AGENT_RE = re.compile(r"[A-Za-z0-9._-]+")


def _root_violation(anchor: Path | None, raw_path: str, agent: str) -> str | None:
    """A block reason when *raw_path* creates the entry ``workspace_layout.verdict`` judges
    slop in the root owning it, fenced or not; ``None`` outside any or when it exists."""
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = (anchor or Path.cwd()) / fpath
    ws = workspace_resolver.owning_root(fpath)  # an ancestor of the resolved fpath
    if ws is None:
        return None
    rel = fpath.resolve().relative_to(ws)
    globs = workspace_layout.operator_globs(ws)[0]
    slugs = context_registry.registered_slugs(ws)
    heads = [Path(*rel.parts[:k]) for k in range(1, len(rel.parts) + 1)]
    verdicts = [workspace_layout.verdict(h.as_posix(), h != rel, globs, *slugs) for h in heads]
    if "slop" not in verdicts or (ws / heads[verdicts.index("slop")]).exists():
        return None
    return (
        f"[ROOT WHITELIST GATE] Writing '{rel.as_posix()}' creates an entry the layout law "
        f"does not admit. The workspace root may only contain: {workspace_layout.root_entries_display()}; "
        ".dadaia/ only its zones; a closed-canon zone only its canon. Temp files belong in "
        f"{ws / '.dadaia' / 'tmp'}/<agent>/<YYYYMMDD>/.\n"
        f"fix: {mkdir_line(ws / '.dadaia' / 'tmp' / agent / f'{datetime.now(UTC):%Y%m%d}')}"
    )
