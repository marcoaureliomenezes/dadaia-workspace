"""dadaia public subcommands."""

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.cli.help_digest import write_digest
from dadaia_workspace.core.cli_line import fix_line, spell_fix
from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.core.model_registry import TEMPLATES
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

app = typer.Typer(help="Manage distributed public agent assets.")
console = Console()


@app.command(
    epilog="Recipe:\n\n" + "\n\n".join(fix_line(None, "public", v) for v in ("install", "doctor"))
)
def install(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
    template: str | None = typer.Option(
        None,
        "--template",
        help="Agent-model template to save and apply: " + ", ".join(TEMPLATES) + ".",
    ),
) -> None:
    """Stage the packaged public assets, then install them into runtime projections.

    Projects the shared authored set plus every harness registered in
    `.dadaia/states/harness_profile.json` — the roster of record. A harness enters
    that roster through `harness add <name>`, never through a flag here.
    """
    workspace_root = resolve_workspace_root()
    svc = container.build_public_service()
    try:
        installed = svc.install(workspace_root, force=force, template=template)
    except PublicAssetError as exc:
        console.print(f"✗ {exc}", style="red", markup=False)
        raise typer.Exit(1) from exc

    if installed:
        console.print(f"[green]✓[/green] {len(installed)} asset(s) processed:")
        for item in installed:
            console.print(f"  {item}", markup=False)
    else:
        console.print("[dim]No assets to install.[/dim]")

    # Derived help digest rider: regenerate at install time, never at hook fire. Fail-soft.
    write_digest(workspace_root, ctx.find_root().command)


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
        print(spell_fix(fix))
        raise typer.Exit(1)
