"""dadaia init command — one line, one directory, one harness (0.4.7 FR1)."""

from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core import harness_registry

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


def _refuse(message: str, fix: str) -> typer.Exit:
    """Print *message* + its ONE executable ``fix:`` line on stderr and exit 2."""
    typer.secho(message, err=True, fg=typer.colors.RED)
    typer.secho(f"fix: {fix}", err=True, fg=typer.colors.RED)
    return typer.Exit(2)


@app.command()
def init(
    directory: str = typer.Argument(
        ..., metavar="DIR", help="Workspace directory — created if absent."
    ),
    harness: str = typer.Option(
        "",
        "--harness",
        help=f"The one agent runtime to scaffold: {', '.join(harness_registry.L1_ENTRY_HARNESSES)}.",
    ),
    skip_assets: bool = typer.Option(
        False, "--skip-assets", help="Skip installing public agent assets"
    ),
) -> None:
    """Bootstrap a dadaia workspace in DIR for one harness: .dadaia/, the law, and that harness's projection."""
    # Every refusal happens BEFORE any output or filesystem write, so a rejected
    # invocation leaves nothing behind (no partial workspace, no leaked payload).
    if not harness:
        raise _refuse(
            "--harness is required: a workspace is born with exactly one agent runtime "
            f"({', '.join(harness_registry.L1_ENTRY_HARNESSES)}); "
            "`dadaia harness add <name>` adds any other later.",
            f"dadaia init {directory} --harness {harness_registry.L1_ENTRY_HARNESSES[0]}",
        )
    try:
        chosen = harness_registry.parse_harness_name(harness)
    except ValueError as exc:
        raise _refuse(
            str(exc),
            f"dadaia init {directory} --harness {harness_registry.L1_ENTRY_HARNESSES[0]}",
        ) from None

    # The seam is argv: the directory is a parameter, never resolved from cwd.
    root = Path(directory).expanduser()
    root = (Path.cwd() / root).resolve() if not root.is_absolute() else root.resolve()
    if root.exists() and not root.is_dir():
        raise _refuse(
            f"'{root}' is not a directory.", f"dadaia init {directory}-workspace --harness {chosen}"
        )
    # A directory that already holds `.dadaia/` is THIS workspace (a re-run, idempotent);
    # anything else non-empty is a foreign tree and is never scaffolded over.
    if root.is_dir() and any(root.iterdir()) and not (root / ".dadaia").is_dir():
        raise _refuse(
            f"'{root}' already holds a foreign tree (not a dadaia workspace).",
            f"dadaia init {directory}-workspace --harness {chosen}",
        )
    root.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Initializing workspace:[/bold] {root}")
    console.print(f"[dim]Harness:[/dim] {chosen}")

    svc = container.build_workspace_service(root)
    from dadaia_workspace.core.exceptions import WorkspaceVenvBootstrapError

    try:
        _, installed = svc.init(root, skip_assets=skip_assets, harnesses=(chosen,))
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
