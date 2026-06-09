"""dadaia init command."""

from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root_for_init

console = Console()
app = typer.Typer()


@app.command()
def init(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Workspace root path"),
    skip_assets: bool = typer.Option(
        False, "--skip-assets", help="Skip installing public agent assets"
    ),
) -> None:
    """Bootstrap a dadaia workspace: creates .dadaia/ and installs agent assets into .claude/."""
    root = resolve_workspace_root_for_init(workspace, explicit=workspace is not None)
    console.print(f"[bold]Initializing workspace:[/bold] {root}")

    svc = container.build_workspace_service(root)
    _, installed = svc.init(root, skip_assets=skip_assets)

    console.print(f"[green]✓[/green] .dadaia/ bootstrapped at {root / '.dadaia'}")

    if skip_assets:
        console.print("[dim]Skipped public asset installation (--skip-assets)[/dim]")
    else:
        if installed:
            console.print(
                f"[green]✓[/green] Installed {len(installed)} asset(s) into {root / '.claude'}"
            )
            for item in installed:
                console.print(f"  {item}")
        else:
            console.print("[dim]No new assets to install (all up to date)[/dim]")
