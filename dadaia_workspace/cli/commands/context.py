"""dadaia context subcommands."""

import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.cli._specs_resolution import (
    HARNESS_SESSION_ID_ENV_VARS,
    alive_context_trees,
    sanitize_session_id,
)
from dadaia_workspace.cli._specs_resolution import (
    resolve_context_for_cli as _resolve_context_for_cli,
)
from dadaia_workspace.cli.redact import ContextRedactor
from dadaia_workspace.core import session_store
from dadaia_workspace.core.exceptions import (
    AssociatedRepoConflictError,
    AssociatedRepoNotFoundError,
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    DadaiaError,
    GitSyncError,
    InvalidContextNameError,
    RepoUrlMissingError,
    SchemaVersionError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.core.models.spec_context import (
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.spec_context.service import (
    DeadReviewRequiredError,
    DeadSecretFoundError,
    SpecContextService,
)
from dadaia_workspace.features.workspace import onboarding

app = typer.Typer(help="Manage Spec Context Projects.")
# FR17 (v0.4.4, T-044-28): associated-repo registry verbs, nested under `context repo`
# — same `app.add_typer` pattern as `specs release`/`specs segment`.
repo_app = typer.Typer(help="Manage a context's associated repos (main repo excluded).")
app.add_typer(repo_app, name="repo")
console = Console()
err_console = Console(stderr=True)


def _ctx_service() -> SpecContextService:
    try:
        return container.build_spec_context_service(resolve_workspace_root())
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(1) from None
    except SchemaVersionError as exc:
        # Use plain stderr so CliRunner captures it in result.output (mix_stderr=True default)
        print(str(exc), file=sys.stderr)
        raise typer.Exit(1) from None


def _ctx_to_dict(svc: SpecContextService, ctx: SpecContextProject) -> dict:  # type: ignore[type-arg]
    # v0.1.72 FR4 (bug `context-current-branch-stale-for-alive-repo`) / v0.4.4 FR18
    # (bug `context-list-current-branch-stale-for-alive-repo`, A18.3): `current_branch`
    # is resolved through SpecContextService.repos_live_status — the ONE
    # branch-resolution implementation `show` AND `list` both call, so the two verbs
    # can no longer disagree on this field the way they used to (list previously read
    # the stored snapshot directly while show queried git live). The stored snapshot
    # remains available under the distinct name `stored_branch` (A18.1).
    statuses = svc.repos_live_status(ctx)
    main_status, associated_statuses = statuses[0], statuses[1:]
    return {
        "name": ctx.name,
        "state": ctx.state.value,
        "main_repo": ctx.repo_slug,
        "repo_url": ctx.repo_url,
        "created_at": ctx.created_at,
        "alive_since": ctx.alive_since,
        "dead_since": ctx.dead_since,
        "current_branch": main_status.current_branch or ctx.current_branch,
        "stored_branch": ctx.current_branch,
        "associated_repos": [
            {
                "slug": status.slug,
                "url": status.url,
                "on_disk": status.on_disk,
                "current_branch": status.current_branch,
            }
            for status in associated_statuses
        ],
    }


def _resolve_caller_context_name() -> str | None:
    """Best-effort resolution of the caller's own context name (SPEC v0.9.0 FR8a:
    "other than the caller's resolved context"). Never raises — an unresolved caller
    means nothing is excluded, so `--redact` masks every context/slug it encounters."""
    try:
        return _resolve_context_for_cli(None)
    except ValueError:
        return None


def _build_context_redactor(contexts: list[SpecContextProject]) -> ContextRedactor:
    """Candidates = every known context's name and every repo slug (main + FR15
    associated repos, via `all_repos()`); excludes the caller's own resolved context
    name and its own full repo set (render boundary ONLY — `contexts` is data the
    service already returned with true names). FR18 widened this from "main slug
    only" — an associated repo can be exactly as private as a main one, so it must
    redact the same way."""
    caller_name = _resolve_caller_context_name()
    caller_ctx = next((ctx for ctx in contexts if ctx.name == caller_name), None)
    caller_repo_slugs = (
        {r.slug for r in caller_ctx.all_repos()} if caller_ctx is not None else set()
    )
    candidates: list[str] = []
    for ctx in contexts:
        candidates.append(ctx.name)
        for repo in ctx.all_repos():
            candidates.append(repo.slug)
    return ContextRedactor(candidates, exclude=(caller_name, *caller_repo_slugs))


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _sessions_dir(workspace_root: Path) -> Path:
    # Session-store path via the single owner (T-011-05 / FR-W1-05, ADR-12) — the bind CLI
    # no longer constructs the ``.dadaia/sessions`` path itself.
    return session_store.sessions_dir(workspace_root)


def _live_session(workspace_root: Path, session_id: str) -> dict[str, Any] | None:
    """This caller's own session record, or ``None`` when absent/stale — the single
    owner's predicate (:func:`core.session_store.live_session`, F002)."""
    record = session_store.live_session(workspace_root, session_id)
    return None if record is None else dict(record)


def _harness_session_id() -> str | None:
    """Harness-native session id from the environment ONLY (no payload — this is a CLI
    entrypoint, not a hook). Scans the single shared env-var list
    (:data:`~dadaia_workspace.core.invocation.HARNESS_SESSION_ID_ENV_VARS`) so the
    harness id never drifts from what the gate/hooks read (release K1)."""
    for name in HARNESS_SESSION_ID_ENV_VARS:
        sanitized = sanitize_session_id(os.environ.get(name))
        if sanitized:
            return sanitized
    return None


def resolve_own_session_id(*, explicit: str | None = None, mint: bool = False) -> str | None:
    """Resolve THIS caller's own session identity (T-50-05: the single helper every verb
    below used to duplicate as its own copy-pasted micro-ladder).

    Order: *explicit* (a verb's own CLI override, e.g. ``release --session``) -> the
    eval-flow ``DADAIA_SESSION_ID`` (sanitized, CWE-22 — every site now gets the same
    defence ``bind`` already had) -> the harness-native session id
    (:func:`_harness_session_id`) -> when *mint* is set, a freshly minted ``sess_*`` id
    (``bind``'s own fallback when a record must be created but neither channel carries
    an identity yet — a WRITE-side concern this CLI command owns for itself, never part
    of the read-side session-id rule, release K1). Session IDENTITY only — never a
    context-resolution rung.
    """
    if explicit:
        return explicit
    env_sid = sanitize_session_id(os.environ.get("DADAIA_SESSION_ID"))
    if env_sid:
        return env_sid
    harness_id = _harness_session_id()
    if harness_id:
        return harness_id
    if mint:
        return f"sess_{uuid.uuid4().hex[:8]}"
    return None


def bind_session(workspace_root: Path, name: str) -> str:
    """Record THIS session's binding to *name*; return the session id — the one
    binding author ``bind``, ``create`` and ``init --repo`` share."""
    session_id = resolve_own_session_id(mint=True)
    if session_id is None:  # pragma: no cover — mint=True always yields one
        raise RuntimeError("session-id resolution returned None despite mint=True")
    session_store.write_session(
        workspace_root,
        session_id,
        session_store.new_binding_record(
            session_id=session_id,
            context=name,
            runtime=os.environ.get("DADAIA_RUNTIME", "unknown"),
            pid=os.getpid(),
            now=_now_iso(),
        ),
    )
    return session_id


def print_next_step(workspace_root: Path, focus: str | None = None) -> None:
    """The derived onboarding next step (FR6 AC6.2) — the text ``doctor`` also reports."""
    step = onboarding.next_step(workspace_root, alive_context_trees(workspace_root), focus)
    if step is not None:
        console.print(step.text(), markup=False, highlight=False, soft_wrap=True)


def _create_fix(error: Exception, name: str | None, urls: list[str]) -> str:
    """The invocation, every ``--associated-repo`` kept (AC3.5), with what failed made a
    placeholder — never the failing command repeated; an owned slug names its owner."""
    if isinstance(error, AssociatedRepoConflictError):
        return f"{DADAIA_BIN} context list"
    if isinstance(error, ContextAlreadyExistsError):
        name = "<another-name>"
    urls = [u if repr(u) not in str(error) else "<clone-url>" for u in urls]
    flags = [f"--associated-repo {u}" for u in urls[1:]]
    return " ".join(
        [f"{DADAIA_BIN} context create", *([name] if name else []), "--main-repo", urls[0], *flags]
    )


@app.command()
def create(
    name: str | None = typer.Argument(None, help="Context name (default: the main repo's slug)"),
    main_repo: str = typer.Option(
        ..., "--main-repo", help="Clone URL of the main repo (the repo where specs/ lives)"
    ),
    associated: list[str] = typer.Option(
        [], "--associated-repo", help="Clone URL of an associated repo; repeatable"
    ),
) -> None:
    """Clone (or adopt) every repo, install the pre-push hook, make the context ALIVE and
    bind this session — one step; on failure nothing is left behind."""
    ws = resolve_workspace_root()
    try:
        ctx = container.build_spec_context_service(ws).create(
            main_repo, name=name, associated_urls=tuple(associated)
        )
    except (DadaiaError, OSError) as e:
        err_console.print(f"Error: {e}", markup=False, soft_wrap=True)
        err_console.print(
            f"fix: {_create_fix(e, name, [main_repo, *associated])}", markup=False, soft_wrap=True
        )
        raise typer.Exit(1) from None
    session_id = bind_session(ws, ctx.name)
    suffix = f", {len(ctx.associated_repos)} associated repo(s)" if ctx.associated_repos else ""
    console.print(
        f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' created, ALIVE and bound "
        f"(main repo: repos/{ctx.repo_slug}{suffix})",
        highlight=False,
        soft_wrap=True,
    )
    for line in session_store.binding_env_lines(ctx.name, session_id):
        console.print(line, markup=False, soft_wrap=True, highlight=False)
    print_next_step(ws, ctx.name)


@app.command(name="list")
def list_all(
    json_output: bool = typer.Option(False, "--json", help="Output stable JSON contract"),
    redact: bool = typer.Option(
        False,
        "--redact",
        help=(
            "Mask every context name and repo slug other than this caller's resolved "
            "context (SPEC v0.9.0 FR8a). Default output is unchanged."
        ),
    ),
) -> None:
    """List all Spec Context Projects."""
    svc = _ctx_service()
    try:
        contexts = svc.list_all()
    except SchemaVersionError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(1) from None

    redactor = _build_context_redactor(contexts) if redact else None

    if json_output:
        payload = []
        for ctx in contexts:
            # FR18/A18.1-A18.3: the SAME payload builder `show --json` uses — one
            # key set, so the two verbs cannot drift apart again.
            payload.append(_ctx_to_dict(svc, ctx))
        if redactor is not None:
            payload = [redactor.json_value(row) for row in payload]
        print(json.dumps(payload, sort_keys=True))
        return
    if not contexts:
        console.print(
            f"No contexts found. Create one: {DADAIA_BIN} context create <name> "
            "--main-repo <clone-url>",
            markup=False,
            soft_wrap=True,
        )
        return

    table = Table(title="Spec Context Projects")
    table.add_column("Name", style="bold")
    table.add_column("State")
    table.add_column("Main repo")
    table.add_column("Associated repos")

    state_style = {
        ContextState.ALIVE: "[green]alive[/green]",
        ContextState.DEAD: "[dim]dead[/dim]",
    }

    for ctx in contexts:
        name = redactor.text(ctx.name) if redactor is not None else ctx.name
        repo_slug = redactor.text(ctx.repo_slug) if redactor is not None else ctx.repo_slug
        table.add_row(
            name,
            state_style.get(ctx.state, ctx.state.value),
            repo_slug,
            str(len(ctx.associated_repos)),
        )
    console.print(table)


def _resolve_default_context(svc: Any, workspace_root: Path) -> Any | None:
    """Resolve no-arg ``context show`` through the caller-owned resolution seam."""
    from dadaia_workspace.cli._specs_resolution import resolve_context_for_cli

    _ = workspace_root  # kept for signature stability; resolution no longer needs it directly.
    try:
        resolved_name = resolve_context_for_cli(None)
    except ValueError:
        # ``show`` is a query verb: "nothing is selected" is a valid ANSWER here, not an
        # error — the resolver's ValueError is for verbs that REQUIRE a context (bug
        # context-show-json-traceback-unbound, consumer validation 2026-07-15).
        return None
    if not resolved_name:
        return None
    try:
        return svc.show(resolved_name)
    except ContextNotFoundError:
        return None


@app.command()
def show(
    name: str | None = typer.Argument(None, help="Context name"),
    json_output: bool = typer.Option(False, "--json", help="Output stable JSON contract"),
    redact: bool = typer.Option(
        False,
        "--redact",
        help=(
            "Mask every context name and repo slug other than this caller's resolved "
            "context (SPEC v0.9.0 FR8a). Default output is unchanged."
        ),
    ),
) -> None:
    """Show details of a context."""
    svc = _ctx_service()
    if name is None:
        # No name: use only explicit/caller-owned/cwd resolution.
        ctx = _resolve_default_context(svc, resolve_workspace_root())
    else:
        try:
            ctx = svc.show(name)
        except ContextNotFoundError as e:
            err_console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    redactor: ContextRedactor | None = None
    if redact:
        try:
            all_contexts = svc.list_all()
        except SchemaVersionError:
            all_contexts = [ctx] if ctx is not None else []
        redactor = _build_context_redactor(all_contexts)

    if json_output:
        if ctx is None:
            print(json.dumps({"context": None}, indent=2))
        else:
            data = _ctx_to_dict(svc, ctx)
            # Show only this caller's session. A context-wide "last binder" fallback would
            # expose foreign state as the caller's own and can never be authoritative.
            workspace_root = resolve_workspace_root()
            session_id = resolve_own_session_id()
            session_obj = _live_session(workspace_root, session_id) if session_id else None
            data["session"] = session_obj
            if redactor is not None:
                data = redactor.json_value(data)
            print(json.dumps(data, indent=2))
        return

    if ctx is None:
        msg = f"Context '{name}' not found." if name else "No active context."
        console.print(f"[dim]{msg}[/dim]")
        return

    display_name = redactor.text(ctx.name) if redactor is not None else ctx.name
    display_repo = redactor.text(ctx.repo_slug) if redactor is not None else ctx.repo_slug
    repo_url_text = ctx.repo_url or "—"
    if redactor is not None and ctx.repo_url:
        repo_url_text = redactor.text(ctx.repo_url)

    # FR18: table and --json share the SAME branch-resolution seam
    # (SpecContextService.repos_live_status, A18.3) — main repo's live branch here
    # is the identical value `list`'s --json output reports for this context.
    statuses = svc.repos_live_status(ctx)
    main_status, associated_statuses = statuses[0], statuses[1:]
    branch_text = main_status.current_branch or ctx.current_branch or "—"

    console.print(f"[bold]Name:[/bold]       {display_name}")
    console.print(f"[bold]State:[/bold]      {ctx.state.value}")
    console.print(f"[bold]Main repo:[/bold]  {display_repo}")
    console.print(f"[bold]Repo URL:[/bold]   {repo_url_text}")
    console.print(f"[bold]Branch:[/bold]     {branch_text}")
    console.print(f"[bold]Created:[/bold]    {ctx.created_at}")
    console.print(f"[bold]Alive since:[/bold]  {ctx.alive_since or '—'}")
    console.print(f"[bold]Dead since:[/bold]   {ctx.dead_since or '—'}")

    if associated_statuses:
        assoc_table = Table(title="Associated repos")
        assoc_table.add_column("Slug", style="bold")
        assoc_table.add_column("URL")
        assoc_table.add_column("On disk")
        assoc_table.add_column("Branch")
        for status in associated_statuses:
            assoc_table.add_row(
                status.slug,
                status.url or "—",
                "yes" if status.on_disk else "no",
                status.current_branch or "—",
            )
        console.print(assoc_table)


@app.command()
def alive(name: str = typer.Argument(..., help="Context name to make ALIVE")) -> None:
    """Transition a context to ALIVE; clone repo if absent. Idempotent if already ALIVE."""
    try:
        ws = resolve_workspace_root()
        ctx = container.build_spec_context_service(ws).alive(name)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' is now ALIVE")
    except SchemaVersionError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(1) from None
    except RepoUrlMissingError as e:
        err_console.print(f"Error: {e}", markup=False, soft_wrap=True)
        raise typer.Exit(1) from None
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def baseline(
    name: str = typer.Argument(..., help="ALIVE context with an unborn Git repository"),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Explicitly consent to creating the initial commit."
    ),
    push: bool = typer.Option(False, "--push", help="Also push and configure upstream."),
    message: str = typer.Option(
        "chore: establish dadaia scaffold baseline",
        "--message",
        help="Initial commit message.",
    ),
) -> None:
    """Create the explicit initial scaffold commit for an unborn repository."""
    if not yes:
        err_console.print(
            "[red]Error:[/red] Baseline creates a Git commit. Re-run with --yes after "
            "reviewing the scaffold; add --push only if remote publication is intended."
        )
        raise typer.Exit(1)
    try:
        ctx = _ctx_service().baseline(name, message=message, push=push)
        suffix = " and pushed" if push else ""
        console.print(
            f"[green]✓[/green] Initial baseline committed{suffix} for '[bold]{ctx.name}[/bold]'"
        )
    except (ContextNotFoundError, ContextStateError, DeadSecretFoundError, GitSyncError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None


@app.command()
def dead(
    name: str = typer.Argument(..., help="Context name to make DEAD"),
    commit: bool = typer.Option(
        False,
        "--commit",
        help=(
            "Explicit consent to commit+push untracked files. Without it, dead() "
            "refuses if untracked files are present and pushes nothing. With it, a "
            "secret scan runs over the files before push and blocks on any finding."
        ),
    ),
) -> None:
    """Transition a context to DEAD; git sync + remove repo from disk."""
    try:
        ctx = _ctx_service().dead(name, commit=commit)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' is now DEAD")
    except DeadReviewRequiredError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except DeadSecretFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except RepoUrlMissingError as e:
        err_console.print(f"Error: {e}", markup=False, soft_wrap=True)
        raise typer.Exit(1) from None
    except GitSyncError as e:
        # Residual git failures (network, refs) surface as a clean error, not a
        # traceback (validation-029 F-06/F-22 no-traceback law).
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command(
    epilog="Examples: dadaia context bind my-ctx | eval $(dadaia context bind my-ctx --print-env)"
)
def bind(
    name: str = typer.Argument(..., help="Context name to bind to"),
    print_env: bool = typer.Option(
        False,
        "--print-env",
        help=(
            "Emit eval-compatible 'export DADAIA_CONTEXT/DADAIA_SESSION_ID' lines for "
            "`eval $(dadaia context bind ... --print-env)`. Default off — the binding is "
            "persisted in the session record either way."
        ),
    ),
) -> None:
    """Bind this shell session to a context.

    Run: dadaia context bind <name> [--print-env]

    The bind sets this session's write scope to the context's main repo plus its
    associated repos.
    """
    workspace_root = resolve_workspace_root()
    sessions_dir = _sessions_dir(workspace_root)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    svc = _ctx_service()
    try:
        svc.show(name)
    except ContextNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    # Stable session identity (bug bind-session-id-divergence, 2026-07-15): the SAME
    # resolution order the gate/hooks use, so rebinds UPDATE one record.
    session_id = bind_session(workspace_root, name)

    # T-50-05 (SPEC v0.5.0 FR1): without this loud warning, a caller with no
    # harness-native id and no DADAIA_CONTEXT gets a silent no-op. stderr only, so it
    # never corrupts `eval $(dadaia context bind ... --print-env)`.
    if (
        not _harness_session_id()
        and not os.environ.get("DADAIA_CONTEXT")
        and not os.environ.get("DADAIA_SESSION_ID")
        and not print_env
    ):
        err_console.print(
            f"[yellow]![/yellow] No harness-native session id and DADAIA_CONTEXT is "
            f"unset in this shell — this binding is reachable only if DADAIA_CONTEXT="
            f"{name} is exported here (e.g. `eval $(dadaia context bind {name} "
            "--print-env)`)."
        )

    if print_env:
        for line in session_store.binding_env_lines(name, session_id):
            print(line)
        return

    console.print(f"[green]✓[/green] Bound to '[bold]{name}[/bold]' (session id: {session_id})")


# ------------------------------------------------------------------ context repo (FR17)


@repo_app.command(name="add")
def repo_add(
    ctx_name: str = typer.Argument(..., help="Context name"),
    slug: str = typer.Argument(
        ..., help="Associated repo to register — the directory name under repos/"
    ),
    url: str = typer.Option(
        "", "--url", help="Repo clone URL — required unless repos/<slug> is already a checkout"
    ),
) -> None:
    """Register an associated repo on a context.

    Run: dadaia context repo add <ctx> <slug> [--url <url>]

    Idempotent: re-adding the same slug with the same URL is a no-op success. The
    same slug with a DIFFERENT URL is refused — this verb is the one place an
    associated repo's URL is set, so the recovery path is 'context repo remove'
    then 'context repo add' again, never a second divergent URL-update verb.
    Adding the context's own main repo slug is refused (it is already covered).
    """
    try:
        ctx, was_added = _ctx_service().add_repo(ctx_name, slug, url)
    except (ContextNotFoundError, InvalidContextNameError, AssociatedRepoConflictError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except RepoUrlMissingError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        err_console.print(
            f"fix: {DADAIA_BIN} context repo add {ctx_name} {slug} --url <clone-url>",
            markup=False,
            soft_wrap=True,
        )
        raise typer.Exit(1) from None

    if was_added:
        console.print(
            f"[green]✓[/green] Associated repo '[bold]{slug}[/bold]' added to context "
            f"'[bold]{ctx_name}[/bold]' ({len(ctx.associated_repos)} associated repo(s) total)."
        )
    else:
        console.print(
            f"[green]✓[/green] Associated repo '[bold]{slug}[/bold]' is already registered "
            f"on context '[bold]{ctx_name}[/bold]' with this URL — no change."
        )


@repo_app.command(name="remove")
def repo_remove(
    ctx_name: str = typer.Argument(..., help="Context name"),
    slug: str = typer.Argument(..., help="Associated repo slug to remove from the registry"),
) -> None:
    """Remove an associated repo from a context's registry.

    Run: dadaia context repo remove <ctx> <slug>

    Registry-only (A17.2): this NEVER deletes the on-disk checkout at
    'repos/<slug>' — it only drops the registry entry, and always states
    explicitly what it leaves behind on disk. To also remove the checkout, delete
    it yourself, or run 'dadaia context dead <ctx>' first (which git-syncs and
    removes every repo in the set, including this one, before you unregister it).
    """
    try:
        ctx = _ctx_service().remove_repo(ctx_name, slug)
    except ContextNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except AssociatedRepoNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    console.print(
        f"[green]✓[/green] Associated repo '[bold]{slug}[/bold]' removed from context "
        f"'[bold]{ctx_name}[/bold]' registry ({len(ctx.associated_repos)} associated "
        "repo(s) remain)."
    )
    on_disk = resolve_workspace_root() / "repos" / slug
    if on_disk.exists():
        console.print(
            f"[yellow]![/yellow] The on-disk checkout at 'repos/{slug}' was left "
            "untouched — this only removes the registry entry, it never deletes "
            "files. Remove it yourself if it is no longer needed."
        )
    else:
        console.print(f"[dim]No on-disk checkout found at 'repos/{slug}'.[/dim]")


@app.command()
def delete(name: str = typer.Argument(..., help="Context name to delete")) -> None:
    """Delete a context. Context must be dead."""
    try:
        _ctx_service().delete(name)
        console.print(f"[green]✓[/green] Context '[bold]{name}[/bold]' deleted")
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


# v2 removals: activate/deactivate/promote/use removed in v0.1.7
