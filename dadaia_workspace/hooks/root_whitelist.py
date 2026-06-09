"""PreToolUse workspace-root whitelist gate (Windows-safe port of ``root-whitelist-gate.sh``).

The Law: the workspace root may contain ONLY these entries::

    .agents/ .claude/ .codex/ .dadaia/ .opencode/ repos/   (directories)
    AGENTS.md CLAUDE.md prompt.md                            (files)

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
        ".opencode",
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


def main() -> int:
    """Run the root-whitelist gate. Returns 0 always (block via the stdout envelope)."""
    payload = _common.read_stdin_json()
    name = _common.tool_name(payload)
    # NotebookEdit is not root-relevant in the shell version; keep the same tool set.
    if name not in _common.WRITE_TOOLS - {"NotebookEdit"}:
        return 0

    raw_path = _common.target_path(payload)
    if not raw_path:
        return 0  # fail open

    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open
        return 0

    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = workspace / fpath

    # Only gate writes whose immediate parent is exactly the workspace root.
    try:
        is_at_root = fpath.parent.resolve() == workspace.resolve()
    except OSError:
        return 0
    if not is_at_root:
        return 0

    basename = fpath.name
    if basename in _WHITELIST:
        return 0
    if _operator_exception(workspace, basename):
        return 0

    _common.emit_block(
        f"[ROOT WHITELIST GATE] Writing '{basename}' at workspace root is forbidden. "
        "The workspace root may only contain: .agents/ .claude/ .codex/ .dadaia/ "
        ".opencode/ repos/ AGENTS.md CLAUDE.md prompt.md. Redirect output to "
        ".dadaia/<subdir> (temp files: .dadaia/tmp/<agent>/<date>/; tool caches: "
        ".dadaia/; MCP output: .dadaia/mcps/<server>/). If this entry is genuinely "
        "required at root, add a glob pattern to .dadaia/states/root_exceptions.txt and "
        "retry. Operator-created files are exempt — add them to root_exceptions.txt."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
