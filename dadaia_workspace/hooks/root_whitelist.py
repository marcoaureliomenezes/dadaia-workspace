"""PreToolUse layout gate: a write whose new entry ``workspace_layout.verdict`` judges
``slop`` — at the root, ``.dadaia/``, a closed-canon zone, ``repos/`` or ``worktrees/`` —
is blocked; the doctor asks the same function, so ALLOW ⇔ not slop. Fails open on unparseable input.
"""

from __future__ import annotations

import os
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
    try:
        anchor = invocation.resolve(env=os.environ, cwd=Path.cwd()).workspace_root
    except Exception:  # noqa: BLE001 — fail-open
        return None
    return next(filter(None, (_root_violation(anchor, p) for p in raw_paths)), None)


def _root_violation(anchor: Path | None, raw_path: str) -> str | None:
    """A block reason when ``workspace_layout.verdict`` judges *raw_path*'s entry slop in
    the root owning it, fenced or not — the doctor's own answer; ``None`` outside any."""
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = (anchor or Path.cwd()) / fpath
    ws = workspace_resolver.owning_root(fpath)  # an ancestor of the resolved fpath
    if ws is None:
        return None
    rel = fpath.resolve().relative_to(ws)
    globs = workspace_layout.operator_globs(ws)[0]
    slugs = context_registry.registered_slugs(ws)
    if not rel.parts or workspace_layout.verdict(rel.as_posix(), False, globs, *slugs) != "slop":
        return None
    return (
        f"[ROOT WHITELIST GATE] Writing '{rel.as_posix()}' creates an entry the layout law "
        f"does not admit. The workspace root may only contain: {workspace_layout.root_entries_display()}; "
        ".dadaia/ only its zones; a closed-canon zone only its canon. Temp files belong in "
        f"{ws / '.dadaia' / 'tmp'}/<agent>/<YYYYMMDD>/.\n"
        f"fix: {mkdir_line(ws / '.dadaia' / 'tmp')}"
    )
