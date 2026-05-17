"""dadaia context subcommands."""

import json

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    RepoCatalogError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.spec_context.service import SpecContextService

app = typer.Typer(help="Manage Spec Context Projects.")
console = Console()
err_console = Console(stderr=True)


def _ctx_service() -> SpecContextService:
    try:
        return container.build_spec_context_service(resolve_workspace_root())
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(1) from None


def _ctx_to_dict(ctx: SpecContextProject) -> dict:  # type: ignore[type-arg]
    return {
        "name": ctx.name,
        "state": ctx.state.value,
        "repo_slug": ctx.repo_slug,
        "repo_url": ctx.repo_url,
        "is_primary": ctx.is_primary,
        "created_at": ctx.created_at,
        "activated_at": ctx.activated_at,
        "current_branch": ctx.current_branch,
    }


@app.command()
def create(
    name: str = typer.Argument(..., help="Context name"),
    repo: str = typer.Option(..., "--repo", help="Repo slug (directory name under repos/)"),
) -> None:
    """Create a new Spec Context Project in state 'inativo'."""
    workspace_root = resolve_workspace_root()
    # Look up repo_url from whitelist; fall back gracefully if catalog unavailable
    repo_url = ""
    try:
        repos_svc = container.build_repos_service()
        rows = repos_svc.list_known(workspace_root)
        for row in rows:
            if row.get("Repo Name") == repo:
                repo_url = row.get("Repo URL", "")
                break
    except (RepoCatalogError, Exception):
        pass

    try:
        ctx = _ctx_service().create(name, repo, repo_url)
        console.print(
            f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' created "
            f"(repo: {ctx.repo_slug}, state: {ctx.state})"
        )
    except (ContextAlreadyExistsError, ContextNotFoundError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


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
    table.add_column("Primary")
    table.add_column("Repo")

    state_style = {
        ContextState.ATIVO: "[green]ativo[/green]",
        ContextState.INATIVO: "[dim]inativo[/dim]",
    }

    for ctx in contexts:
        table.add_row(
            ctx.name,
            state_style.get(ctx.state, ctx.state.value),
            "[bold yellow]✓[/bold yellow]" if ctx.is_primary else "",
            ctx.repo_slug,
        )
    console.print(table)


@app.command()
def show(
    name: str | None = typer.Argument(None, help="Context name"),
    json_output: bool = typer.Option(False, "--json", help="Output stable JSON contract"),
) -> None:
    """Show details of a context."""
    svc = _ctx_service()
    if name is None:
        # Show primary context
        all_ctxs = svc.list_all()
        ctx = next((c for c in all_ctxs if c.is_primary), None)
    else:
        try:
            ctx = svc.show(name)
        except ContextNotFoundError as e:
            err_console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    if json_output:
        if ctx is None:
            print(json.dumps({"context": None}, indent=2))
        else:
            print(json.dumps(_ctx_to_dict(ctx), indent=2))
        return

    if ctx is None:
        msg = f"Context '{name}' not found." if name else "No primary context."
        console.print(f"[dim]{msg}[/dim]")
        return

    console.print(f"[bold]Name:[/bold]       {ctx.name}")
    console.print(f"[bold]State:[/bold]      {ctx.state.value}")
    console.print(f"[bold]Primary:[/bold]    {ctx.is_primary}")
    console.print(f"[bold]Repo:[/bold]       {ctx.repo_slug}")
    console.print(f"[bold]Repo URL:[/bold]   {ctx.repo_url or '—'}")
    console.print(f"[bold]Created:[/bold]    {ctx.created_at}")
    console.print(f"[bold]Activated:[/bold]  {ctx.activated_at or '—'}")


@app.command()
def activate(name: str = typer.Argument(..., help="Context name to activate")) -> None:
    """Activate a context (clone repo if absent; auto-promote if no primary)."""
    try:
        ws = resolve_workspace_root()
        ctx = container.build_spec_context_service(ws).activate(name)
        primary_note = " [bold yellow](primary)[/bold yellow]" if ctx.is_primary else ""
        console.print(
            f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' is now active{primary_note}"
        )
        if ctx.is_primary:
            container.build_public_service().install(ws, target="opencode", force=True)
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def deactivate(name: str = typer.Argument(..., help="Context name to deactivate")) -> None:
    """Deactivate a context (git sync + remove repo from disk)."""
    try:
        ctx = _ctx_service().deactivate(name)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' deactivated")
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def promote(name: str = typer.Argument(..., help="Context name to promote as primary")) -> None:
    """Promote an active context as the workspace primary."""
    try:
        ws = resolve_workspace_root()
        ctx = container.build_spec_context_service(ws).promote(name)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' is now primary")
        container.build_public_service().install(ws, target="opencode", force=True)
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def delete(name: str = typer.Argument(..., help="Context name to delete")) -> None:
    """Delete a context. Context must be inactive."""
    try:
        _ctx_service().delete(name)
        console.print(f"[green]✓[/green] Context '[bold]{name}[/bold]' deleted")
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def use(name: str = typer.Argument(..., help="Context name to isolate this session to")) -> None:
    """Isolate this shell session to a specific context without changing global state.

    Run: eval $(dadaia context use <name>)

    Sets DADAIA_CONTEXT for the current shell only. Does NOT modify spec_contexts.json
    or primary_context.json.
    """
    all_ctxs = _ctx_service().list_all()
    ctx = next((c for c in all_ctxs if c.name == name), None)
    if ctx is None:
        available = ", ".join(c.name for c in all_ctxs) or "none"
        err_console.print(f"[red]Error:[/red] Context '{name}' not found. Available: {available}")
        raise typer.Exit(1) from None
    print(f"export DADAIA_CONTEXT={name}")
