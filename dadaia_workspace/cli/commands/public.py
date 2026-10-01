"""dadaia public subcommands."""

from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core.models.doctor_report import DoctorStatus
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

app = typer.Typer(help="Manage distributed public agent assets.")
console = Console()


@app.command()
def stage() -> None:
    """Stage packaged public assets into .dadaia/agentic/."""
    workspace_root = resolve_workspace_root()
    # Defence-in-depth (rc-4 / T-017-36, bug agent-skill-surface-slop): fail staging on broken
    # agent→skill references so a stage with dangling skills never silently succeeds (doctor
    # also catches these post-hoc; this blocks them at the source).
    from dadaia_workspace.infrastructure.entity_doctor import check_agent_skill_refs

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


@app.command(
    epilog="Recipe: .dadaia/.venv/bin/dadaia public stage && .dadaia/.venv/bin/dadaia public install && .dadaia/.venv/bin/dadaia public doctor"
)
def install(
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
) -> None:
    """Install staged public assets into runtime projections.

    Projects the shared authored set plus every harness registered in
    `.dadaia/states/harness_profile.json` — the roster of record. A harness enters
    that roster through `.dadaia/.venv/bin/dadaia harness add <name>`, never through a flag here.
    """
    workspace_root = resolve_workspace_root()
    svc = container.build_public_service()
    installed = svc.install(workspace_root, force=force)

    if installed:
        console.print(f"[green]✓[/green] {len(installed)} asset(s) processed:")
        for item in installed:
            console.print(f"  {item}", markup=False)
    else:
        console.print("[dim]No assets to install.[/dim]")

    # Derived help digest rider (backlog cli-help-architecture): regenerate the
    # version-stamped digest at install time — never at hook fire. Fail-soft.
    from dadaia_workspace.cli.help_digest import write_digest

    write_digest(workspace_root)


@app.command()
def doctor() -> None:
    """Diagnose drift between package source, staging, and runtime projections.

    Scoped to the same roster `install` projects: the shared authored set plus the
    harnesses registered in the profile.
    """
    workspace_root = resolve_workspace_root()
    lines, fix = container.build_public_service().verdict(workspace_root)
    for line in lines:
        print(line.render())  # plain: a fix line is never wrapped at the terminal width
    if fix:
        print(f"fix: {fix}")
        raise typer.Exit(1)
