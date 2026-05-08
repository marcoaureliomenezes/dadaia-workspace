"""dadaia init command."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from dadaia_workspace import container

console = Console()
app = typer.Typer()


def _resolve_workspace(workspace: Optional[Path]) -> Path:
    if workspace:
        return workspace.resolve()
    # Walk up from CWD looking for .claude/ or .dadaia/
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".claude").exists() or (parent / ".dadaia").exists():
            return parent
    return cwd


@app.command()
def init(
    workspace: Optional[Path] = typer.Option(None, "--workspace", "-w", help="Workspace root path"),
    skip_assets: bool = typer.Option(False, "--skip-assets", help="Skip installing public agent assets"),
) -> None:
    """Bootstrap a dadaia workspace: creates .dadaia/ and installs agent assets into .claude/."""
    root = _resolve_workspace(workspace)
    console.print(f"[bold]Initializing workspace:[/bold] {root}")

    svc = container.build_workspace_service(root)
    _, installed = svc.init(root, skip_assets=skip_assets)

    console.print(f"[green]✓[/green] .dadaia/ bootstrapped at {root / '.dadaia'}")

    if skip_assets:
        console.print("[dim]Skipped public asset installation (--skip-assets)[/dim]")
    else:
        if installed:
            console.print(f"[green]✓[/green] Installed {len(installed)} asset(s) into {root / '.claude'}")
            for item in installed:
                console.print(f"  {item}")
        else:
            console.print("[dim]No new assets to install (all up to date)[/dim]")
