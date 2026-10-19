"""dadaia init command — one plan, one directory, one or more harnesses."""

import sys
from dataclasses import dataclass, replace
from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.cli._fail import fail
from dadaia_workspace.cli.commands.context import create_fix, print_next_step
from dadaia_workspace.core import harness_registry
from dadaia_workspace.core.cli_line import fix_line, shell_line, spell_fix
from dadaia_workspace.core.exceptions import (
    AssociatedRepoConflictError,
    ContextAlreadyExistsError,
    DadaiaError,
    GitSyncError,
    InvalidContextNameError,
    RepoUrlMissingError,
    WorkspaceVenvBootstrapError,
)
from dadaia_workspace.core.model_registry import TEMPLATES
from dadaia_workspace.core.platform import act, workspace_cli_path
from dadaia_workspace.features.export.service import Artifact, ExportService
from dadaia_workspace.features.spec_context.service import slug_from_url

console = Console()
app = typer.Typer()

_LAW_NOTE = "Sessions launch at the workspace root."

#: How ``init`` is invoked before any workspace (and so any ``.dadaia/.venv``) exists —
#: every ``fix:`` line init prints starts here, so each one runs as printed.
_INIT = ("uvx", "dadaia-workspace", "init")
reconcile_workspace = container.reconcile_workspace


@dataclass(frozen=True)
class InitPlan:
    """Everything one ``init`` run does — filled by flags, or by prompts on a TTY."""

    directory: str
    harness: str
    repo: str = ""
    associated: tuple[str, ...] = ()
    from_: str = ""

    def command(self, directory: object = None, runner: tuple[str, ...] = _INIT) -> str:
        """The ``init`` invocation that runs this plan — every flag it carries, so a
        ``fix:`` line built from it never drops a level (*directory* overrides DIR)."""
        target = str(self.directory if directory is None else directory)
        flags = [("--harness", self.harness)] if self.harness else []
        flags += [("--from", self.from_)] if self.from_ else []
        flags += [("--repo", self.repo)] if self.repo else []
        flags += [("--associated-repo", url) for url in self.associated]
        return shell_line(*runner, *filter(None, [target]), *sum(flags, ()))


def _interactive() -> bool:
    """Prompts are asked only when a human can answer them."""
    return sys.stdin.isatty()


def _root(directory: str) -> Path:
    """The seam is argv: the directory is a parameter, never resolved from cwd."""
    root = Path(directory).expanduser()
    return (Path.cwd() / root).resolve() if not root.is_absolute() else root.resolve()


def _profile_harness(directory: str) -> str:
    """An existing workspace answers ``--harness`` from its own profile."""
    root = _root(directory)
    if not (root / ".dadaia").is_dir():
        return ""
    return next(iter(container.build_workspace_service(root).harnesses(root)), "")


def _plan(
    directory: str, harness: str, repo: str, associated: tuple[str, ...], from_: str
) -> InitPlan:
    """Fill the plan: flags first; a missing DIR/harness is prompted on a TTY, else refused.
    With ``--from`` the harnesses come from the artifact, so none is asked.

    An incomplete invocation on a TTY is an interview, so it also asks the main-repo URL
    and associated URLs (blank ends each); a complete one never prompts.
    """
    harness = harness or (_profile_harness(directory) if directory and not from_ else "")
    if directory and (harness or from_):
        return InitPlan(directory, harness, repo, associated, from_)
    first = harness_registry.L1_ENTRY_HARNESSES[0]
    if not _interactive():
        plan = InitPlan(directory or "", harness or first, repo, associated, from_)
        fail(
            "init needs DIR and --harness when no terminal can answer prompts; "
            f"harnesses: {', '.join(harness_registry.L1_ENTRY_HARNESSES)}.",
            plan.command()
            if directory
            else act(
                "agent",
                f"run `{plan.command()}` with the new workspace's directory as its first argument",
            ),
        )
    directory = directory or str(Path.cwd() / typer.prompt("Workspace name"))
    if not from_:
        harness = harness or typer.prompt(
            f"Harness ({', '.join(harness_registry.L1_ENTRY_HARNESSES)})", default=first
        )
        repo = repo or typer.prompt("Main repo URL (blank = none)", default="", show_default=False)
    urls = list(associated)
    while repo and (
        url := typer.prompt("Associated repo URL (blank = done)", default="", show_default=False)
    ):
        urls.append(url)
    return InitPlan(directory, harness, repo, tuple(urls), from_)


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
        help="Clone URL of this workspace's first project — cloned and made ALIVE.",
    ),
    associated_repo: list[str] = typer.Option(  # noqa: B008 — typer's repeatable option
        [],
        "--associated-repo",
        help="Clone URL of an associated repo of the --repo project (repeatable).",
    ),
    from_: str = typer.Option(
        "",
        "--from",
        help="An artifact written by `export` (JSON or tar.gz): install its harnesses and "
        "register its contexts DEAD here. Excludes --repo.",
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        help=f"Agent model template to save and project: {', '.join(TEMPLATES)}.",
    ),
    skip_assets: bool = typer.Option(
        False, "--skip-assets", help="Skip installing public agent assets"
    ),
) -> None:
    """Bootstrap a dadaia workspace in DIR for one harness: .dadaia/, the law, and that harness's projection."""
    # Every refusal happens BEFORE any output or filesystem write, so a rejected
    # invocation leaves nothing behind (no partial workspace, no leaked payload).
    if from_ and repo:
        fail(
            "--from restores an artifact's contexts; it cannot be combined with --repo.",
            InitPlan(directory, harness, from_=from_).command(),
        )
    plan = _plan(directory, harness, repo, tuple(associated_repo), from_)
    try:
        if plan.harness:
            plan = replace(plan, harness=harness_registry.parse_harness_name(plan.harness))
    except ValueError as exc:  # a bad option value is Click's usage error (exit 2)
        raise typer.BadParameter(str(exc), param_hint="'--harness'") from None
    artifact = _read(plan.from_) if plan.from_ else None
    chosen = (plan.harness,) if plan.harness else artifact.harnesses if artifact else ()
    if not chosen:
        fail(
            "the artifact names no harness.",
            replace(plan, harness=harness_registry.L1_ENTRY_HARNESSES[0]).command(),
        )

    root = _root(plan.directory)
    sibling_fix = plan.command(root.parent / ((root.name or "dadaia") + "-workspace"))
    if root.exists() and not root.is_dir():
        fail(f"'{root}' is not a directory.", sibling_fix)
    # A directory that already holds `.dadaia/` is THIS workspace (a re-run, idempotent);
    # anything else non-empty is a foreign tree and is never scaffolded over.
    if root.is_dir() and any(root.iterdir()) and not (root / ".dadaia").is_dir():
        fail(f"'{root}' already holds a foreign tree (not a dadaia workspace).", sibling_fix)
    root.mkdir(parents=True, exist_ok=True)

    svc = container.build_workspace_service(root)
    try:
        before, after, action = svc.venv_change(root)
        installed = svc.init(root, skip_assets=skip_assets, harnesses=chosen, template=template)
    except WorkspaceVenvBootstrapError as exc:
        cli = workspace_cli_path(root)  # the venv's own init only where the venv exists
        runner = (str(cli), "init") if cli.is_file() else _INIT
        fail(exc, plan.command(root, runner))

    console.print(
        f"[green]✓[/green] Workspace {root} ({', '.join(chosen)})", highlight=False, soft_wrap=True
    )
    if skip_assets:
        # The service's one [warn] item: the workspace has NO hook wiring until
        # `public install` runs. markup=False keeps the literal token out of Rich's tag
        # parser (CWE-116, security review).
        for item in installed:
            console.print(item, markup=False)
    else:
        console.print(f"[green]✓[/green] {len(installed)} asset(s) installed", highlight=False)
    console.print(f"CLI: {workspace_cli_path(root)}", markup=False, highlight=False, soft_wrap=True)
    console.print(_LAW_NOTE, markup=False, soft_wrap=True)

    if action in ("upgrade", "repair"):
        _reconcile_upgrade(root, action, before, after)
    elif before is not None:
        console.print(f"already at {before}", markup=False, highlight=False)

    if artifact:
        _restore(root, artifact, Path(plan.from_).expanduser())
    else:
        print_next_step(root, _create_context(root, plan) if plan.repo else None)


def _read(source: str) -> Artifact:
    """The artifact at *source*, read before any write; a refusal ends the run."""
    try:
        return ExportService.read(Path(source).expanduser())
    except DadaiaError as exc:
        fail(exc)


def _restore(root: Path, artifact: Artifact, source: Path) -> None:
    """``--from``: register each context DEAD through ``register``, list what cannot be fetched,
    place a hard artifact's bundles, and print the ``context alive`` line of each ALIVE one."""
    contexts = container.build_spec_context_service(root)
    alive, unborn = [], []
    for ctx in artifact.contexts:
        try:
            contexts.register(ctx)
        except RepoUrlMissingError:
            unborn.append(ctx)
            _say(f"not replicated: no remote   {ctx.name}")
        except (
            ContextAlreadyExistsError,
            InvalidContextNameError,
            AssociatedRepoConflictError,
        ) as exc:
            _say(f"skipped ({exc})   {ctx.name}")
        else:
            _say(f"registered (dead)   {ctx.name}")
            for repo in (r for r in ctx.all_repos() if r.url and not _reachable(root, r.url)):
                _say(f"unreachable   {repo.url}   ({ctx.name})")
            alive += [ctx.name] * (ctx.name in artifact.alive)
    if unborn:
        empty = [f"repos/{r.slug}" for c in unborn for r in c.all_repos() if not r.url]
        _say(spell_fix(act("agent", f"add a remote to {', '.join(empty)}, then export again")))
    try:
        container.build_export_service(root).restore(source)
    except DadaiaError as exc:
        fail(exc)
    if alive:
        _say("Restore each ALIVE context with:")
        for name in alive:
            _say(f"  {fix_line(root, 'context', 'alive', name)}")


def _say(text: str) -> None:
    console.print(text, markup=False, highlight=False, soft_wrap=True)


def _reachable(root: Path, url: str) -> bool:
    try:
        container.build_git_client().git(
            root, "ls-remote", "--heads", url, env={"GIT_TERMINAL_PROMPT": "0"}
        )
    except GitSyncError:
        return False
    return True


def _reconcile_upgrade(root: Path, action: str, before: str | None, after: str | None) -> None:
    """Re-init is the upgrade: the freshly installed venv is reconciled."""
    result = reconcile_workspace(
        root,
        expected_version=after or "",
    )
    if not result.ok:
        fail(
            f"reconcile after upgrade failed: {result.error}",
            fix_line(root, "reconcile", "--expect-version", after or ""),
        )
    container.build_spec_context_service(root).refresh_hooks()
    line = f"repaired -> {after}" if action == "repair" else f"upgraded {before} -> {after}"
    console.print(line, markup=False, highlight=False)


def _create_context(root: Path, plan: InitPlan) -> str:
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
    except (DadaiaError, OSError) as exc:
        fail(exc, create_fix(root, exc, None, [plan.repo, *plan.associated]))
    console.print(f"[green]✓[/green] {slug} ALIVE", highlight=False, soft_wrap=True)
    return slug
