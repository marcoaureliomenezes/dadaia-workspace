"""dadaia init command."""

from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core import harness_registry
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root_for_init

console = Console()
app = typer.Typer()


@app.command()
def init(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Workspace root path"),
    skip_assets: bool = typer.Option(
        False, "--skip-assets", help="Skip installing public agent assets"
    ),
    harness: str = typer.Option(
        "all",
        "--harness",
        help="Harness set to scaffold: 'all' or a comma-separated subset of claude,codex,pi.",
    ),
) -> None:
    """Bootstrap a dadaia workspace: creates .dadaia/ and projects agent assets for the chosen harness set (default all: .claude/, .codex/, .pi/, .agents/)."""
    # Parse --harness BEFORE any output so a bad value is a clean BadParameter
    # (exit 2, message on stderr, empty stdout — no partial payload leaks).
    try:
        harnesses = harness_registry.parse_harness_set(harness)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--harness") from exc

    root = resolve_workspace_root_for_init(workspace, explicit=workspace is not None)
    console.print(f"[bold]Initializing workspace:[/bold] {root}")
    console.print(f"[dim]Harness set:[/dim] {', '.join(harnesses)}")

    svc = container.build_workspace_service(root)
    from dadaia_workspace.core.exceptions import WorkspaceVenvBootstrapError

    try:
        _, installed = svc.init(root, skip_assets=skip_assets, harnesses=harnesses)
    except WorkspaceVenvBootstrapError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from None

    console.print(f"[green]✓[/green] .dadaia/ bootstrapped at {root / '.dadaia'}")

    if skip_assets:
        console.print("[dim]Skipped public asset installation (--skip-assets)[/dim]")
    else:
        if installed:
            console.print(
                f"[green]✓[/green] Installed {len(installed)} asset(s) across runtime projections under {root}"
            )
            for item in installed:
                console.print(f"  {item}")
        else:
            console.print("[dim]No new assets to install (all up to date)[/dim]")
