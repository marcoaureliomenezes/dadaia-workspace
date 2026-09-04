"""dadaia import command."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

console = Console()
err_console = Console(stderr=True)


def import_workspace(
    file: Annotated[Path, typer.Argument(help="A spec-contexts.json written by 'dadaia export'.")],
    workspace: Annotated[
        Path | None,
        typer.Option("--workspace", "-w", help="Workspace root (default: resolved from cwd)."),
    ] = None,
) -> None:
    """Register every context of a `dadaia export` file this workspace does not know as DEAD.

    Known names are skipped; `dadaia context alive <name>` clones each registered context.
    """
    try:
        result = container.build_import_service(resolve_workspace_root(workspace)).run(file)
    except (DadaiaError, ValueError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    for name, reason in result.skipped:
        console.print(f"  [dim]skipped ({escape(reason)})[/dim]   {escape(name)}")
    for name in result.registered:
        console.print(f"  [green]registered (dead)[/green]  {name}")
    if result.registered:
        console.print("\nRestore each context with:")
        for name in result.registered:
            console.print(f"  dadaia context alive {name}", soft_wrap=True)
