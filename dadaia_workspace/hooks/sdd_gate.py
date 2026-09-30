"""PreToolUse SDD gate: resolves ONE Invocation per write target (the target's
``repos/<slug>`` wins over every other rung) and delegates the verdict to
:mod:`gate_policy`. PROTECTED is the sole fail-closed path; the only other block is a
MUTATING write into a repo another context owns. The gate reads no ``_RELEASE.json``."""

from __future__ import annotations

import os
from pathlib import Path

from dadaia_workspace.core import invocation
from dadaia_workspace.features.spec_context import gate_policy
from dadaia_workspace.hooks import _common
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore


def _target_slug(workspace: Path, fpath: Path) -> str | None:
    """The ``repos/<slug>`` the write target lands in, or ``None`` for a root path."""
    try:
        rel = fpath.resolve().relative_to((workspace / "repos").resolve())
    except (ValueError, OSError):
        return None
    return rel.parts[0] if rel.parts else None


def _evaluate_target(
    payload: dict[str, object], workspace: Path | None, raw_path: str
) -> tuple[gate_policy.Decision, str]:
    """``(ALLOW, "")`` or ``(BLOCK, reason)`` for one target; an unattributable MUTATING
    write fails open."""
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = (workspace or Path.cwd()) / fpath
    # target-first root: a nested sandbox under the cwd never shadows the root owning fpath
    inv = invocation.resolve(target_path=fpath, payload=payload, env=os.environ, cwd=Path.cwd())
    effective_workspace = inv.workspace_root or workspace
    if effective_workspace is None:
        return gate_policy.Decision.ALLOW, ""  # fail-open: no root owns the target

    try:
        rel_path = fpath.resolve().relative_to(effective_workspace.resolve()).as_posix()
    except (ValueError, OSError):
        rel_path = fpath.as_posix()

    states = effective_workspace / ".dadaia" / "states"  # the install ledger is the law set
    ledger = JsonInstallLedgerStore().read(states)
    projected = frozenset(e.relpath for e in ledger.entries) if ledger else frozenset()
    projected |= {JsonInstallLedgerStore.path(states).relative_to(effective_workspace).as_posix()}
    cls = gate_policy.classify_path(rel_path, projected)

    if cls == gate_policy.PathClass.PROTECTED:
        return gate_policy.evaluate(rel_path, root=effective_workspace, projected=projected)

    ctx = inv.context_name or ""
    # an unregistered slug has no owner, so the policy fails open on it
    target_slug = _target_slug(effective_workspace, fpath)
    owner_repos = invocation.all_repos(effective_workspace, ctx) if target_slug else frozenset()
    target_owner = ctx if target_slug in owner_repos else None
    return gate_policy.evaluate(
        rel_path,
        root=effective_workspace,
        bound_context=inv.bind.context_name,
        bound_repos=inv.bind.repos,
        target_slug=target_slug,
        target_owner=target_owner,
        bound_by_env=inv.session_id is None,
    )


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """The first BLOCK reason over EVERY write target, else ``None``; no parseable target allows."""
    name = str(payload.get("tool_name") or "")
    if not _common.is_write_tool(name):
        return None
    raw_paths = _common.target_paths(payload)
    if not raw_paths:
        return None
    # the cwd root only anchors a relative target
    workspace = invocation.resolve(env=os.environ, cwd=Path.cwd()).workspace_root
    for raw_path in raw_paths:
        decision, reason = _evaluate_target(payload, workspace, raw_path)
        if decision == gate_policy.Decision.BLOCK:
            return reason
    return None
