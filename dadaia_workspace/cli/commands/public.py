"""dadaia public subcommands."""

import json
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.table import Table

import dadaia_workspace
from dadaia_workspace import container
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

#: Display styles by status. Rendering only — the verdict NEVER depends on this map:
#: an unmapped status prints unstyled and still blocks if its status blocks.
_STYLE_BY_STATUS: dict[DoctorStatus, str] = {
    DoctorStatus.OK: "green",
    DoctorStatus.MISSING: "yellow",
    DoctorStatus.DRIFT: "yellow",
    DoctorStatus.ERROR: "red",
    DoctorStatus.LEAK: "red",
    DoctorStatus.EXTRA: "yellow",
    DoctorStatus.NOT_APPLICABLE: "cyan",
    DoctorStatus.UNSUPPORTED: "cyan",
}

app = typer.Typer(help="Manage distributed public agent assets.")
console = Console()
TargetOption = Annotated[
    str,
    typer.Option(
        "--target",
        help="Runtime target: all, agents, claude, codex, pi, or kimi-code",
    ),
]

_ONLY_CHOICES = (
    "agents",
    "skills",
    "rules",
    "schemas",
    "scripts",
    "runtime",
    "templates",
    "data",
    "plugins",
)


@app.command()
def stage() -> None:
    """Stage packaged public assets into .dadaia/agentic/."""
    workspace_root = resolve_workspace_root()
    # Defence-in-depth (rc-4 / T-017-36, bug agent-skill-surface-slop): fail staging on broken
    # agent→skill references so a stage with dangling skills never silently succeeds (doctor
    # also catches these post-hoc; this blocks them at the source).
    from dadaia_workspace.infrastructure.codex_doctor import check_agent_skill_refs

    public_dir = Path(__file__).resolve().parent.parent.parent / "public"
    ref_drift = [r for r in check_agent_skill_refs(public_dir) if r.status is DoctorStatus.DRIFT]
    if ref_drift:
        console.print("[red]✗ staging blocked — broken agent→skill references:[/red]")
        for issue in ref_drift:
            console.print(f"  {issue.render()}", markup=False)
        raise typer.Exit(1)
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
    only: str = typer.Option(
        "",
        "--only",
        help=f"Install only one asset category: {', '.join(_ONLY_CHOICES)}",
    ),
) -> None:
    """Install staged public assets into runtime projections."""
    if repos_only and workspace_only:
        typer.echo("Error: --repos-only and --workspace-only are mutually exclusive.", err=True)
        raise typer.Exit(1)

    only_value: str | None = only if only else None
    if only_value is not None and only_value not in _ONLY_CHOICES:
        typer.echo(
            f"Error: --only '{only_value}' is not valid. Choose from: {', '.join(_ONLY_CHOICES)}",
            err=True,
        )
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
    installed = svc.install(
        workspace_root, target=target, force=force, scope=scope, only=only_value
    )

    if installed:
        console.print(f"[green]✓[/green] {len(installed)} asset(s) processed:")
        for item in installed:
            console.print(f"  {item}", markup=False)
    else:
        console.print("[dim]No assets to install.[/dim]")


@app.command(name="list")
def list_assets(
    format: str = typer.Option("table", "--format", help="Output format: table or json"),
) -> None:
    """List all public assets grouped by category."""
    if format not in ("table", "json"):
        typer.echo("Error: --format must be 'table' or 'json'.", err=True)
        raise typer.Exit(1)

    svc = container.build_public_service()
    assets = svc.list_all()

    if format == "json":
        typer.echo(json.dumps(assets, indent=2))
        return

    table = Table(title="Public Assets")
    table.add_column("Type", style="bold cyan")
    table.add_column("Count", justify="right")
    table.add_column("Names")
    for category, names in assets.items():
        table.add_row(category, str(len(names)), "  ".join(names))
    console.print(table)


@app.command()
def doctor() -> None:
    """Diagnose drift between package source, staging, and runtime projections."""
    workspace_root = resolve_workspace_root()
    report = container.build_public_service().doctor(workspace_root)
    lines: list[DoctorLine] = list(report.lines)
    for line in lines:
        console.print(line.render(), style=_STYLE_BY_STATUS.get(line.status), markup=False)
    # The verdict is the typed report's — fail-closed: EVERY blocking status exits 1,
    # including ones this CLI never special-cased (bug public-doctor-exits-zero-
    # despite-error: [error] used to fall into a decorative else and exit 0).
    if any(line.status.blocking for line in lines):
        raise typer.Exit(1)
