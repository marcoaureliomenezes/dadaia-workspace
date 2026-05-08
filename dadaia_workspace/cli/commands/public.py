"""dadaia public subcommands."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from dadaia_workspace import container

app = typer.Typer(help="Manage distributed public agent assets.")
console = Console()


def _resolve_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".claude").exists() or (parent / ".dadaia").exists():
            return parent
    return cwd


@app.command()
def install(
    target: Optional[Path] = typer.Option(None, "--target", help="Target .claude/ directory (default: workspace .claude/)"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
) -> None:
    """Install public agent assets (rules, skills, commands) into .claude/."""
    workspace_root = _resolve_workspace()
    svc = container.build_public_service()

    if target:
        from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
        mgr = FileSystemPublicAssetManager()
        installed = mgr.install(target.resolve(), force=force)
    else:
        installed = svc.install(workspace_root, force=force)

    if installed:
        console.print(f"[green]✓[/green] {len(installed)} asset(s) processed:")
        for item in installed:
            console.print(f"  {item}")
    else:
        console.print("[dim]No assets to install.[/dim]")
