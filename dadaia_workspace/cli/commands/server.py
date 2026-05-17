"""dadaia server subcommands — port registry management."""

import json
import sys
import webbrowser
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import (
    PortConflictError,
    PortNotRegisteredError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.models.server_registry import PortStatus
from dadaia_workspace.features.server_registry.service import ServerRegistryService

app = typer.Typer(help="Manage the dev server port registry.")
console = Console()
err_console = Console(stderr=True)


def _resolve_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".dadaia").exists():
            return parent
    return cwd


def _svc() -> ServerRegistryService:
    try:
        return container.build_server_registry_service(_resolve_workspace())
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(1) from None


@app.command(name="list")
def list_servers(
    project: str | None = typer.Option(None, "--project", help="Filter by project name"),
    status: str = typer.Option("active", "--status", help="Filter: active | stale | all"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON array"),
) -> None:
    """List registered dev servers."""
    entries = _svc().list_entries(project=project, include_stale=True)

    if status == "active":
        entries = [(e, s) for e, s in entries if s == PortStatus.ACTIVE]
    elif status == "stale":
        entries = [(e, s) for e, s in entries if s == PortStatus.STALE]

    if json_output:
        data = [
            {
                "port": e.port,
                "project": e.project,
                "url": e.url or f"http://localhost:{e.port}",
                "status": s.value,
                "pid": e.pid,
                "reserved_at": e.reserved_at,
                "expires_at": e.expires_at,
                "description": e.description,
            }
            for e, s in entries
        ]
        print(json.dumps(data, indent=2))
        return

    if not entries:
        console.print("[dim]No servers registered.[/dim]")
        return

    table = Table(title="Server Registry")
    table.add_column("Port", style="bold")
    table.add_column("Project")
    table.add_column("URL")
    table.add_column("Status")
    table.add_column("Description")

    status_style = {
        PortStatus.ACTIVE: "[green]● running[/green]",
        PortStatus.STALE: "[dim]○ stale[/dim]",
    }

    for e, s in entries:
        table.add_row(
            str(e.port),
            e.project,
            e.url or f"http://localhost:{e.port}",
            status_style.get(s, s.value),
            e.description or "—",
        )
    console.print(table)


@app.command()
def next(
    project: str = typer.Option(..., "--project", help="Project name"),
    min_port: int = typer.Option(3000, "--min-port"),
    max_port: int = typer.Option(3999, "--max-port"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Suggest the next available port for a project (deterministic, does not register)."""
    try:
        port, is_base = _svc().next_port(project, min_port=min_port, max_port=max_port)
    except PortNotRegisteredError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    url = f"http://localhost:{port}"
    if json_output:
        print(json.dumps({"port": port, "url": url, "is_base_port": is_base}, indent=2))
        return

    if not is_base:
        console.print(
            f"[yellow]Note:[/yellow] base port for '{project}' was occupied; using next free port."
        )
    console.print(f"[green]►[/green] Port [bold]{port}[/bold]  →  {url}")


@app.command()
def register(
    port: int = typer.Option(..., "--port"),
    project: str = typer.Option(..., "--project"),
    url: str = typer.Option("", "--url"),
    pid: int | None = typer.Option(None, "--pid"),
    ttl: int = typer.Option(8, "--ttl", help="Hours until entry expires"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Register a port for a project."""
    try:
        entry = _svc().register(
            port=port,
            project=project,
            url=url,
            pid=pid,
            ttl_hours=ttl,
            description=description,
        )
        console.print(
            f"[green]✓[/green] Port [bold]{entry.port}[/bold] registered for '{entry.project}'  →  {entry.url}"
        )
    except PortConflictError as e:
        err_console.print(f"[red]Conflict:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def release(
    port: int | None = typer.Option(None, "--port"),
    project: str | None = typer.Option(None, "--project"),
) -> None:
    """Release a port (or all ports for a project)."""
    svc = _svc()
    if port is None and project is None:
        err_console.print("[red]Error:[/red] Provide --port and/or --project.")
        raise typer.Exit(1) from None

    try:
        if project is not None and port is None:
            released = svc.release_all(project=project)
            if not released:
                console.print(f"[dim]No registered ports for project '{project}'.[/dim]")
            else:
                for e in released:
                    console.print(f"[green]✓[/green] Released port {e.port} ('{e.project}')")
        else:
            svc.release(port=port, project=project)  # type: ignore[arg-type]
            console.print(f"[green]✓[/green] Port [bold]{port}[/bold] released")
    except (PortConflictError, PortNotRegisteredError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def show(
    project: str = typer.Option(..., "--project"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show registered servers for a project."""
    entries = _svc().show_project(project)
    if not entries:
        console.print(f"[dim]No servers registered for '{project}'.[/dim]")
        console.print(
            f"  Tip: run [bold]dadaia server next --project {project}[/bold] to get a port."
        )
        return

    if json_output:
        data = [
            {
                "port": e.port,
                "project": e.project,
                "url": e.url or f"http://localhost:{e.port}",
                "status": s.value,
                "pid": e.pid,
                "reserved_at": e.reserved_at,
                "expires_at": e.expires_at,
                "description": e.description,
            }
            for e, s in entries
        ]
        print(json.dumps(data, indent=2))
        return

    for e, s in entries:
        status_label = (
            "[green]● running[/green]" if s == PortStatus.ACTIVE else "[dim]○ stale[/dim]"
        )
        url = e.url or f"http://localhost:{e.port}"
        console.print(f"  Port [bold]{e.port}[/bold]  {url}  {status_label}")
        if e.description:
            console.print(f"  [dim]{e.description}[/dim]")


@app.command()
def clean(
    dry_run: bool = typer.Option(False, "--dry-run", help="List stale entries without removing"),
) -> None:
    """Remove stale port entries (dead PID or expired TTL)."""
    removed = _svc().clean(dry_run=dry_run)
    if not removed:
        console.print("[dim]No stale entries found.[/dim]")
        return
    verb = "Would remove" if dry_run else "Removed"
    for e in removed:
        console.print(f"[yellow]{verb}:[/yellow] port {e.port} ('{e.project}')")


@app.command()
def dashboard(
    port: int = typer.Option(4999, "--port", help="Dashboard HTTP port"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open browser automatically"),
) -> None:
    """[DEPRECATED] Start the server registry dashboard (bookmarkable URL).

    Use 'dadaia panel' instead. This command will be removed in the next release.
    """
    import warnings

    warnings.warn(
        "'dadaia server dashboard' is deprecated. Use 'dadaia panel' instead."
        " This command will be removed in the next release.",
        DeprecationWarning,
        stacklevel=2,
    )
    print(
        "[deprecation] 'dadaia server dashboard' will be removed in a future release."
        " Use 'dadaia panel' instead.",
        file=sys.stderr,
    )

    from http.server import ThreadingHTTPServer

    from dadaia_workspace.features.server_registry.dashboard import DashboardHandler

    ws = _resolve_workspace()
    states_dir = ws / ".dadaia" / "states"
    DashboardHandler.states_dir = states_dir

    url = f"http://127.0.0.1:{port}"
    console.print(f"[green]►[/green] Serving registry dashboard at [bold]{url}[/bold]")
    console.print("  Press [bold]Ctrl+C[/bold] to stop.")

    if not no_open:
        webbrowser.open(url)

    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        console.print("\n[dim]Dashboard stopped.[/dim]")
