"""dadaia export command."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.cli._fail import fail
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.workspace_resolver import resolve_cli_workspace_root

console = Console()


def export(
    workspace: Annotated[
        Path | None,
        typer.Option("--workspace", "-w", help="Workspace root (default: resolved from cwd)."),
    ] = None,
    hard: Annotated[
        bool,
        typer.Option(
            "--hard", help="Write `workspace-export.tar.gz`: the JSON plus the unpushed work."
        ),
    ] = False,
) -> None:
    """Write `.dadaia/dist/spec-contexts.json` — one record per spec context, read-only.

    The file is overwritten on every run. `--hard` writes `.dadaia/dist/workspace-export.tar.gz`
    instead: the same JSON plus a bundle of each open lane and `wt-rc` tree and each pause
    bundle, every bundle scanned for secrets.
    """
    try:
        result = container.build_export_service(resolve_cli_workspace_root(workspace)).run(hard)
    except DadaiaError as exc:
        fail(exc)
    console.print(f"[green]✓[/green] {result.path}  ({result.contexts} contexts)", soft_wrap=True)
