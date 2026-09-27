"""PreToolUse layout gate: a write whose new entry ``workspace_layout.verdict`` judges
``slop`` — at the root, ``.dadaia/`` or a closed-canon zone — is blocked; the doctor
asks the same function, so ALLOW ⇔ not slop. Fails open on unparseable input.
"""

from __future__ import annotations

import os
from pathlib import Path

from dadaia_workspace.core import invocation, workspace_layout
from dadaia_workspace.core.cli_line import shell_line
from dadaia_workspace.hooks import _common

#: Whitelisted root-level basenames (The Law) — DERIVED from the single authority
#: ``core/workspace_layout.py`` so this hook and the workspace doctor can never diverge
#: (they did, the day the root `AGENTS.md` map was added to one and not the other).
_WHITELIST: frozenset[str] = (
    workspace_layout.ROOT_ALLOWED_DIRS | workspace_layout.ROOT_ALLOWED_FILES
)

#: Root-level basenames that are FILES (everything else in ``_WHITELIST`` is a
#: directory and renders with a trailing slash in operator-facing text).
_ROOT_FILES: frozenset[str] = workspace_layout.ROOT_ALLOWED_FILES


def _render_whitelist() -> str:
    """Render the whitelist for the block message — DERIVED from ``_WHITELIST`` so the
    operator-facing text can never drift from the enforced policy (bug class found
    during the v0.2.8 consumer sweep: the message literal omitted ``.kimi-code/`` while
    the policy already allowed it)."""
    dirs = sorted(f"{name}/" for name in _WHITELIST if name not in _ROOT_FILES)
    return " ".join([*dirs, *sorted(_ROOT_FILES)])


def _exception_globs(workspace: Path) -> tuple[str, ...]:
    try:
        text = (workspace / workspace_layout.INSTANCE_EXCEPTIONS).read_text(encoding="utf-8")
    except OSError:
        return ()
    return workspace_layout.parse_exception_globs(text)


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """Pure root-whitelist policy over an ALREADY-PARSED hook payload.

    Returns a block reason when ANY write target lands a forbidden new entry at the
    workspace root, else ``None`` (ALLOW). This is the reusable policy surface the merged
    ``pre_gate`` entrypoint drives; ``main`` is a thin back-compat wrapper kept one release.

    FR-W4-04: a multi-file apply_patch surfaces every file header; ANY forbidden header
    blocks the whole patch (most restrictive wins).
    """
    name = str(payload.get("tool_name") or "")
    # NotebookEdit is not root-relevant in the shell version; keep the same tool set.
    if name not in _common.WRITE_TOOLS - {"NotebookEdit"}:
        return None

    raw_paths = _common.target_paths(payload)
    if not raw_paths:
        return None  # fail open

    try:
        workspace = invocation.resolve(env=os.environ, cwd=Path.cwd()).workspace_root
        if workspace is None:
            raise RuntimeError("workspace not resolved")
    except Exception:  # noqa: BLE001 — fail-open
        return None

    for raw_path in raw_paths:
        block = _root_violation(workspace, raw_path)
        if block is not None:
            return block
    return None


def _root_violation(workspace: Path, raw_path: str) -> str | None:
    """A block reason when the entry *raw_path* would create is not ``canon`` or
    ``operator`` by ``workspace_layout.verdict`` — the doctor's own answer, so the gate
    never ALLOWs what the reaper moves (ADR 0058: an existing entry is not presumed the
    operator's). Fail-open on an unresolvable path or a target outside the workspace."""
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = workspace / fpath
    try:
        ws = workspace.resolve()
        rel = fpath.resolve().relative_to(ws)
    except (OSError, ValueError):
        return None
    if not rel.parts:
        return None
    if workspace_layout.verdict(rel.as_posix(), False, _exception_globs(ws)) != "slop":
        return None
    return (
        f"[ROOT WHITELIST GATE] Writing '{rel.as_posix()}' creates an entry the layout law "
        f"does not admit. The workspace root may only contain: {_render_whitelist()}; "
        ".dadaia/ only its zones; a closed-canon zone only its canon. Temp files belong in "
        f"{ws / '.dadaia' / 'tmp'}/<agent>/<YYYYMMDD>/ (operator exceptions: "
        f"{workspace_layout.INSTANCE_EXCEPTIONS}, operator-written).\n"
        f"fix: {shell_line('mkdir', '-p', str(ws / '.dadaia' / 'tmp'))}"
    )
