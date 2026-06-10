"""PreToolUse SDD gate (the canonical, cross-platform gate surface).

This hook is the enforcement entrypoint the harness invokes as
``python -m dadaia_workspace.hooks.sdd_gate``. It does NOT re-derive the gate policy:
it delegates classification + decision to :func:`gate_policy.classify_path` and
:func:`gate_policy.evaluate`, which is the single source of truth (avoids a third
drifting copy alongside the bash gate).

Parity invariants preserved verbatim from the rc-4 shell gate:

1. **PATH-first context slug.** The context is derived from the write-target path
   (``repos/<slug>/...``); ``DADAIA_CONTEXT`` is consulted only as an override when the
   path is under no repo. A write under ``repos/B/...`` therefore never acquires
   ``repos/A``'s lease (fixes gate-cross-context-lock-contamination).
2. **PROTECTED is the sole fail-CLOSED path.** ``.dadaia/sessions/`` writes are blocked
   unconditionally (SEC-01); every other class fails OPEN.
3. **Fail-open posture.** Only a genuine live-foreign ``LockHeldError`` BLOCKs (surfaced
   by ``gate_policy.evaluate``); any other error → ALLOW. The hook never deadlocks.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dadaia_workspace.features.spec_context import gate_policy
from dadaia_workspace.hooks import _common

_SLUG_STRIP = re.compile(r"[^A-Za-z0-9_-]")


def _resolve_workspace() -> Path:
    """Resolve the workspace root: ``WORKSPACE_ROOT`` env wins, else walk up from cwd."""
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


def _context_slug(workspace: Path, fpath: Path) -> str:
    """Derive the context slug PATH-first from the write target.

    A target under ``<ws>/repos/<slug>/...`` belongs to context ``<slug>`` regardless of
    which context is first-ALIVE in the registry. ``DADAIA_CONTEXT`` is honored only as an
    explicit override when the path is under no repo. The result is sanitized to
    ``[A-Za-z0-9_-]`` (CWE-22).
    """
    repos = workspace / "repos"
    slug = ""
    try:
        rel = fpath.resolve().relative_to(repos.resolve())
        parts = rel.parts
        if parts:
            slug = parts[0]
    except (ValueError, OSError):
        slug = ""
    if not slug:
        slug = os.environ.get("DADAIA_CONTEXT", "")  # explicit override only
    return _SLUG_STRIP.sub("", slug or "")


def _active_field(specs_dir: Path, field: str) -> str:
    """Read a ``<field>: <value>`` line from ``releases/ACTIVE.md`` (empty on miss)."""
    active = specs_dir / "releases" / "ACTIVE.md"
    try:
        text = active.read_text(encoding="utf-8")
    except OSError:
        return ""
    pat = re.compile(rf"^{re.escape(field)}:\s*(.+?)\s*$", re.MULTILINE)
    m = pat.search(text)
    return m.group(1) if m else ""


def main() -> int:
    """Run the SDD gate. Returns 0 always (block is signaled via the stdout envelope)."""
    payload = _common.read_stdin_json()
    name = _common.tool_name(payload)
    if not _common.is_write_tool(name):
        return 0

    raw_path = _common.target_path(payload)
    if not raw_path:
        # Fail-safe: unparseable target → ALLOW (never deadlock on a parse miss).
        return 0

    try:
        workspace = _resolve_workspace()
    except Exception:  # noqa: BLE001 — fail-open: unresolved workspace must not block
        return 0

    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = workspace / fpath

    # Workspace-relative path for the policy classifier (POSIX-style separators).
    try:
        rel_path = fpath.resolve().relative_to(workspace.resolve()).as_posix()
    except (ValueError, OSError):
        rel_path = fpath.as_posix()

    cls = gate_policy.classify_path(rel_path)

    # PROTECTED short-circuit (sole fail-CLOSED path): no context/lease work needed.
    if cls == gate_policy.PathClass.PROTECTED:
        decision, reason = gate_policy.evaluate(
            workspace,
            rel_path,
            ctx="",
            phase="",
            session_id="",
            release="",
            mode="",
        )
        if decision == gate_policy.Decision.BLOCK:
            _common.emit_block(reason)
        return 0

    ctx = _context_slug(workspace, fpath)
    specs_dir = workspace / "repos" / ctx / "specs" if ctx else workspace / "specs"
    phase = _active_field(specs_dir, "phase")
    release = _active_field(specs_dir, "release") or "none"
    session_id = _common.resolve_session_id(payload, default="anon-session")
    mode = os.environ.get("DADAIA_MODE", "IMPLEMENTATION")

    # MUTATING with no resolvable context → fail open (UNGATED, no lease), matching shell.
    if cls == gate_policy.PathClass.MUTATING and not ctx:
        return 0

    decision, reason = gate_policy.evaluate(
        workspace,
        rel_path,
        ctx=ctx,
        phase=phase,
        session_id=session_id,
        release=release,
        mode=mode,
    )
    if decision == gate_policy.Decision.BLOCK:
        _common.emit_block(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
