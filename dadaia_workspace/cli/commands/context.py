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
from dadaia_workspace.features.spec_context.locking import (
    workspace_lock,
)
from dadaia_workspace.features.spec_context.service import SpecContextService

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
    return workspace_root / ".dadaia" / "sessions"


def _load_session(sessions_dir: Path, session_id: str) -> dict[str, Any] | None:
    """Load a session file, return None if not found."""
    session_file = sessions_dir / f"{session_id}.json"
    if not session_file.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(session_file.read_text())
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
) -> None:
    """Create a new Spec Context Project in state 'dead'."""
    workspace_root = resolve_workspace_root()
    # Look up repo_url from whitelist; fall back gracefully if catalog unavailable
    repo_url = ""
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
        with contextlib.suppress(Exception):
            container.build_public_service().install(ws, target="opencode", force=True)
    except SchemaVersionError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(1) from None
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def dead(name: str = typer.Argument(..., help="Context name to make DEAD")) -> None:
    """Transition a context to DEAD; git sync + remove repo from disk."""
    try:
        ctx = _ctx_service().dead(name)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' is now DEAD")
    except ContextLockedError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def bind(
    name: str = typer.Argument(..., help="Context name to bind to"),
    mode: str = typer.Option(
        ...,
        "--mode",
        help=("Binding mode: read | spec | implementation | review. read/spec are never blocked."),
    ),
    release: str | None = typer.Option(
        None, "--release", help="Release ID (required for implementation and review modes)"
    ),
    force: bool = typer.Option(False, "--force", help="Accepted but no-op (lock-steal replaces)"),
    reason: str = typer.Option("", "--reason", help="Reason note (informational only)"),
) -> None:
    """Bind this shell session to a context.

    Run: eval $(dadaia context bind <name> --mode <mode> [--release <id>])

    Outputs eval-compatible export lines to set DADAIA_CONTEXT, DADAIA_SESSION_ID,
    and DADAIA_MODE in the current shell.
    """
    mode_upper = mode.upper()
    if mode_upper not in ("READ", "SPEC", "IMPLEMENTATION", "REVIEW"):
        err_console.print(
            f"[red]Error:[/red] Invalid mode '{mode}'. Must be one of: read, spec, implementation, review"
        )
        raise typer.Exit(1) from None

    # --release is required for implementation and review
    if mode_upper in ("IMPLEMENTATION", "REVIEW") and not release:
        err_console.print(
            f"[red]Error:[/red] --release <id> is required for --mode {mode_upper.lower()}"
        )
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

    # ALIVE guard: IMPLEMENTATION and REVIEW modes require an ALIVE context (AC-T11-5)
    if mode_upper in ("IMPLEMENTATION", "REVIEW") and ctx.state != ContextState.ALIVE:
        err_console.print(
            f"[red]Error:[/red] Context '{name}' is not ALIVE (state={ctx.state.value}). "
            "Run 'dadaia context alive <name>' first."
        )
        raise typer.Exit(1) from None

    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    now = _now_iso()
    runtime = os.environ.get("DADAIA_AGENT_RUNTIME", "unknown")
    pid = os.getpid()

    session_data: dict = {  # type: ignore[type-arg]
        "session_id": session_id,
        "context": name,
        "mode": f"BOUND_{mode_upper}" if mode_upper in ("IMPLEMENTATION", "REVIEW") else mode_upper,
        "release": release,
        "runtime": runtime,
        "pid": pid,
        "bound_at": now,
        "last_seen_at": now,
        "ttl_seconds": 300,
        "is_stale": False,
    }

    try:
        with workspace_lock(workspace_root):
            session_file = sessions_dir / f"{session_id}.json"
            session_file.write_text(json.dumps(session_data, indent=2))
    except WorkspaceLockTimeoutError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    # Output eval-compatible export lines
    dadaia_mode = mode_upper
    print(f"export DADAIA_CONTEXT={name}")
    print(f"export DADAIA_SESSION_ID={session_id}")
    print(f"export DADAIA_MODE={dadaia_mode}")


@app.command(name="release")
def release_cmd() -> None:
    """Release the current session's binding.

    Run: dadaia context release
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
    session_file = sessions_dir / f"{session_id}.json"

    with workspace_lock(workspace_root):
        session_file.unlink(missing_ok=True)

    console.print(f"[green]✓[/green] Session '[bold]{session_id}[/bold]' released")


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
def delete(name: str = typer.Argument(..., help="Context name to delete")) -> None:
    """Delete a context. Context must be dead."""
    try:
        _ctx_service().delete(name)
        console.print(f"[green]✓[/green] Context '[bold]{name}[/bold]' deleted")
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# Deprecated verbs — exit non-zero with pointer to new verbs (AC-T10d-7)
# ---------------------------------------------------------------------------


@app.command(hidden=True)
def activate(name: str = typer.Argument(..., help="[DEPRECATED]")) -> None:
    """[REMOVED] 'activate' was removed in v2."""
    print(
        "Error: 'activate' was removed in v2. Use: dadaia context alive <name>",
        file=sys.stderr,
    )
    raise typer.Exit(1)


@app.command(hidden=True)
def deactivate(name: str = typer.Argument(..., help="[DEPRECATED]")) -> None:
    """[REMOVED] 'deactivate' was removed in v2."""
    print(
        "Error: 'deactivate' was removed in v2. Use: dadaia context dead <name>",
        file=sys.stderr,
    )
    raise typer.Exit(1)


@app.command(hidden=True)
def promote(name: str = typer.Argument(..., help="[DEPRECATED]")) -> None:
    """[REMOVED] 'promote' was removed in v2."""
    print(
        "Error: 'promote' was removed in v2. Use: dadaia context bind <name> --mode spec",
        file=sys.stderr,
    )
    raise typer.Exit(1)


@app.command(hidden=True)
def use(name: str = typer.Argument(..., help="[DEPRECATED]")) -> None:
    """[REMOVED] 'use' was removed in v2."""
    print(
        "Error: 'use' was removed in v2. Use: dadaia context bind <name> --mode read",
        file=sys.stderr,
    )
    raise typer.Exit(1)
