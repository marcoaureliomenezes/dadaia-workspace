"""dadaia init command — one line, one directory, one harness."""

from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.cli.commands.context import bind_session
from dadaia_workspace.core import harness_registry, session_store
from dadaia_workspace.core.exceptions import ContextAlreadyExistsError, DadaiaError
from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.features.spec_context.service import slug_from_url

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
    f"`{DADAIA_BIN} context create --main-repo <url>`."
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
            f"`{DADAIA_BIN} harness add <name>` adds any other later.",
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
    sibling_fix = (
        f"{_INIT} {root.parent / ((root.name or 'dadaia') + '-workspace')} --harness {chosen}"
    )
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

    # --repo: `init` is a CALLER of `context create` (T-048-04 reshapes it). Re-running
    # the identical command stays a no-op: a context already holding THIS url is reused.
    ctx_svc = container.build_spec_context_service(root)
    try:
        try:
            slug = ctx_svc.create(repo).name
        except ContextAlreadyExistsError:
            slug = slug_from_url(repo)
            if ctx_svc.show(slug).repo_url != repo:
                raise
            ctx_svc.alive(slug)
        env_lines = session_store.binding_env_lines(slug, bind_session(root, slug))
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
