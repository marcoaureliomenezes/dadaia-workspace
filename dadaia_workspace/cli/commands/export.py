"""dadaia export command."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.export import ExportOptions
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

console = Console()
err_console = Console(stderr=True)


def export(
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory (default: .dadaia/dist/)."),
    ] = None,
    include_reports: Annotated[
        bool,
        typer.Option("--include-reports", help="Include .dadaia/reports/ in the archive."),
    ] = False,
    exclude_mnt: Annotated[
        bool,
        typer.Option("--exclude-mnt", help="Exclude mnt/ container volumes from the archive."),
    ] = False,
    list_only: Annotated[
        bool,
        typer.Option("--list", help="Dry-run: print manifest JSON without creating the archive."),
    ] = False,
) -> None:
    """Export workspace state to a portable .tar.gz archive.

    The archive includes all durable state (.dadaia/states, academy, scripts,
    configs, .claude rules) needed to restore the workspace on a new VPS.
    Secrets (*.env), caches (.venv, .npm, linuxbrew) and repos/ are excluded.
    """
    workspace_root = resolve_workspace_root()
    try:
        svc = container.build_export_service(workspace_root)
        options = ExportOptions(
            output=output,
            include_reports=include_reports,
            exclude_mnt=exclude_mnt,
            list_only=list_only,
        )
        result = svc.run(options)
    except DadaiaError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    if list_only:
        return

    size_kb = result.size // 1024
    console.print(f"[green]✓[/green] {result.path}  ({size_kb} KB)")
