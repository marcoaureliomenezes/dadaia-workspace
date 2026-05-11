"""CLI command: dadaia doctor [--fix]."""

from pathlib import Path

import typer

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError

app = typer.Typer(help="Diagnose and repair workspace state.")


def _resolve_workspace() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".dadaia").exists():
            return parent
    return cwd


err_console = typer.echo


@app.callback(invoke_without_command=True)
def doctor(
    fix: bool = typer.Option(False, "--fix", help="Apply automatic repairs."),
) -> None:
    """Diagnose workspace state invariants and optionally repair them."""
    workspace_root = _resolve_workspace()
    try:
        dr = container.build_doctor_service(workspace_root)
    except WorkspaceNotInitializedError:
        typer.echo("Error: Workspace not initialized. Run 'dadaia init' first.", err=True)
        raise typer.Exit(1) from None

    issues = dr.check()

    if not issues:
        typer.echo("All invariants OK — workspace is healthy.")
        return

    typer.echo(f"Found {len(issues)} issue(s):")
    for issue in issues:
        fixable = "[fixable]" if issue.fixable else "[manual]"
        typer.echo(f"  {issue.code} {fixable} — {issue.description}")

    if fix:
        actions = dr.fix()
        typer.echo(f"\nApplied {len(actions)} repair(s):")
        for action in actions:
            typer.echo(f"  - {action}")
    else:
        typer.echo("\nRun 'dadaia doctor --fix' to apply automatic repairs.")
