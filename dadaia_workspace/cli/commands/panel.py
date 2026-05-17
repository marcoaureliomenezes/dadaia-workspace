"""dadaia panel — local workspace UI served at http://127.0.0.1:<port>/."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.server import build_panel_http_server, serve_blocking

_LOOPBACK_ONLY: frozenset[str] = frozenset({"127.0.0.1"})

app = typer.Typer(help="Start the Dadaia Workspace Panel (local UI).")


def _resolve_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".dadaia").exists():
            return parent
    return cwd


@app.callback(invoke_without_command=True)
def panel(
    port: int = typer.Option(4999, "--port", help="HTTP port to bind"),
    no_open: bool = typer.Option(False, "--no-open", help="Skip automatic browser launch"),
    bind: str = typer.Option("127.0.0.1", "--bind", help="Bind address (loopback only)"),
) -> None:
    """Start the Dadaia Workspace Panel at http://<bind>:<port>/."""
    if bind not in _LOOPBACK_ONLY:
        typer.echo(
            f"Release-1 supports loopback bind only. Got: {bind}",
            err=True,
        )
        raise typer.Exit(2)

    workspace_root = _resolve_workspace()

    try:
        views = container.build_panel_views(workspace_root)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Failed to initialise panel: {exc}", err=True)
        raise typer.Exit(1) from None

    handler_cls = make_handler_class(views)

    try:
        server = build_panel_http_server(host=bind, port=port, handler_factory=handler_cls)
    except OSError:
        typer.echo(
            f"Port {port} already in use. Find the holder with: lsof -i :{port}",
            err=True,
        )
        raise typer.Exit(1) from None

    typer.echo(f"Panel running at http://{bind}:{port}/")

    if not no_open:
        webbrowser.open(f"http://{bind}:{port}/")

    serve_blocking(server)
    sys.exit(0)
