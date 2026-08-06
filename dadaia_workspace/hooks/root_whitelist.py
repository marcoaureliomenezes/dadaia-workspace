"""PreToolUse workspace-root whitelist gate (the canonical, cross-platform gate surface).

The Law: the workspace root may contain ONLY these entries::

    .agents/ .claude/ .codex/ .dadaia/ .kimi-code/ .pi/ repos/  (directories)
    AGENTS.md CLAUDE.md DADAIA.md prompt.md                     (files)

Any other top-level entry is blocked. An operator exception list at
``.dadaia/states/root_exceptions.txt`` (one fnmatch glob per line) documents deliberate
exceptions. The gate classifies the **first path component** of the target relative to the
workspace root (T-47-15): a write blocks when that first component would create a NEW
top-level entry outside the whitelist/exceptions — so a nested write like
``<root>/.opencode/agents/foo.md`` is blocked, while a write into an existing (operator-
created) top-level dir is allowed. Fails open on unparseable input.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from dadaia_workspace.hooks import _common

#: Whitelisted root-level basenames (The Law).
_WHITELIST: frozenset[str] = frozenset(
    {
        ".agents",
        ".claude",
        ".codex",
        ".dadaia",
        ".kimi-code",
        ".pi",
        "repos",
        "AGENTS.md",
        "CLAUDE.md",
        "DADAIA.md",
        "prompt.md",
    }
)

#: Root-level basenames that are FILES (everything else in ``_WHITELIST`` is a
#: directory and renders with a trailing slash in operator-facing text).
_ROOT_FILES: frozenset[str] = frozenset({"AGENTS.md", "CLAUDE.md", "DADAIA.md", "prompt.md"})


def _render_whitelist() -> str:
    """Render the whitelist for the block message — DERIVED from ``_WHITELIST`` so the
    operator-facing text can never drift from the enforced policy (bug class found
    during the v0.2.8 consumer sweep: the message literal omitted ``.kimi-code/`` while
    the policy already allowed it)."""
    dirs = sorted(f"{name}/" for name in _WHITELIST if name not in _ROOT_FILES)
    return " ".join([*dirs, *sorted(_ROOT_FILES)])


def _resolve_workspace() -> Path:
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def _operator_exception(workspace: Path, basename: str) -> bool:
    """Return True if *basename* matches a glob in the operator exception list."""
    efile = workspace / ".dadaia" / "states" / "root_exceptions.txt"
    try:
        text = efile.read_text(encoding="utf-8")
    except OSError:
        return False
    for raw in text.splitlines():
        pat = raw.strip()
        if pat and not pat.startswith("#") and fnmatch.fnmatch(basename, pat):
            return True
    return False


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """Pure root-whitelist policy over an ALREADY-PARSED hook payload.

    Returns a block reason when ANY write target lands a forbidden new entry at the
    workspace root, else ``None`` (ALLOW). This is the reusable policy surface the merged
    ``pre_gate`` entrypoint drives; ``main`` is a thin back-compat wrapper kept one release.

    FR-W4-04: a multi-file apply_patch surfaces every file header; ANY forbidden header
    blocks the whole patch (most restrictive wins).
    """
    name = _common.tool_name(payload)
    # NotebookEdit is not root-relevant in the shell version; keep the same tool set.
    if name not in _common.WRITE_TOOLS - {"NotebookEdit"}:
        return None

    raw_paths = _common.target_paths(payload)
    if not raw_paths:
        return None  # fail open

    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open
        return None

    for raw_path in raw_paths:
        block = _root_violation(workspace, raw_path)
        if block is not None:
            return block
    return None


def _root_violation(workspace: Path, raw_path: str) -> str | None:
    """Return a block reason if *raw_path* creates a forbidden new root entry, else ``None``.

    The gate classifies the **first path component** of the target relative to the
    workspace root (T-47-15). A write blocks when that first component would create a NEW
    top-level entry that is neither whitelisted nor matched by an operator-exception glob —
    which closes the nested hole where ``Write <root>/.opencode/agents/foo.md`` was allowed
    even though it materializes a forbidden new top-level ``.opencode/`` entry.

    An **existing** non-whitelisted top-level entry is presumed operator-created and left
    alone (the operator exception, fail-open): only a not-yet-existing first component is
    blocked, preserving the original new-entry semantics — just computed on the first
    component rather than the immediate parent.

    Fail-open: an unresolvable path or a target outside the workspace root yields ``None``.
    """
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = workspace / fpath

    try:
        ws = workspace.resolve()
        resolved = fpath.resolve()
    except OSError:
        return None

    # The target must live under the workspace root; anything else is not root-relevant.
    try:
        rel = resolved.relative_to(ws)
    except ValueError:
        return None
    if not rel.parts:
        return None

    first = rel.parts[0]
    if first in _WHITELIST:
        return None
    if _operator_exception(workspace, first):
        return None
    # Only a NEW top-level entry is forbidden. An existing non-whitelisted top-level entry
    # is presumed operator-created (origin-ambiguous → fail-open, per the Root Law).
    if (ws / first).exists():
        return None

    return (
        f"[ROOT WHITELIST GATE] Writing '{first}' at workspace root is forbidden. "
        f"The workspace root may only contain: {_render_whitelist()}. Redirect output to "
        ".dadaia/<subdir> (temp files: .dadaia/tmp/<agent>/<date>/; tool caches: "
        ".dadaia/; MCP output: .dadaia/mcps/<server>/). If this entry is genuinely "
        "required at root, add a glob pattern to .dadaia/states/root_exceptions.txt and "
        "retry. Operator-created files are exempt — add them to root_exceptions.txt."
    )
