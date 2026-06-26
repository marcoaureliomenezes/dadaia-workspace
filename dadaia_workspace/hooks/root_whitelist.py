"""PreToolUse workspace-root whitelist gate (the canonical, cross-platform gate surface).

The Law: the workspace root may contain ONLY these entries::

    .agents/ .claude/ .codex/ .dadaia/ .pi/ repos/             (directories)
    AGENTS.md CLAUDE.md prompt.md                               (files)

Any other top-level entry is blocked. An operator exception list at
``.dadaia/states/root_exceptions.txt`` (one fnmatch glob per line) documents deliberate
exceptions. The gate only fires on writes whose immediate parent IS the workspace root;
writes under any subdirectory are allowed. Fails open on unparseable input.
"""

from __future__ import annotations

import fnmatch
import os
import sys
from pathlib import Path

from dadaia_workspace.hooks import _common

#: Whitelisted root-level basenames (The Law).
_WHITELIST: frozenset[str] = frozenset(
    {
        ".agents",
        ".claude",
        ".codex",
        ".dadaia",
        ".pi",
        "repos",
        "AGENTS.md",
        "CLAUDE.md",
        "prompt.md",
    }
)


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


def main() -> int:
    """Run the root-whitelist gate. Returns 0 always (block via the stdout envelope)."""
    payload = _common.read_stdin_json()
    reason = evaluate_payload(payload)
    if reason is not None:
        _common.emit_block(reason)
    return 0


def _root_violation(workspace: Path, raw_path: str) -> str | None:
    """Return a block reason if *raw_path* writes a forbidden new root entry, else ``None``.

    Fail-open: an unresolvable parent or a non-root target yields ``None`` (allowed).
    """
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = workspace / fpath

    # Only gate writes whose immediate parent is exactly the workspace root.
    try:
        is_at_root = fpath.parent.resolve() == workspace.resolve()
    except OSError:
        return None
    if not is_at_root:
        return None

    basename = fpath.name
    if basename in _WHITELIST:
        return None
    if _operator_exception(workspace, basename):
        return None

    return (
        f"[ROOT WHITELIST GATE] Writing '{basename}' at workspace root is forbidden. "
        "The workspace root may only contain: .agents/ .claude/ .codex/ .dadaia/ "
        ".pi/ repos/ AGENTS.md CLAUDE.md prompt.md. Redirect output to "
        ".dadaia/<subdir> (temp files: .dadaia/tmp/<agent>/<date>/; tool caches: "
        ".dadaia/; MCP output: .dadaia/mcps/<server>/). If this entry is genuinely "
        "required at root, add a glob pattern to .dadaia/states/root_exceptions.txt and "
        "retry. Operator-created files are exempt — add them to root_exceptions.txt."
    )


if __name__ == "__main__":
    sys.exit(main())
