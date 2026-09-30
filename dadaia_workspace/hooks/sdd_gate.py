"""PreToolUse SDD gate: resolves ONE Invocation and the target's ``scope()`` per write
target and delegates the verdict to :mod:`gate_policy`. The gate reads no
``_RELEASE.json``."""

from __future__ import annotations

import os
from pathlib import Path

from dadaia_workspace.core import invocation
from dadaia_workspace.features.spec_context import gate_policy
from dadaia_workspace.hooks import _common
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore


def _evaluate_target(
    payload: dict[str, object], workspace: Path | None, raw_path: str
) -> tuple[gate_policy.Decision, str]:
    """``(ALLOW, "")`` or ``(BLOCK, reason)`` for one target."""
    fpath = Path(raw_path)
    if not fpath.is_absolute():
        fpath = (workspace or Path.cwd()) / fpath
    # target-first root: a nested sandbox under the cwd never shadows the root owning fpath
    inv = invocation.resolve(target_path=fpath, env=os.environ, cwd=Path.cwd())
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
    repo, zone = invocation.scope(effective_workspace, fpath)
    return gate_policy.evaluate(
        rel_path,
        root=effective_workspace,
        projected=projected,
        zone=zone,
        repo=repo,
        owner=invocation.context_name_for_repo_slug(effective_workspace, repo) if repo else None,
        context=inv.bind.context_name,
        repos=inv.bind.repos,
        has_id=inv.session_id is not None,
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
