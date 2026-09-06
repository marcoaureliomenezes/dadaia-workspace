"""dadaia export command."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.workspace_resolver import resolve_cli_workspace_root

console = Console()
err_console = Console(stderr=True)


def export(
    workspace: Annotated[
        Path | None,
        typer.Option("--workspace", "-w", help="Workspace root (default: resolved from cwd)."),
    ] = None,
) -> None:
    """Write `.dadaia/dist/spec-contexts.json` — one record per spec context.

    The file is overwritten on every run. On another workspace, `dadaia import <file>`
    registers each unknown context DEAD and `dadaia context alive <name>` clones it.
    """
    try:
        result = container.build_export_service(resolve_cli_workspace_root(workspace)).run()
    except DadaiaError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    console.print(f"[green]✓[/green] {result.path}  ({result.contexts} contexts)", soft_wrap=True)
