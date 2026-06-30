"""dadaia lock subcommands (v0.1.6: single-record TTL-lease management)."""

import os
import uuid
from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.spec_context import lease as _lease
from dadaia_workspace.hooks.sdd_gate import _active_field, _build_pid_probe

app = typer.Typer(help="Manage SDD implementation lease records.")
console = Console()
err_console = Console(stderr=True)


def _active_release_for(workspace: Path, ctx: str) -> str:
    """Resolve the context's live ACTIVE release id (``"none"`` when archived/absent).

    T-43-10: ``lock steal`` is release-aware — a lease pinned to a release that is NOT this
    context's ACTIVE release is reclaimable despite a live holder pid. The specs dir is the
    in-repo context tree (``repos/<ctx>/specs``) for a Spec Context Project, or the
    workspace-root ``specs`` for the self-hosting case. Never returns ``None`` so the steal
    path always applies release-aware reclaim (an absent/`none` ACTIVE release means any
    release-pinned lease is reclaimable).
    """
    specs_dir = workspace / "repos" / ctx / "specs"
    if not (specs_dir / "releases" / "ACTIVE.md").exists():
        specs_dir = workspace / "specs"
    return _active_field(specs_dir, "release") or "none"


def _caller_session_id() -> str:
    """Resolve the caller's stable session id, matching the gate's resolution order.

    The lease must be transferred to the caller's *actual* harness session so that
    subsequent gated writes (which the gate keys on the same env vars) RENEW the
    lease instead of seeing a foreign holder and blocking. Falls back to a random
    id only when nothing identifies the session.
    """
    for var in (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
    ):
        val = os.environ.get(var)
        if val:
            return "".join(c for c in val if c.isalnum() or c in "_-")
    return f"sess_{uuid.uuid4().hex[:8]}"


@app.command()
def steal(
    ctx: str = typer.Argument(..., help="Context name whose lease to steal"),
) -> None:
    """Reclaim a stale lease record for the current caller.

    Reads .dadaia/states/ctx_locks/<ctx>.lock.json and calls lease.steal().
    Refuses if the lease is live — including a TTL-expired record whose recorded
    holder pid is still alive (the pid-liveness probe veto, T-011-01): a
    genuinely-running session is never stolen even past TTL. A record with no
    ``pid`` field (legacy/pre-pid) degrades to the TTL rule.

    Use when a session died mid-work and its lease record is stale (TTL expired and
    the holder is no longer running).

    Release-aware (T-43-10): a lease pinned to a release that is NOT this context's live
    ACTIVE release (e.g. a closed/archived release whose holder process is still idling
    alive) is reclaimable despite the live pid — it is semantically dead. The pid-veto is
    retained ONLY for a lease pinned to the live ACTIVE release, so a genuinely-active
    current-release session is never stolen.
    """
    workspace = resolve_workspace_root()
    session_id = _caller_session_id()
    pid_probe = _build_pid_probe()
    active_release = _active_release_for(workspace, ctx)

    ok, rec = _lease.steal(
        workspace, ctx, session_id, pid_probe=pid_probe, active_release=active_release
    )
    if ok:
        console.print(
            f"[green]✓[/green] Lease for '[bold]{ctx}[/bold]' stolen. "
            f"New session_id: [bold]{session_id}[/bold]"
        )
        raise typer.Exit(0)
    else:
        err_console.print(
            "Lease is live (holder pid alive or heartbeat < TTL); refusing steal. "
            "Verify the holder is actually dead."
        )
        raise typer.Exit(1)
