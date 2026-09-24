"""dadaia init command — one line, one directory, one harness."""

from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.cli.commands.context import resolve_own_session_id
from dadaia_workspace.core import harness_registry
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.features.workspace.bootstrap import bootstrap_repo

console = Console()
app = typer.Typer()

#: Printed once at the end of a successful init that got no ``--repo``, around the chosen
#: harness's own ``init_note`` (the registry owns per-harness advice; the library prints
#: it and never writes user settings). The first line is the law (sessions launch at the
#: workspace root); the last names where projects live and the ONE verb that makes the
#: first. With ``--repo`` these are replaced by the binding's export lines.
_LAW_NOTE = "Sessions launch at the workspace root."
_PROJECTS_NOTE = (
    "Projects live under repos/ — make the first with "
    f"`{DADAIA_BIN} context create <name> --main-repo <slug> --url <url>`."
)


#: How ``init`` is invoked before any workspace (and so any ``.dadaia/.venv``) exists —
#: every ``fix:`` line init prints starts here, so each one runs as printed.
_INIT = "uvx dadaia-workspace init"


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
    repo: str = typer.Option(
        "",
        "--repo",
        help="Clone URL of this workspace's first project — cloned, made ALIVE and bound.",
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
            f"{_INIT} {directory} --harness {harness_registry.L1_ENTRY_HARNESSES[0]}",
        )
    try:
        chosen = harness_registry.parse_harness_name(harness)
    except ValueError as exc:
        raise _refuse(
            str(exc),
            f"{_INIT} {directory} --harness {harness_registry.L1_ENTRY_HARNESSES[0]}",
        ) from None

    # The seam is argv: the directory is a parameter, never resolved from cwd.
    root = Path(directory).expanduser()
    root = (Path.cwd() / root).resolve() if not root.is_absolute() else root.resolve()
    sibling_fix = f"{_INIT} {root.with_name(root.name + '-workspace')} --harness {chosen}"
    if root.exists() and not root.is_dir():
        raise _refuse(f"'{root}' is not a directory.", sibling_fix)
    # A directory that already holds `.dadaia/` is THIS workspace (a re-run, idempotent);
    # anything else non-empty is a foreign tree and is never scaffolded over.
    if root.is_dir() and any(root.iterdir()) and not (root / ".dadaia").is_dir():
        raise _refuse(
            f"'{root}' already holds a foreign tree (not a dadaia workspace).", sibling_fix
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

    if not repo:
        notes = (_LAW_NOTE, harness_registry.HARNESS_RECORDS[chosen].init_note, _PROJECTS_NOTE)
        for note in filter(None, notes):
            console.print(note, markup=False, soft_wrap=True)
        return

    # --repo: `init` is a CALLER of the context lifecycle. The clone, the registration
    # and the binding are the implementations `context create|alive|bind` run — reached
    # here by composition, so the two entry points can never disagree.
    session_id = resolve_own_session_id(mint=True)
    if session_id is None:  # pragma: no cover — mint=True always yields one
        raise RuntimeError("session-id resolution returned None despite mint=True")
    ctx_svc = container.build_spec_context_service(root)
    try:
        slug, env_lines = bootstrap_repo(
            root,
            repo,
            session_id=session_id,
            create_context=ctx_svc.create,
            main_repo_url=lambda name: ctx_svc.show(name).repo_url,
            alive_context=ctx_svc.alive,
        )
    except (DadaiaError, OSError) as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        typer.secho(
            f"fix: {_INIT} {directory} --harness {chosen} --repo <a reachable clone URL>",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(1) from None

    console.print(f"[green]✓[/green] {slug} cloned into {root / 'repos' / slug}, ALIVE and bound")
    for line in env_lines:
        console.print(line, markup=False, soft_wrap=True, highlight=False)
