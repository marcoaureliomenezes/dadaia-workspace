"""dadaia context subcommands."""

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject

app = typer.Typer(help="Manage Spec Context Projects.")
console = Console()
err_console = Console(stderr=True)


def _resolve_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".dadaia").exists():
            return parent
    return cwd


def _ctx_service() -> "container.SpecContextService":  # type: ignore[name-defined]
    try:
        return container.build_spec_context_service(_resolve_workspace())
    except WorkspaceNotInitializedError:
        err_console.print("[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first.")
        raise typer.Exit(1)


def _ctx_to_dict(ctx: SpecContextProject) -> dict:  # type: ignore[type-arg]
    return {
        "name": ctx.name,
        "state": ctx.state.value,
        "context_dir": str(ctx.context_dir) if ctx.context_dir else None,
        "specs_dir": str(ctx.specs_dir) if ctx.specs_dir else None,
        "primary_repo": {
            "repo_ref": ctx.primary_repo.repo_ref,
            "source_kind": ctx.primary_repo.source_kind.value,
            "materialized_path": str(ctx.primary_repo.materialized_path) if ctx.primary_repo.materialized_path else None,
        },
        "secondary_repos": [
            {
                "repo_ref": r.repo_ref,
                "source_kind": r.source_kind.value,
                "materialized_path": str(r.materialized_path) if r.materialized_path else None,
            }
            for r in ctx.secondary_repos
        ],
    }


@app.command()
def create(
    name: str = typer.Argument(..., help="Context name"),
    repo: str = typer.Option(..., "--repo", help="Primary repo ref (URL or local path)"),
    secondary: list[str] = typer.Option([], "--secondary", help="Secondary repo refs"),
) -> None:
    """Create a new Spec Context Project in state 'inativo'."""
    try:
        ctx = _ctx_service().create(name, repo, secondary or None)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' created (state: {ctx.state})")
    except ContextAlreadyExistsError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="list")
def list_all() -> None:
    """List all Spec Context Projects."""
    contexts = _ctx_service().list_all()
    if not contexts:
        console.print("[dim]No contexts found. Use 'dadaia context create' to create one.[/dim]")
        return

    table = Table(title="Spec Context Projects")
    table.add_column("Name", style="bold")
    table.add_column("State")
    table.add_column("Primary Repo")
    table.add_column("Secondaries")

    state_style = {
        ContextState.ATIVO: "[green]ativo[/green]",
        ContextState.STANDBY: "[yellow]standby[/yellow]",
        ContextState.INATIVO: "[dim]inativo[/dim]",
    }

    for ctx in contexts:
        table.add_row(
            ctx.name,
            state_style.get(ctx.state, ctx.state.value),
            ctx.primary_repo.repo_ref,
            ", ".join(r.repo_ref for r in ctx.secondary_repos) or "—",
        )
    console.print(table)


@app.command()
def show(
    name: Optional[str] = typer.Argument(None, help="Context name (omit for active context)"),
    json_output: bool = typer.Option(False, "--json", help="Output stable JSON contract"),
) -> None:
    """Show details of a context. Omit name to show the active context."""
    ctx = _ctx_service().show(name)
    selected_by = "name" if name else "active"

    if json_output:
        payload = {
            "context": _ctx_to_dict(ctx) if ctx else None,
            "selected_by": selected_by,
        }
        print(json.dumps(payload, indent=2))
        return

    if ctx is None:
        msg = f"Context '{name}' not found." if name else "No active context."
        console.print(f"[dim]{msg}[/dim]")
        return

    console.print(f"[bold]Name:[/bold]        {ctx.name}")
    console.print(f"[bold]State:[/bold]       {ctx.state.value}")
    console.print(f"[bold]Primary:[/bold]     {ctx.primary_repo.repo_ref}")
    if ctx.secondary_repos:
        console.print(f"[bold]Secondary:[/bold]  {', '.join(r.repo_ref for r in ctx.secondary_repos)}")
    if ctx.context_dir:
        console.print(f"[bold]Context dir:[/bold] {ctx.context_dir}")
    if ctx.specs_dir:
        console.print(f"[bold]Specs dir:[/bold]  {ctx.specs_dir}")


@app.command()
def activate(name: str = typer.Argument(..., help="Context name to activate")) -> None:
    """Activate a context, materializing its repos if needed."""
    try:
        ctx = _ctx_service().activate(name)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' is now active")
        if ctx.specs_dir:
            console.print(f"  specs_dir: {ctx.specs_dir}")
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def deactivate() -> None:
    """Deactivate the current active context (moves to standby)."""
    try:
        ctx = _ctx_service().deactivate()
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' moved to standby")
    except ContextStateError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def delete(name: str = typer.Argument(..., help="Context name to delete")) -> None:
    """Delete a context. Syncs managed repos before removing if in standby."""
    try:
        _ctx_service().delete(name)
        console.print(f"[green]✓[/green] Context '[bold]{name}[/bold]' deleted")
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="add-repo")
def add_repo(
    name: str = typer.Argument(..., help="Context name"),
    repo: str = typer.Option(..., "--repo", help="Repo ref to add as secondary"),
) -> None:
    """Add a secondary repo to an existing context."""
    try:
        ctx = _ctx_service().add_repo(name, repo)
        console.print(f"[green]✓[/green] Added '{repo}' to context '[bold]{ctx.name}[/bold]'")
    except (ContextNotFoundError, ContextAlreadyExistsError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="remove-repo")
def remove_repo(
    name: str = typer.Argument(..., help="Context name"),
    repo: str = typer.Option(..., "--repo", help="Repo ref to remove"),
) -> None:
    """Remove a secondary repo from a context."""
    try:
        ctx = _ctx_service().remove_repo(name, repo)
        console.print(f"[green]✓[/green] Removed '{repo}' from context '[bold]{ctx.name}[/bold]'")
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
