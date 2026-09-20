"""dadaia init command."""

from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core import harness_registry
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root_for_init

console = Console()
app = typer.Typer()

#: Printed once at the end of every successful init. The first line is the law
#: (sessions launch at the workspace root); the second is a RECOMMENDATION about the
#: operator's own ``~/.claude/settings.json`` — the library prints it and never writes
#: user settings, so a stray repo-level ``CLAUDE.md`` hiding the workspace
#: ``AGENTS.md`` stays the operator's decision to prevent.
_CLOSING_NOTES = (
    "Sessions launch at the workspace root.",
    "Claude Code: set `instructionFiles: claude-md-and-agents-md` in your user settings "
    "(~/.claude/settings.json) so a stray CLAUDE.md in a repo never hides the workspace "
    "AGENTS.md.",
)


@app.command()
def init(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Workspace root path"),
    skip_assets: bool = typer.Option(
        False, "--skip-assets", help="Skip installing public agent assets"
    ),
    harness: str = typer.Option(
        "all",
        "--harness",
        help="Harness set to scaffold: 'all' or a comma-separated subset of claude,codex,kimi-code.",
    ),
) -> None:
    """Bootstrap a dadaia workspace: creates .dadaia/ and projects agent assets for the chosen harness set (default all: .agents/, .claude/, .codex/)."""
    # Parse --harness BEFORE any output so a bad value is a clean BadParameter
    # (exit 2, message on stderr, empty stdout — no partial payload leaks).
    try:
        harnesses = harness_registry.parse_harness_set(harness)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--harness") from exc

    # An explicit --workspace is authoritative (it may not exist yet: init creates it).
    explicit = workspace is not None
    root = workspace.resolve() if workspace is not None else resolve_workspace_root_for_init()

    # Bug ancestor-walk-workspace-root-silent-mistarget (T-043-47/A30.5): the
    # .dadaia/-nesting boundary in resolve_workspace_root_for_init already stops the
    # dangerous case (a throwaway workspace nested under an ancestor's own .dadaia/
    # tree) from silently mistargeting that ancestor. The one remaining shape where a
    # bare invocation still walks to a directory OTHER than cwd is the legitimate
    # sub-repo case (cwd nested under a sub-repo lacking its own sentinel) — still
    # loudly named here, on stderr, so it is never mistaken for "init happened at cwd".
    if not explicit and root != Path.cwd().resolve():
        typer.secho(
            f"Ancestor workspace detected: resolved root differs from cwd "
            f"(cwd={Path.cwd().resolve()}, resolved_root={root}). "
            "Pass --workspace to target a different directory explicitly.",
            err=True,
            fg=typer.colors.YELLOW,
        )

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
        # The service reports the consequence loudly — the workspace has NO hook wiring
        # (no gate, no venv guard) until `dadaia public install` runs. markup=False keeps
        # the literal [warn] token out of Rich's tag parser (CWE-116, security review).
        for item in installed:
            console.print(f"  {item}", markup=False)
    else:
        if installed:
            console.print(
                f"[green]✓[/green] Installed {len(installed)} asset(s) across runtime projections under {root}"
            )
            for item in installed:
                console.print(f"  {item}")
        else:
            console.print("[dim]No new assets to install (all up to date)[/dim]")

    for note in _CLOSING_NOTES:
        console.print(note, markup=False, soft_wrap=True)
