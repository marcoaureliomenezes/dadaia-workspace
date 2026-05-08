"""dadaia repos subcommands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container

app = typer.Typer(help="Query the known repos catalog.")
console = Console()


def _resolve_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".dadaia").exists():
            return parent
    return cwd


@app.command(name="list")
def list_repos() -> None:
    """List repos from repos.xlsx catalog."""
    workspace_root = _resolve_workspace()
    svc = container.build_repos_service()
    rows = svc.list_known(workspace_root)

    if not rows:
        console.print("[dim]No repos found. Add repos.xlsx to your workspace root.[/dim]")
        return

    if rows:
        table = Table(title="Known Repos")
        for col in rows[0].keys():
            table.add_column(col)
        for row in rows:
            table.add_row(*row.values())
        console.print(table)
