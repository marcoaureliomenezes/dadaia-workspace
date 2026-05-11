"""dadaia public subcommands."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from dadaia_workspace import container

app = typer.Typer(help="Manage distributed public agent assets.")
console = Console()
TargetOption = Annotated[
    str,
    typer.Option(
        "--target",
        help="Runtime target: all, claude, codex, opencode, or agents",
    ),
]


def _resolve_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if any(
            (parent / name).exists()
            for name in (".dadaia", ".agents", ".claude", ".codex", ".opencode")
        ):
            return parent
    return cwd


@app.command()
def stage() -> None:
    """Stage packaged public assets into .dadaia/agentic/."""
    workspace_root = _resolve_workspace()
    staged = container.build_public_service().stage(workspace_root)
    if staged:
        console.print(f"[green]✓[/green] {len(staged)} asset group(s) staged:")
        for item in staged:
            console.print(f"  {item}", markup=False)
    else:
        console.print("[dim]No assets to stage.[/dim]")


@app.command()
def install(
    target: TargetOption = "all",
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
) -> None:
    """Install staged public assets into runtime projections."""
    workspace_root = _resolve_workspace()
    svc = container.build_public_service()
    installed = svc.install(workspace_root, target=target, force=force)

    if installed:
        console.print(f"[green]✓[/green] {len(installed)} asset(s) processed:")
        for item in installed:
            console.print(f"  {item}", markup=False)
    else:
        console.print("[dim]No assets to install.[/dim]")


@app.command()
def doctor() -> None:
    """Diagnose drift between package source, staging, and runtime projections."""
    workspace_root = _resolve_workspace()
    reports = container.build_public_service().doctor(workspace_root)
    for item in reports:
        if item.startswith("[ok]"):
            console.print(item, style="green", markup=False)
        elif item.startswith("[missing]") or item.startswith("[drift]"):
            console.print(item, style="yellow", markup=False)
        elif item.startswith("[unsupported]"):
            console.print(item, style="cyan", markup=False)
        else:
            console.print(item, markup=False)
