"""dadaia academy subcommands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import ContextAlreadyExistsError, ContextNotFoundError
from dadaia_workspace.features.academy.service import AcademyService

app = typer.Typer(help="Manage Academy courses.")
console = Console()
err_console = Console(stderr=True)


def _resolve_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".dadaia").exists():
            return parent
    return cwd


def _academy_service() -> AcademyService:
    workspace_root = _resolve_workspace()
    return container.build_academy_service(workspace_root)


@app.command()
def modules() -> None:
    """List available Academy modules from the built-in knowledge base."""
    svc = _academy_service()
    mods = svc.list_modules()
    if not mods:
        console.print("[dim]No modules found.[/dim]")
        return
    for number, name in mods:
        console.print(f"  {number:2d}  {name}")


@app.command(name="list")
def list_all() -> None:
    """List all courses in this workspace."""
    svc = _academy_service()
    courses = svc.list_all()
    if not courses:
        console.print("[dim]No courses found. Use 'dadaia academy create' to start one.[/dim]")
        return

    table = Table(title="Academy Courses")
    table.add_column("Slug", style="bold")
    table.add_column("Name")
    table.add_column("Module")
    table.add_column("Created")

    for course in courses:
        table.add_row(
            course.slug,
            course.name,
            f"{course.module_number} — {course.module_name}",
            course.created_at[:10],
        )
    console.print(table)


@app.command()
def create(
    name: str = typer.Argument(..., help="Course name"),
    module: int = typer.Option(..., "--module", "-m", help="Module number"),
) -> None:
    """Create a new course from a knowledge base module."""
    try:
        course = _academy_service().create(name, module)
        console.print(
            f"[green]✓[/green] Course '[bold]{course.slug}[/bold]' created "
            f"from module {course.module_number} ({course.module_name})"
        )
        console.print(f"  Course dir: {course.course_dir}")
    except (ContextAlreadyExistsError, ContextNotFoundError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def update(
    slug: str = typer.Argument(..., help="Course slug"),
    module: int = typer.Option(..., "--module", "-m", help="New module number"),
) -> None:
    """Update an existing course to use a different module."""
    try:
        course = _academy_service().update(slug, module)
        console.print(
            f"[green]✓[/green] Course '[bold]{course.slug}[/bold]' updated "
            f"to module {course.module_number} ({course.module_name})"
        )
    except ContextNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def delete(
    slug: str = typer.Argument(..., help="Course slug to delete"),
) -> None:
    """Delete a course and its working directory."""
    try:
        _academy_service().delete(slug)
        console.print(f"[green]✓[/green] Course '[bold]{slug}[/bold]' deleted")
    except ContextNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
