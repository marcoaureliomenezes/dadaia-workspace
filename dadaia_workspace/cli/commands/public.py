"""dadaia public subcommands."""

from typing import Annotated, Literal

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

app = typer.Typer(help="Manage distributed public agent assets.")
console = Console()
TargetOption = Annotated[
    str,
    typer.Option(
        "--target",
        help="Runtime target: all, claude, codex, opencode, or agents",
    ),
]


@app.command()
def stage() -> None:
    """Stage packaged public assets into .dadaia/agentic/."""
    workspace_root = resolve_workspace_root()
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
    repos_only: bool = typer.Option(
        False, "--repos-only", help="Install only consumer repo assets."
    ),
    workspace_only: bool = typer.Option(
        False, "--workspace-only", help="Install only workspace-root guardrail pair."
    ),
) -> None:
    """Install staged public assets into runtime projections."""
    if repos_only and workspace_only:
        typer.echo("Error: --repos-only and --workspace-only are mutually exclusive.", err=True)
        raise typer.Exit(1)

    scope: Literal["all", "repos-only", "workspace-only"]
    if repos_only:
        scope = "repos-only"
    elif workspace_only:
        scope = "workspace-only"
    else:
        scope = "all"

    workspace_root = resolve_workspace_root()
    svc = container.build_public_service()
    installed = svc.install(workspace_root, target=target, force=force, scope=scope)

    if installed:
        console.print(f"[green]✓[/green] {len(installed)} asset(s) processed:")
        for item in installed:
            console.print(f"  {item}", markup=False)
    else:
        console.print("[dim]No assets to install.[/dim]")


@app.command()
def doctor() -> None:
    """Diagnose drift between package source, staging, and runtime projections."""
    workspace_root = resolve_workspace_root()
    reports = container.build_public_service().doctor(workspace_root)
    for item in reports:
        if item.startswith("[ok]"):
            console.print(item, style="green", markup=False)
        elif item.startswith("[missing]") or item.startswith("[drift]"):
            console.print(item, style="yellow", markup=False)
        elif item.startswith("[not-applicable]") or item.startswith("[unsupported]"):
            console.print(item, style="cyan", markup=False)
        else:
            console.print(item, markup=False)
