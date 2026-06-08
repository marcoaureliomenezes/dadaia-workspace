"""dadaia clean — reclaim stale files from ephemeral .dadaia/ zones (T-016-Z03)."""

from __future__ import annotations

import typer

from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.workspace_clean.service import WorkspaceCleanService

app = typer.Typer(help="Reclaim stale files from .dadaia/ ephemeral zones.")


@app.callback(invoke_without_command=True)
def clean(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help=("List stale files without deleting (default). Pass --no-dry-run to actually delete."),
    ),
) -> None:
    """Reclaim stale files from .dadaia/tmp/, .dadaia/reports/, .dadaia/dev-report/.

    Dry-run is the default — run with --no-dry-run to actually delete files.

    Operator-protected files (listed in .dadaia/states/root_exceptions.txt)
    are never deleted.  Files outside .dadaia/ are never touched.
    """
    workspace_root = resolve_workspace_root()
    svc = WorkspaceCleanService(workspace_root)
    result = svc.clean(dry_run=dry_run)

    if not result.candidates:
        typer.echo("No stale files found in ephemeral zones.")
        return

    if dry_run:
        typer.echo(f"Dry run — {len(result.candidates)} stale file(s) would be reclaimed:")
        for candidate in result.candidates:
            typer.echo(f"  [{candidate.zone}] {candidate.path}  ({candidate.reason})")
        typer.echo("\nRun 'dadaia clean --no-dry-run' to delete.")
    else:
        typer.echo(f"Reclaimed {len(result.deleted)} file(s):")
        for path in result.deleted:
            typer.echo(f"  deleted: {path}")
        skipped = len(result.candidates) - len(result.deleted)
        if skipped > 0:
            typer.echo(f"  skipped: {skipped} file(s) (protected or already gone)")
