"""dadaia repos subcommands."""

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

app = typer.Typer(help="Query the known repos catalog.")
console = Console()


@app.command(name="list")
def list_repos() -> None:
    """List repos from repos.xlsx catalog."""
    workspace_root = resolve_workspace_root()
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
