"""dadaia public subcommands."""

import json
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.table import Table

import dadaia_workspace
from dadaia_workspace import container
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.ai_surface.doctor import check_ai_surface_ritual

app = typer.Typer(help="Manage distributed public agent assets.")
console = Console()
TargetOption = Annotated[
    str,
    typer.Option(
        "--target",
        help="Runtime target: all, claude, codex, pi, or agents",
    ),
]

_ONLY_CHOICES = (
    "agents",
    "skills",
    "rules",
    "workflows",
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
    ref_drift = [r for r in check_agent_skill_refs(public_dir) if r.startswith("[drift]")]
    if ref_drift:
        console.print("[red]✗ staging blocked — broken agent→skill references:[/red]")
        for issue in ref_drift:
            console.print(f"  {issue}", markup=False)
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
    reports = container.build_public_service().doctor(workspace_root)
    # AI-surface check (v0.1.24 WS-7): fail if mandatory ordered-lifecycle ritual is
    # reintroduced into a dehydrated surface. Wired at the CLI (not the infrastructure
    # service) because the `infrastructure → features` import is forbidden by the
    # import-linter `features-no-subprocess`/layering contract.
    public_dir = Path(dadaia_workspace.__file__).parent / "public"
    reports.extend(check_ai_surface_ritual(public_dir))
    # Workflow-policy Layer-2 residue check (v0.1.28 T-28-D-02): no claude/opencode leaks
    # into the public docs as a selectable Layer-2 worker harness (LAW 1). Wired at the CLI
    # for the same import-layering reason as the AI-surface check above.
    from dadaia_workspace.features.lifecycle.policy_public_doctor import (
        check_workflow_policy_layer2_residue,
    )

    reports.extend(check_workflow_policy_layer2_residue(public_dir))
    has_issues = False
    for item in reports:
        if item.startswith("[ok]"):
            console.print(item, style="green", markup=False)
        elif item.startswith("[missing]") or item.startswith("[drift]"):
            console.print(item, style="yellow", markup=False)
            has_issues = True
        elif item.startswith("[not-applicable]") or item.startswith("[unsupported]"):
            console.print(item, style="cyan", markup=False)
        else:
            console.print(item, markup=False)
    if has_issues:
        raise typer.Exit(1)
