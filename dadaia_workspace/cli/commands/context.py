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
from dadaia_workspace.cli._fail import fail
from dadaia_workspace.cli._specs_resolution import (
    alive_context_trees,
    own_bind_for_cli,
    resolve_session_id,
)
from dadaia_workspace.cli.redact import ContextRedactor, build_context_redactor
from dadaia_workspace.core import session_store
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.exceptions import (
    AssociatedRepoConflictError,
    AssociatedRepoNotFoundError,
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    DadaiaError,
    GitCloneError,
    InvalidContextNameError,
    RepoUrlMissingError,
    SchemaVersionError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.models.spec_context import (
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.spec_context.service import (
    SpecContextService,
)
from dadaia_workspace.features.workspace import onboarding

app = typer.Typer(help="Manage Spec Context Projects.")
# FR17 (v0.4.4, T-044-28): associated-repo registry verbs, nested under `context repo`
# — same `app.add_typer` pattern as `specs release`/`specs segment`.
repo_app = typer.Typer(help="Manage a context's associated repos (main repo excluded).")
app.add_typer(repo_app, name="repo")
console = Console()


def _ctx_service() -> SpecContextService:
    try:
        return container.build_spec_context_service(resolve_workspace_root())
    except WorkspaceNotInitializedError as exc:
        fail(exc)
    except SchemaVersionError as exc:
        fail(exc)


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


def resolve_own_session_id(*, explicit: str | None = None, mint: bool = False) -> str | None:
    """THIS caller's session identity: *explicit* (a verb's own override), else the ONE
    session-id rule (:func:`core.invocation.resolve_session_id`, no payload), else — when
    *mint* is set — a fresh ``sess_*`` id, the write-side fallback ``bind`` owns."""
    sid = explicit or resolve_session_id(None, os.environ)
    return sid or (f"sess_{uuid.uuid4().hex[:8]}" if mint else None)


def print_next_step(workspace_root: Path, focus: str | None = None) -> None:
    """The derived onboarding next step (FR6 AC6.2) — the text ``doctor`` also reports."""
    trees = alive_context_trees(workspace_root)
    bind, session = own_bind_for_cli()
    step = onboarding.next_step(
        workspace_root, trees, focus, None if session is None else bool(bind)
    )
    if step is not None:
        console.print(step.text(), markup=False, highlight=False, soft_wrap=True)


def create_fix(root: Path, error: Exception, name: str | None, urls: list[str]) -> str:
    """The invocation, every ``--associated-repo`` kept (AC3.5), with what failed made a
    placeholder — never the failing command repeated; an owned slug names its owner."""
    if isinstance(error, AssociatedRepoConflictError):
        return fix_line(root, "context", "list")
    if isinstance(error, ContextAlreadyExistsError):
        name = "<another-name>"
    failed = error.url if isinstance(error, GitCloneError) else None
    urls = [u if u != failed else "<clone-url>" for u in urls]
    flags = [arg for u in urls[1:] for arg in ("--associated-repo", u)]
    return fix_line(
        root, "context", "create", *([name] if name else []), "--main-repo", urls[0], *flags
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
    """Clone (or adopt) every repo, install the pre-push hook, make the context ALIVE —
    one step; on failure nothing is left behind."""
    ws = resolve_workspace_root()
    try:
        ctx = container.build_spec_context_service(ws).create(
            main_repo, name=name, associated_urls=tuple(associated)
        )
    except (DadaiaError, OSError) as e:
        fail(f"{e}\nfix: {create_fix(ws, e, name, [main_repo, *associated])}")
    suffix = f", {len(ctx.associated_repos)} associated repo(s)" if ctx.associated_repos else ""
    console.print(
        f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' created and ALIVE "
        f"(main repo: repos/{ctx.repo_slug}{suffix})",
        highlight=False,
        soft_wrap=True,
    )
    print_next_step(ws, ctx.name)


@app.command(name="list")
def list_all(
    json_output: bool = typer.Option(False, "--json", help="Output stable JSON contract"),
    redact: bool = typer.Option(
        False,
        "--redact",
        help=(
            "Mask every context name and repo slug other than this caller's resolved "
            "context. Default output is unchanged."
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

    redactor = build_context_redactor(contexts) if redact else None

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
            "No contexts found. Create one: "
            + fix_line(
                resolve_workspace_root(),
                *["context", "create", "<name>", "--main-repo", "<clone-url>"],
            ),
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


@app.command()
def show(
    name: str | None = typer.Argument(None, help="Context name"),
    json_output: bool = typer.Option(False, "--json", help="Output stable JSON contract"),
    redact: bool = typer.Option(
        False,
        "--redact",
        help=(
            "Mask every context name and repo slug other than this caller's resolved "
            "context. Default output is unchanged."
        ),
    ),
) -> None:
    """Show details of a context."""
    svc = _ctx_service()
    bound, session_id = own_bind_for_cli()  # name and session from ONE Bind
    ctx, target = None, name or bound
    try:
        ctx = svc.show(target) if target else None
    except ContextNotFoundError as e:
        fail(e)

    redactor: ContextRedactor | None = None
    if redact:
        try:
            all_contexts = svc.list_all()
        except SchemaVersionError:
            all_contexts = [ctx] if ctx is not None else []
        redactor = build_context_redactor(all_contexts)

    if json_output:
        if ctx is None:
            print(json.dumps({"context": None}, indent=2))
        else:
            data = _ctx_to_dict(svc, ctx)
            # Show only this caller's session. A context-wide "last binder" fallback would
            # expose foreign state as the caller's own and can never be authoritative.
            workspace_root = resolve_workspace_root()
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
    except DadaiaError as e:
        fail(e)


@app.command()
def baseline(
    name: str = typer.Argument(..., help="Context whose onboarding is published"),
    message: str = typer.Option(
        "chore: publish the dadaia specs", "--message", help="Commit message."
    ),
) -> None:
    """Publish the project's main repo, append-only: adopt what origin holds, or give an
    empty origin the local principal; the work branch carries specs/. A re-run is a no-op.
    An associated repo publishes by plain `git push` under the pre-push gate."""
    try:
        work = _ctx_service().baseline(name, message=message)
    except (DadaiaError, OSError) as exc:
        fail(exc)
    done = f"published on {work}" if work else "already published — nothing to do"
    console.print(f"✓ '{name}' {done}", markup=False, highlight=False, soft_wrap=True)


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
    except DadaiaError as e:
        fail(e)


@app.command(
    epilog="Examples: .dadaia/.venv/bin/dadaia context bind my-ctx | eval $(.dadaia/.venv/bin/dadaia context bind my-ctx --print-env)"
)
def bind(
    name: str = typer.Argument(..., help="Context name to bind to"),
    print_env: bool = typer.Option(
        False,
        "--print-env",
        help=(
            "Emit eval-compatible 'export DADAIA_CONTEXT/DADAIA_SESSION_ID' lines for "
            "`eval $(.dadaia/.venv/bin/dadaia context bind ... --print-env)`. Default off — the binding is "
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
        if svc.show(name).state == ContextState.DEAD:
            fix = fix_line(workspace_root, "context", "alive", name)
            fail(f"Context '{name}' is DEAD — bring it back first.\nfix: {fix}")
    except ContextNotFoundError as e:
        fail(e)

    # Stable session identity (bug bind-session-id-divergence, 2026-07-15): the SAME
    # resolution order the gate/hooks use, so rebinds UPDATE one record.
    session_id = resolve_own_session_id(mint=True) or ""
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

    # An id-less shell's bind lives in its env: the eval epilogue is its only path (#S11).
    if not resolve_session_id(None, os.environ):
        if print_env:
            for line in session_store.binding_env_lines(name, session_id):
                print(line)
            return
        if os.environ.get("DADAIA_CONTEXT") != name:
            print(
                f"! No session id in this shell — this binding is reachable only where "
                f"DADAIA_CONTEXT={name} is exported (`eval $(... --print-env)`).",
                file=sys.stderr,
            )

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
        fail(e)
    except RepoUrlMissingError as e:
        ws = resolve_workspace_root()
        fail(
            f"{e}\nfix: {fix_line(ws, 'context', 'repo', 'add', ctx_name, slug, '--url', '<clone-url>')}"
        )

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

    Registry-only: this NEVER deletes the on-disk checkout at
    'repos/<slug>' — it only drops the registry entry, and always states
    explicitly what it leaves behind on disk. To also remove the checkout, delete
    it yourself, or run 'dadaia context dead <ctx>' first (which git-syncs and
    removes every repo in the set, including this one, before you unregister it).
    """
    try:
        ctx = _ctx_service().remove_repo(ctx_name, slug)
    except ContextNotFoundError as e:
        fail(e)
    except AssociatedRepoNotFoundError as e:
        fail(e)

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
        fail(e)


# v2 removals: activate/deactivate/promote/use removed in v0.1.7
