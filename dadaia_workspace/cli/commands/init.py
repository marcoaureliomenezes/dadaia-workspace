"""dadaia init command — one plan, one directory, one harness."""

import sys
from dataclasses import dataclass
from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.cli.commands.context import bind_session, print_next_step
from dadaia_workspace.core import harness_registry, session_store
from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    DadaiaError,
    WorkspaceVenvBootstrapError,
    WorkspaceVenvNewerError,
)
from dadaia_workspace.features.reconcile import reconcile_workspace
from dadaia_workspace.features.spec_context.service import slug_from_url
from dadaia_workspace.features.workspace.onboarding import cli_path

console = Console()
app = typer.Typer()

_LAW_NOTE = "Sessions launch at the workspace root."

#: How ``init`` is invoked before any workspace (and so any ``.dadaia/.venv``) exists —
#: every ``fix:`` line init prints starts here, so each one runs as printed.
_INIT = "uvx dadaia-workspace init"


@dataclass(frozen=True)
class InitPlan:
    """Everything one ``init`` run does — filled by flags, or by prompts on a TTY."""

    directory: str
    harness: str
    repo: str = ""
    associated: tuple[str, ...] = ()


def _interactive() -> bool:
    """Prompts are asked only when a human can answer them (D1)."""
    return sys.stdin.isatty()


def _refuse(message: str, fix: str) -> typer.Exit:
    """Print *message* + its ONE executable ``fix:`` line on stderr and exit 2."""
    typer.secho(message, err=True, fg=typer.colors.RED)
    typer.secho(f"fix: {fix}", err=True, fg=typer.colors.RED)
    return typer.Exit(2)


def _root(directory: str) -> Path:
    """The seam is argv: the directory is a parameter, never resolved from cwd."""
    root = Path(directory).expanduser()
    return (Path.cwd() / root).resolve() if not root.is_absolute() else root.resolve()


def _profile_harness(directory: str) -> str:
    """An existing workspace answers ``--harness`` from its own profile (AC2.1)."""
    root = _root(directory)
    if not (root / ".dadaia").is_dir():
        return ""
    return next(iter(container.build_workspace_service(root).harnesses(root)), "")


def _plan(directory: str, harness: str, repo: str, associated: tuple[str, ...]) -> InitPlan:
    """Fill the plan: flags first; a missing DIR/harness is prompted on a TTY, else refused.

    An incomplete invocation on a TTY is an interview, so it also asks the main-repo URL
    and associated URLs (blank ends each); a complete one never prompts.
    """
    harness = harness or (_profile_harness(directory) if directory else "")
    if directory and harness:
        return InitPlan(directory, harness, repo, associated)
    first = harness_registry.L1_ENTRY_HARNESSES[0]
    if not _interactive():
        raise _refuse(
            "init needs DIR and --harness when no terminal can answer prompts; "
            f"harnesses: {', '.join(harness_registry.L1_ENTRY_HARNESSES)}.",
            f"{_INIT} {directory or '<dir>'} --harness {harness or first}",
        )
    directory = directory or str(Path.cwd() / typer.prompt("Workspace name"))
    harness = harness or typer.prompt(
        f"Harness ({', '.join(harness_registry.L1_ENTRY_HARNESSES)})", default=first
    )
    repo = repo or typer.prompt("Main repo URL (blank = none)", default="", show_default=False)
    urls = list(associated)
    while repo and (
        url := typer.prompt("Associated repo URL (blank = done)", default="", show_default=False)
    ):
        urls.append(url)
    return InitPlan(directory, harness, repo, tuple(urls))


@app.command()
def init(
    directory: str = typer.Argument(
        "", metavar="[DIR]", show_default=False, help="Workspace directory — created if absent."
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
    associated_repo: list[str] = typer.Option(  # noqa: B008 — typer's repeatable option
        [],
        "--associated-repo",
        help="Clone URL of an associated repo of the --repo project (repeatable).",
    ),
    skip_assets: bool = typer.Option(
        False, "--skip-assets", help="Skip installing public agent assets"
    ),
) -> None:
    """Bootstrap a dadaia workspace in DIR for one harness: .dadaia/, the law, and that harness's projection."""
    # Every refusal happens BEFORE any output or filesystem write, so a rejected
    # invocation leaves nothing behind (no partial workspace, no leaked payload).
    plan = _plan(directory, harness, repo, tuple(associated_repo))
    try:
        chosen = harness_registry.parse_harness_name(plan.harness)
    except ValueError as exc:
        raise _refuse(
            str(exc),
            f"{_INIT} {plan.directory} --harness {harness_registry.L1_ENTRY_HARNESSES[0]}",
        ) from None

    root = _root(plan.directory)
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

    svc = container.build_workspace_service(root)
    try:
        before, after, action = svc.venv_change(root)
        _, installed = svc.init(root, skip_assets=skip_assets, harnesses=(chosen,))
    except WorkspaceVenvNewerError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        typer.secho(
            f"fix: uvx dadaia-workspace@{exc.installed} init {root}", err=True, fg=typer.colors.RED
        )
        raise typer.Exit(1) from None
    except WorkspaceVenvBootstrapError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from None

    console.print(f"[green]✓[/green] Workspace {root} ({chosen})", highlight=False, soft_wrap=True)
    if skip_assets:
        # The service's one [warn] item: the workspace has NO hook wiring until
        # `public install` runs. markup=False keeps the literal token out of Rich's tag
        # parser (CWE-116, security review).
        for item in installed:
            console.print(item, markup=False)
    else:
        console.print(f"[green]✓[/green] {len(installed)} asset(s) installed", highlight=False)
    console.print(f"CLI: {cli_path(root)}", markup=False, highlight=False, soft_wrap=True)
    for note in filter(None, (_LAW_NOTE, harness_registry.HARNESS_RECORDS[chosen].init_note)):
        console.print(note, markup=False, soft_wrap=True)

    if action == "upgrade":
        _reconcile_upgrade(root, before, after)
    elif before is not None:
        console.print(f"already at {before}", markup=False, highlight=False)

    print_next_step(root, _create_context(root, plan, chosen) if plan.repo else None)


def _reconcile_upgrade(root: Path, before: str | None, after: str | None) -> None:
    """D3: re-init IS the upgrade — the freshly installed venv is reconciled."""
    result = reconcile_workspace(
        root,
        expected_version=after or "",
        public_service=container.build_public_service(),
        doctor_service=container.build_doctor_service(root),
    )
    if not result.ok:
        typer.secho(f"Error: reconcile after upgrade failed: {result.error}", err=True, fg="red")
        typer.secho(f"fix: {cli_path(root)} reconcile --expect-version {after}", err=True)
        raise typer.Exit(1)
    console.print(f"upgraded {before} -> {after}", markup=False, highlight=False)


def _create_context(root: Path, plan: InitPlan, chosen: str) -> str:
    """``--repo``: ``init`` is a CALLER of ``context create``.

    Re-running the identical command stays a no-op: a context already holding THIS url
    is reused.
    """
    ctx_svc = container.build_spec_context_service(root)
    try:
        try:
            slug = ctx_svc.create(plan.repo, associated_urls=plan.associated).name
        except ContextAlreadyExistsError:
            slug = slug_from_url(plan.repo)
            if ctx_svc.show(slug).repo_url != plan.repo:
                raise
            ctx_svc.alive(slug)
        env_lines = session_store.binding_env_lines(slug, bind_session(root, slug))
    except (DadaiaError, OSError) as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        typer.secho(
            f"fix: {_INIT} {plan.directory} --harness {chosen} --repo <a reachable clone URL>",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(1) from None
    console.print(f"[green]✓[/green] {slug} ALIVE and bound", highlight=False, soft_wrap=True)
    for line in env_lines:
        console.print(line, markup=False, soft_wrap=True, highlight=False)
    return slug
