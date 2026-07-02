"""dadaia context subcommands."""

import contextlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextLockedError,
    ContextNotFoundError,
    ContextStateError,
    RepoCatalogError,
    SchemaVersionError,
    WorkspaceLockTimeoutError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.spec_context import session_identity
from dadaia_workspace.features.spec_context.locking import (
    workspace_lock,
)
from dadaia_workspace.features.spec_context.service import (
    DeadReviewRequiredError,
    DeadSecretFoundError,
    SpecContextService,
)

app = typer.Typer(help="Manage Spec Context Projects.")
console = Console()
err_console = Console(stderr=True)


def _ctx_service() -> SpecContextService:
    try:
        return container.build_spec_context_service(resolve_workspace_root())
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(1) from None
    except SchemaVersionError as exc:
        # Use plain stderr so CliRunner captures it in result.output (mix_stderr=True default)
        print(str(exc), file=sys.stderr)
        raise typer.Exit(1) from None


def _ctx_to_dict(ctx: SpecContextProject) -> dict:  # type: ignore[type-arg]
    return {
        "name": ctx.name,
        "state": ctx.state.value,
        "repo_slug": ctx.repo_slug,
        "repo_url": ctx.repo_url,
        "created_at": ctx.created_at,
        "alive_since": ctx.alive_since,
        "dead_since": ctx.dead_since,
        "current_branch": ctx.current_branch,
    }


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _sessions_dir(workspace_root: Path) -> Path:
    # Session-store path via the single owner (T-011-05 / FR-W1-05, ADR-12) — the bind CLI
    # no longer constructs the ``.dadaia/sessions`` path itself.
    return session_identity.sessions_dir(workspace_root)


def _load_session(sessions_dir: Path, session_id: str) -> dict[str, Any] | None:
    """Load a session file, return None if not found."""
    session_file = sessions_dir / f"{session_id}.json"
    if not session_file.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(session_file.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _session_is_stale(session_data: dict) -> bool:  # type: ignore[type-arg]
    """Check if a session is stale based on TTL."""
    try:
        last_seen = session_data.get("last_seen_at", "")
        ttl = int(session_data.get("ttl_seconds", 300))
        if not last_seen:
            return False
        last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        now = datetime.now(tz=UTC)
        elapsed = (now - last_seen_dt).total_seconds()
        return elapsed > ttl
    except Exception:
        return False


@app.command()
def create(
    name: str = typer.Argument(..., help="Context name"),
    repo: str = typer.Option(..., "--repo", help="Repo slug (directory name under repos/)"),
    url: str | None = typer.Option(
        None,
        "--url",
        help=(
            "Repo clone URL. Overrides the repos-catalog lookup when given — use it "
            "for a repo not in the catalog or to pin an explicit remote."
        ),
    ),
) -> None:
    """Create a new Spec Context Project in state 'dead'."""
    workspace_root = resolve_workspace_root()
    # An explicit --url overrides the catalog lookup (FR-W2-03 a / T-011-08); otherwise
    # look up repo_url from the repos catalog, failing gracefully if unavailable.
    repo_url = ""
    if url is not None:
        repo_url = url
    else:
        try:
            repos_svc = container.build_repos_service()
            rows = repos_svc.list_known(workspace_root)
            for row in rows:
                if row.get("Repo Name") == repo:
                    repo_url = row.get("Repo URL", "")
                    break
        except (RepoCatalogError, Exception):
            pass

    try:
        ctx = _ctx_service().create(name, repo, repo_url)
        console.print(
            f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' created "
            f"(repo: {ctx.repo_slug}, state: {ctx.state})"
        )
    except (ContextAlreadyExistsError, ContextNotFoundError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command(name="list")
def list_all() -> None:
    """List all Spec Context Projects."""
    try:
        contexts = _ctx_service().list_all()
    except SchemaVersionError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(1) from None
    if not contexts:
        console.print("[dim]No contexts found. Use 'dadaia context create' to create one.[/dim]")
        return

    table = Table(title="Spec Context Projects")
    table.add_column("Name", style="bold")
    table.add_column("State")
    table.add_column("Repo")

    state_style = {
        ContextState.ALIVE: "[green]alive[/green]",
        ContextState.DEAD: "[dim]dead[/dim]",
    }

    for ctx in contexts:
        table.add_row(
            ctx.name,
            state_style.get(ctx.state, ctx.state.value),
            ctx.repo_slug,
        )
    console.print(table)


@app.command()
def show(
    name: str | None = typer.Argument(None, help="Context name"),
    json_output: bool = typer.Option(False, "--json", help="Output stable JSON contract"),
) -> None:
    """Show details of a context."""
    svc = _ctx_service()
    if name is None:
        # Show first ALIVE context when no name given (v2: no global primary)
        all_ctxs = svc.list_all()
        ctx = next((c for c in all_ctxs if c.state == ContextState.ALIVE), None)
    else:
        try:
            ctx = svc.show(name)
        except ContextNotFoundError as e:
            err_console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    if json_output:
        if ctx is None:
            print(json.dumps({"context": None}, indent=2))
        else:
            data = _ctx_to_dict(ctx)
            # Add session sub-object (AC-T10d-6)
            session_id = os.environ.get("DADAIA_SESSION_ID")
            session_obj = None
            if session_id:
                workspace_root = resolve_workspace_root()
                sessions_dir = _sessions_dir(workspace_root)
                session_data = _load_session(sessions_dir, session_id)
                if session_data and not _session_is_stale(session_data):
                    session_obj = session_data
            data["session"] = session_obj
            print(json.dumps(data, indent=2))
        return

    if ctx is None:
        msg = f"Context '{name}' not found." if name else "No active context."
        console.print(f"[dim]{msg}[/dim]")
        return

    console.print(f"[bold]Name:[/bold]       {ctx.name}")
    console.print(f"[bold]State:[/bold]      {ctx.state.value}")
    console.print(f"[bold]Repo:[/bold]       {ctx.repo_slug}")
    console.print(f"[bold]Repo URL:[/bold]   {ctx.repo_url or '—'}")
    console.print(f"[bold]Created:[/bold]    {ctx.created_at}")
    console.print(f"[bold]Alive since:[/bold]  {ctx.alive_since or '—'}")
    console.print(f"[bold]Dead since:[/bold]   {ctx.dead_since or '—'}")


@app.command()
def alive(name: str = typer.Argument(..., help="Context name to make ALIVE")) -> None:
    """Transition a context to ALIVE; clone repo if absent. Idempotent if already ALIVE."""
    try:
        ws = resolve_workspace_root()
        ctx = container.build_spec_context_service(ws).alive(name)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' is now ALIVE")
        # FR-S05/S06: a pre-existing specs/ tree below the canonical pattern version is
        # only safe-preserved + add-missing-merged — never silently upgraded. Offer the
        # backup-protected upgrade explicitly so structural drift is the operator's choice.
        with contextlib.suppress(Exception):
            from dadaia_workspace.core import specs_version as _ver

            specs_dir = ws / "repos" / ctx.repo_slug / "specs"
            current = _ver.read_pattern_version(specs_dir)
            if current < _ver.CANONICAL_SPECS_VERSION:
                console.print(
                    f"[yellow]![/yellow] specs pattern version {current} is below the "
                    f"canonical {_ver.CANONICAL_SPECS_VERSION}. Run "
                    f"[bold]dadaia specs upgrade[/bold] (backup-protected) to migrate."
                )
    except SchemaVersionError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(1) from None
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def dead(
    name: str = typer.Argument(..., help="Context name to make DEAD"),
    commit: bool = typer.Option(
        False,
        "--commit",
        help=(
            "Explicit consent to commit+push untracked files. Without it, dead() "
            "refuses if untracked files are present and pushes nothing. With it, a "
            "secret scan runs over the files before push and blocks on any finding."
        ),
    ),
) -> None:
    """Transition a context to DEAD; git sync + remove repo from disk."""
    try:
        ctx = _ctx_service().dead(name, commit=commit)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' is now DEAD")
    except DeadReviewRequiredError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except DeadSecretFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except ContextLockedError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


# Bind mode resolution (FR-R4-01/02). The operator-facing aliases map onto two
# canonical, non-acquiring modes (READ) and two lease-taking modes (IMPLEMENTATION,
# REVIEW). `spec` is a legacy alias of `read`; both persist as READ. Lease-taking modes
# persist with the BOUND_ prefix the gate/lease layer expects.
_BIND_MODE_ALIASES: dict[str, str] = {
    "READ": "READ",
    "SPEC": "READ",  # legacy alias → READ (no lease)
    "IMPLEMENTATION": "IMPLEMENTATION",
    "REVIEW": "REVIEW",
}
_LEASE_TAKING_MODES = ("IMPLEMENTATION", "REVIEW")


@app.command()
def bind(
    name: str = typer.Argument(..., help="Context name to bind to"),
    mode: str = typer.Option(
        "read",
        "--mode",
        help=(
            "Binding mode (optional; default 'read'): read | implementation | review. "
            "Legacy alias: 'spec' maps to read. read never takes a lease."
        ),
    ),
    release: str | None = typer.Option(
        None, "--release", help="Release ID (required for implementation and review modes)"
    ),
    print_env: bool = typer.Option(
        False,
        "--print-env",
        help=(
            "Back-compat: also emit eval-compatible 'export DADAIA_*' lines for operators "
            "who still run 'eval $(dadaia context bind ...)'. Default off — bind persists "
            "the mode in the session record instead."
        ),
    ),
    force: bool = typer.Option(False, "--force", help="Accepted but no-op (lock-steal replaces)"),
    reason: str = typer.Option("", "--reason", help="Reason note (informational only)"),
) -> None:
    """Bind this shell session to a context.

    Run: dadaia context bind <name> [--mode <mode>] [--release <id>]

    With no --mode, binds normally in 'read' (observe) mode — never lock-blocked. The
    bound context, mode, and session id are persisted in the session record (consumed by
    the SDD gate); a human confirmation line is printed. Pass --print-env to additionally
    emit the legacy 'export DADAIA_*' lines for `eval $(...)` workflows.
    """
    mode_upper = mode.upper()
    if mode_upper not in _BIND_MODE_ALIASES:
        err_console.print(
            f"[red]Error:[/red] Invalid mode '{mode}'. Must be one of: "
            "read, spec, implementation, review"
        )
        raise typer.Exit(1) from None

    resolved_mode = _BIND_MODE_ALIASES[mode_upper]

    # --release is required for the lease-taking modes (implementation, review).
    if resolved_mode in _LEASE_TAKING_MODES and not release:
        err_console.print(f"[red]Error:[/red] --release <id> is required for --mode {mode.lower()}")
        raise typer.Exit(1) from None

    workspace_root = resolve_workspace_root()
    sessions_dir = _sessions_dir(workspace_root)

    # Ensure directories exist
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Verify context exists and is ALIVE (AC-T11-5)
    svc = _ctx_service()
    try:
        ctx = svc.show(name)
    except ContextNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    # ALIVE guard: lease-taking modes require an ALIVE context (AC-T11-5)
    if resolved_mode in _LEASE_TAKING_MODES and ctx.state != ContextState.ALIVE:
        err_console.print(
            f"[red]Error:[/red] Context '{name}' is not ALIVE (state={ctx.state.value}). "
            "Run 'dadaia context alive <name>' first."
        )
        raise typer.Exit(1) from None

    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    now = _now_iso()
    runtime = os.environ.get("DADAIA_AGENT_RUNTIME", "unknown")
    pid = os.getpid()

    # The persisted mode the gate reads: lease-taking modes carry the BOUND_ prefix; READ
    # persists bare. (spec → READ, review → BOUND_REVIEW per FR-R4-02 mapping table.)
    persisted_mode = (
        f"BOUND_{resolved_mode}" if resolved_mode in _LEASE_TAKING_MODES else resolved_mode
    )

    session_data: dict = {  # type: ignore[type-arg]
        "session_id": session_id,
        "context": name,
        "mode": persisted_mode,
        "release": release,
        "runtime": runtime,
        "pid": pid,
        "bound_at": now,
        "last_seen_at": now,
        "ttl_seconds": 300,
        "is_stale": False,
    }

    # Persist the session record via the single session-identity owner (FR-R4-02 / R3),
    # and refresh the CONTEXT incumbent pointer to this bind's session id (NF-2 fix). The
    # incumbent pointer makes the bind bind the CONTEXT, not just a throwaway sid: the SDD
    # gate resolves a harness session's mode through ``resolve_identity(ctx)`` →
    # ``<ctx>.ptr`` → this record, so a default in-session `dadaia context bind --mode read`
    # (whose minted sid no harness reports) is honored with no env var. For lease-taking
    # binds the pointer is harmless — ``lease.acquire`` rewrites ``<ctx>.ptr`` to the real
    # acquiring harness sid on first MUTATING write, so the incumbent self-corrects.
    try:
        with workspace_lock(workspace_root):
            session_identity.write_session(workspace_root, session_id, session_data)
            session_identity.set_incumbent(workspace_root, name, session_id)
            # FR-W2-02 (ADR-G5): stamp the bind-epoch marker. This is the SOLE trigger for
            # context-memory injection and the ctx-inject hook's harness-real discovery
            # source — the bind CLI's minted sid is invisible to the harness, so the marker's
            # mtime+name is what the hook scans to re-inject on the next prompt. Standalone
            # file, NOT a `.ptr` field (the `.ptr` is lease-incumbency, untouched here).
            #
            # W1-7/W1-8 (v0.1.47 ancestry-chain amendment): record the bind process's
            # ANCESTRY PID CHAIN (nearest-first — ``os.getppid()`` then its ancestors) so the
            # ctx-inject hook and the specs resolver can attribute this marker by MEMBERSHIP,
            # not by single-pid equality. Recording only ``os.getppid()`` broke when bind ran
            # through a harness Bash tool: the immediate parent is an EPHEMERAL shell that dies
            # between calls, so a later hook/resolver (whose ``getppid`` is a NEW shell) never
            # matched. The chain also captures the long-lived HARNESS pid deeper up, which both
            # a later hook (its own ``os.getppid()`` == harness) and a later ``dadaia`` CLI
            # child (harness in ITS ancestry) share — so attribution survives the shell churn
            # while a concurrent session's disjoint chain still can never steal this injection.
            # If the ancestry port is unavailable, the chain degrades to the single
            # ``os.getppid()`` line (the pre-v0.1.47 behavior).
            session_identity.write_bind_epoch(
                workspace_root,
                name,
                pids=container.build_ancestry_pid_chain(os.getppid()),
            )
    except WorkspaceLockTimeoutError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    # Back-compat escape: emit ONLY the legacy export lines when requested, so the output
    # stays eval-safe for operators still running `eval $(dadaia context bind ... --print-env)`.
    if print_env:
        print(f"export DADAIA_CONTEXT={name}")
        print(f"export DADAIA_SESSION_ID={session_id}")
        print(f"export DADAIA_MODE={resolved_mode}")
        return

    # Human confirmation (NOT shell-export syntax): context, mode, session id.
    console.print(
        f"[green]✓[/green] Bound to '[bold]{name}[/bold]' "
        f"(mode: {resolved_mode.lower()}, session id: {session_id})"
    )


@app.command(name="release")
def release_cmd(
    session: str | None = typer.Option(
        None,
        "--session",
        help=(
            "CLI session id to release (default flow). When omitted, the eval-flow "
            "DADAIA_SESSION_ID is used if set."
        ),
    ),
) -> None:
    """Release the current session's binding AND any lease(s) it holds (FR-W4-03).

    Run: dadaia context release

    Two flows (the CLI-sid/harness-sid split):

    * **eval flow** — ``DADAIA_SESSION_ID`` exported (e.g. ``eval $(dadaia context bind
      ... --print-env)``). Hooks key on the same sid, so every lock record naming it is
      released exactly, then the session record is unlinked.
    * **default flow** — a CLI-minted sid (``--session`` or the latest bind record). The
      lock holder is a harness sid that never matches, so the bound context's lease is
      released ONLY when its holder pid is dead or in the caller's process ancestry; a
      live foreign holder's lease is NEVER released by context name alone.

    In BOTH flows the lease is dropped BEFORE the session record is unlinked, so the
    PostToolUse heartbeat cannot renew a released binding (closes
    ``context-release-leaves-lease-heartbeat-renewing``). DP-3: there is no absence-based
    renewal guard — ``release`` deletes the record, and ``renew_heartbeat`` no-ops on an
    absent/foreign record, so resurrection is structurally impossible.
    """
    from dadaia_workspace import container
    from dadaia_workspace.features.spec_context import lease as _lease

    workspace_root = resolve_workspace_root()
    sessions_dir = _sessions_dir(workspace_root)

    env_sid = os.environ.get("DADAIA_SESSION_ID")
    cli_sid = session or env_sid
    if not cli_sid:
        err_console.print(
            "[red]Error:[/red] No active session. Pass --session <id> or set "
            "DADAIA_SESSION_ID (e.g. eval $(dadaia context bind ... --print-env))."
        )
        raise typer.Exit(1) from None

    session_file = sessions_dir / f"{cli_sid}.json"
    session_data = _load_session(sessions_dir, cli_sid)
    released: list[str] = []

    with workspace_lock(workspace_root):
        if env_sid:
            # Eval flow: the env sid is the lock holder key — release every lease it holds.
            released = _lease.release_for_session(workspace_root, env_sid)
        elif session_data is not None:
            # Default flow: resolve the bound context from the CLI session record and
            # release its lease only when the holder is dead or in our ancestry.
            ctx_name = str(session_data.get("context", ""))
            if ctx_name:
                with contextlib.suppress(Exception):
                    pid_probe = container._build_pid_probe()
                    ancestry_probe = container.build_process_ancestry()

                    def _is_ancestor(holder_pid: int, caller_pid: int) -> bool:
                        from dadaia_workspace.core.protocols.process_ancestry import Ancestry

                        return (
                            ancestry_probe.is_ancestor(holder_pid, caller_pid) is Ancestry.ANCESTOR
                        )

                    holder = _lease.release_context_if_caller_owned(
                        workspace_root,
                        ctx_name,
                        caller_pid=os.getpid(),
                        pid_probe=pid_probe,
                        ancestry=_is_ancestor,
                    )
                    if holder is not None:
                        released.append(ctx_name)

        # Unlink the session record AFTER the lease has been dropped.
        session_file.unlink(missing_ok=True)

    if released:
        console.print(
            f"[green]✓[/green] Session '[bold]{cli_sid}[/bold]' released "
            f"(lease(s) dropped: {', '.join(released)})"
        )
    else:
        console.print(f"[green]✓[/green] Session '[bold]{cli_sid}[/bold]' released")


@app.command()
def heartbeat() -> None:
    """Renew the heartbeat for the current session.

    Reads DADAIA_SESSION_ID from the environment.

    Run: dadaia context heartbeat
    """
    session_id = os.environ.get("DADAIA_SESSION_ID")
    if not session_id:
        err_console.print(
            "[red]Error:[/red] No active session. Set DADAIA_SESSION_ID first "
            "(e.g. eval $(dadaia context bind ...))."
        )
        raise typer.Exit(1) from None

    workspace_root = resolve_workspace_root()
    sessions_dir = _sessions_dir(workspace_root)

    session_data = _load_session(sessions_dir, session_id)
    if session_data is None:
        err_console.print(
            f"[red]Error:[/red] Session '{session_id}' not found. "
            "It may have already been released."
        )
        raise typer.Exit(1) from None

    # Renew the lease heartbeat via lease module
    from dadaia_workspace.features.spec_context import lease as _lease

    ctx_name = session_data.get("context", "")
    if ctx_name:
        _lease.renew_heartbeat(workspace_root, ctx_name, session_id)

    now = _now_iso()
    console.print(
        f"[green]✓[/green] Heartbeat renewed for session '[bold]{session_id}[/bold]' "
        f"(context={ctx_name}, last_seen_at={now})"
    )


@app.command()
def update(
    name: str = typer.Argument(..., help="Context name to update"),
    url: str = typer.Option(..., "--url", help="New repo clone URL to persist"),
) -> None:
    """Repair a context's repo URL (FR-W2-03 c / T-011-08).

    Run: dadaia context update <name> --url <url>

    The repair path for the VPS-migration scenario where no on-disk repo is present
    to back-fill from. Persists through the store update() API, preserving the record
    shape and locking.
    """
    try:
        ctx = _ctx_service().update_url(name, url)
        console.print(
            f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' repo URL set to {ctx.repo_url}"
        )
    except ContextNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def delete(name: str = typer.Argument(..., help="Context name to delete")) -> None:
    """Delete a context. Context must be dead."""
    try:
        _ctx_service().delete(name)
        console.print(f"[green]✓[/green] Context '[bold]{name}[/bold]' deleted")
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


# v2 removals: activate/deactivate/promote/use removed in v0.1.7
