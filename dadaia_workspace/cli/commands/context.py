"""dadaia context subcommands."""

import contextlib
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
from dadaia_workspace.cli._specs_resolution import CONTEXT_NAME_RE as _CONTEXT_NAME_RE
from dadaia_workspace.cli._specs_resolution import (
    resolve_context_for_cli as _resolve_context_for_cli,
)
from dadaia_workspace.cli.redact import ContextRedactor
from dadaia_workspace.core.exceptions import (
    ContextAlreadyExistsError,
    ContextNotFoundError,
    ContextStateError,
    GitSyncError,
    RepoCatalogError,
    SchemaVersionError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.session_env import harness_session_id, sanitize_session_id
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.spec_context import presence, session_identity
from dadaia_workspace.features.spec_context.service import (
    DeadReviewRequiredError,
    DeadSecretFoundError,
    SpecContextService,
)

app = typer.Typer(help="Manage Spec Context Projects.")
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


def _ctx_to_dict(ctx: SpecContextProject) -> dict:  # type: ignore[type-arg]
    # v0.1.72 FR4 (bug `context-current-branch-stale-for-alive-repo`): the store's
    # current_branch is a snapshot written only at alive()/dead() transitions — for an
    # ALIVE repo on disk, report the ACTUAL checked-out branch (the stored snapshot is
    # still exposed as `stored_branch`, the dead/alive restore metadata).
    live_branch: str | None = None
    if ctx.state == ContextState.ALIVE:
        repo_path = resolve_workspace_root() / "repos" / ctx.repo_slug
        if (repo_path / ".git").exists():
            try:
                from dadaia_workspace import container

                live_branch = container.build_git_client().current_branch(repo_path) or None
            except Exception:  # noqa: BLE001 — display fallback, never break `show`
                live_branch = None
    return {
        "name": ctx.name,
        "state": ctx.state.value,
        "repo_slug": ctx.repo_slug,
        "repo_url": ctx.repo_url,
        "created_at": ctx.created_at,
        "alive_since": ctx.alive_since,
        "dead_since": ctx.dead_since,
        "current_branch": live_branch or ctx.current_branch,
        "stored_branch": ctx.current_branch,
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
    """Candidates = every known context's name and repo slug; excludes the caller's
    own resolved context name and its associated repo slug (render boundary ONLY —
    `contexts` is data the service already returned with true names)."""
    caller_name = _resolve_caller_context_name()
    caller_slug = next((ctx.repo_slug for ctx in contexts if ctx.name == caller_name), None)
    candidates: list[str] = []
    for ctx in contexts:
        candidates.append(ctx.name)
        candidates.append(ctx.repo_slug)
    return ContextRedactor(candidates, exclude=(caller_name, caller_slug))


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _sessions_dir(workspace_root: Path) -> Path:
    # Session-store path via the single owner (T-011-05 / FR-W1-05, ADR-12) — the bind CLI
    # no longer constructs the ``.dadaia/sessions`` path itself.
    return session_identity.sessions_dir(workspace_root)


def _load_session(sessions_dir: Path, session_id: str) -> dict[str, Any] | None:
    """Load a session file, return None if not found."""
    session_file = sessions_dir / f"{session_id}.json"
    if not session_file.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(session_file.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return None


def _session_is_stale(session_data: dict) -> bool:  # type: ignore[type-arg]
    """Check if a session is stale based on TTL."""
    try:
        last_seen = session_data.get("last_seen_at", "")
        ttl = int(session_data.get("ttl_seconds", 300))
        if not last_seen:
            return False
        last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        now = datetime.now(tz=UTC)
        elapsed = (now - last_seen_dt).total_seconds()
        return elapsed > ttl
    except Exception:
        return False


def _resolve_own_session_id(*, explicit: str | None = None, mint: bool = False) -> str | None:
    """Resolve THIS caller's own session identity (T-50-05: the single helper every verb
    below used to duplicate as its own copy-pasted micro-ladder).

    Order: *explicit* (a verb's own CLI override, e.g. ``release --session``) -> the
    eval-flow ``DADAIA_SESSION_ID`` (sanitized, CWE-22 — every site now gets the same
    defence ``bind`` already had) -> the harness-native session id
    (:func:`harness_session_id`) -> when *mint* is set, a freshly minted ``sess_*`` id
    (``bind``'s own fallback when a record must be created but neither channel carries
    an identity yet). Session IDENTITY only — never a context-resolution rung.
    """
    if explicit:
        return explicit
    env_sid = sanitize_session_id(os.environ.get("DADAIA_SESSION_ID"))
    if env_sid:
        return env_sid
    harness_id = harness_session_id()
    if harness_id:
        return harness_id
    if mint:
        return f"sess_{uuid.uuid4().hex[:8]}"
    return None


@app.command()
def create(
    name: str = typer.Argument(..., help="Context name"),
    repo: str = typer.Option(..., "--repo", help="Repo slug (directory name under repos/)"),
    url: str | None = typer.Option(
        None,
        "--url",
        help=(
            "Repo clone URL. Overrides the repos-catalog lookup when given — use it "
            "for a repo not in the catalog or to pin an explicit remote."
        ),
    ),
) -> None:
    """Create a new Spec Context Project in state 'dead'."""
    # Refuse at CREATE what every downstream verb refuses. `create` accepted names with
    # spaces or Unicode, and then `bind`, `bugs append` and every workflow rejected that
    # same context — so the operator ended up with a context they could create and never
    # use, which is a trap with no way out except deleting it
    # (bug a3-context-create-accepts-unusable-name). The rule is the ONE allowlist the
    # resolver already enforces; it is not a second, stricter opinion.
    for label, value in (("context name", name), ("repo slug", repo)):
        if not _CONTEXT_NAME_RE.fullmatch(value):
            err_console.print(
                f"[red]Error:[/red] invalid {label} {value!r}. Use only letters, digits, "
                "'-' and '_' — the same allowlist every other verb enforces, so a context "
                "that is created is always usable."
            )
            raise typer.Exit(1) from None
    workspace_root = resolve_workspace_root()
    # An explicit --url overrides the catalog lookup (FR-W2-03 a / T-011-08); otherwise
    # look up repo_url from the repos catalog, failing gracefully if unavailable.
    repo_url = ""
    if url is not None:
        repo_url = url
    else:
        try:
            repos_svc = container.build_repos_service()
            rows = repos_svc.list_known(workspace_root)
            for row in rows:
                if row.get("Repo Name") == repo:
                    repo_url = row.get("Repo URL", "")
                    break
        except (RepoCatalogError, Exception):
            pass

    try:
        ctx = _ctx_service().create(name, repo, repo_url)
        console.print(
            f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' created "
            f"(repo: {ctx.repo_slug}, state: {ctx.state})"
        )
    except (ContextAlreadyExistsError, ContextNotFoundError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


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
    try:
        contexts = _ctx_service().list_all()
    except SchemaVersionError as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(1) from None

    redactor = _build_context_redactor(contexts) if redact else None

    if json_output:
        payload = [
            {
                "name": ctx.name,
                "state": ctx.state.value,
                "repo_slug": ctx.repo_slug,
                "repo_url": ctx.repo_url,
                "created_at": ctx.created_at,
                "alive_since": ctx.alive_since,
                "dead_since": ctx.dead_since,
                "current_branch": ctx.current_branch,
            }
            for ctx in contexts
        ]
        if redactor is not None:
            payload = [redactor.json_value(row) for row in payload]
        print(json.dumps(payload, sort_keys=True))
        return
    if not contexts:
        console.print("[dim]No contexts found. Use 'dadaia context create' to create one.[/dim]")
        return

    table = Table(title="Spec Context Projects")
    table.add_column("Name", style="bold")
    table.add_column("State")
    table.add_column("Repo")

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
        # No name: use only explicit/caller-owned/cwd resolution; never foreign presence.
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
            data = _ctx_to_dict(ctx)
            # Show only this caller's session. A context-wide "last binder" fallback would
            # expose foreign state as the caller's own and can never be authoritative.
            workspace_root = resolve_workspace_root()
            sessions_dir = _sessions_dir(workspace_root)
            session_id = _resolve_own_session_id()
            session_obj = None
            if session_id:
                session_data = _load_session(sessions_dir, session_id)
                if session_data and not _session_is_stale(session_data):
                    session_obj = session_data
            data["session"] = session_obj
            # v0.1.76 T-4 (FR7): "presence" — who else is currently active on this
            # context, sourced from the ONLY concurrency-signal surface post-doctrine
            # (features/spec_context/presence.py). Distinct from "session" above (which
            # answers "what is MY session bound to" via the caller-owned record).
            # ``others_alive`` with an empty self-sid excludes nothing (no
            # real presence record is ever keyed by ""), so every live record on the
            # context is listed.
            data["presence"] = [
                {
                    "session_id": rec.session_id,
                    "runtime": rec.runtime,
                    "pid": rec.pid,
                    "started_at": rec.started_at,
                    "last_seen_at": rec.last_seen_at,
                }
                for rec in presence.others_alive(workspace_root, ctx.name, "")
            ]
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

    console.print(f"[bold]Name:[/bold]       {display_name}")
    console.print(f"[bold]State:[/bold]      {ctx.state.value}")
    console.print(f"[bold]Repo:[/bold]       {display_repo}")
    console.print(f"[bold]Repo URL:[/bold]   {repo_url_text}")
    console.print(f"[bold]Created:[/bold]    {ctx.created_at}")
    console.print(f"[bold]Alive since:[/bold]  {ctx.alive_since or '—'}")
    console.print(f"[bold]Dead since:[/bold]   {ctx.dead_since or '—'}")

    presence_records = presence.others_alive(resolve_workspace_root(), ctx.name, "")
    if presence_records:
        names = ", ".join(f"{rec.session_id} ({rec.runtime})" for rec in presence_records)
        console.print(f"[bold]Presence:[/bold]   {names}")
    else:
        console.print("[bold]Presence:[/bold]   —")


@app.command()
def alive(name: str = typer.Argument(..., help="Context name to make ALIVE")) -> None:
    """Transition a context to ALIVE; clone repo if absent. Idempotent if already ALIVE."""
    try:
        ws = resolve_workspace_root()
        ctx = container.build_spec_context_service(ws).alive(name)
        console.print(f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' is now ALIVE")
        # FR-S05/S06: a pre-existing specs/ tree below the canonical pattern version is
        # only safe-preserved + add-missing-merged — never silently upgraded. Offer the
        # backup-protected upgrade explicitly so structural drift is the operator's choice.
        with contextlib.suppress(Exception):
            from dadaia_workspace.core import specs_version as _ver

            specs_dir = ws / "repos" / ctx.repo_slug / "specs"
            current = _ver.read_pattern_version(specs_dir)
            if current < _ver.CANONICAL_SPECS_VERSION:
                console.print(
                    f"[yellow]![/yellow] specs pattern version {current} is below the "
                    f"canonical {_ver.CANONICAL_SPECS_VERSION}. Run "
                    f"[bold]dadaia specs upgrade[/bold] (backup-protected) to migrate."
                )
    except SchemaVersionError as exc:
        print(str(exc), file=sys.stderr)
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
    except GitSyncError as e:
        # Residual git failures (network, refs) surface as a clean error, not a
        # traceback (validation-029 F-06/F-22 no-traceback law).
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
    except (ContextNotFoundError, ContextStateError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


# Bind mode resolution. READ is self-protecting; IMPLEMENTATION and REVIEW are mutating.
# `spec` remains a legacy alias of READ. Mutating modes carry the BOUND_ prefix.
_BIND_MODE_ALIASES: dict[str, str] = {
    "READ": "READ",
    "SPEC": "READ",
    "IMPLEMENTATION": "IMPLEMENTATION",
    "REVIEW": "REVIEW",
}
_MUTATING_MODES = ("IMPLEMENTATION", "REVIEW")


@app.command()
def bind(
    name: str = typer.Argument(..., help="Context name to bind to"),
    mode: str = typer.Option(
        "read",
        "--mode",
        help=(
            "Binding mode (optional; default 'read'): read | implementation | review. "
            "Legacy alias: 'spec' maps to read."
        ),
    ),
    release: str | None = typer.Option(
        None, "--release", help="Release ID (required for implementation and review modes)"
    ),
    print_env: bool = typer.Option(
        False,
        "--print-env",
        help=(
            "Back-compat: also emit eval-compatible 'export DADAIA_*' lines for operators "
            "who still run 'eval $(dadaia context bind ...)'. Default off — bind persists "
            "the mode in the session record instead."
        ),
    ),
    force: bool = typer.Option(False, "--force", help="Deprecated compatibility flag (no-op)"),
    reason: str = typer.Option("", "--reason", help="Reason note (informational only)"),
) -> None:
    """Bind this shell session to a context.

    Run: dadaia context bind <name> [--mode <mode>] [--release <id>]

    With no --mode, binds normally in 'read' (observe) mode — never lock-blocked. The
    bound context, mode, and session id are persisted in the session record (consumed by
    the SDD gate); a human confirmation line is printed. Pass --print-env to additionally
    emit the legacy 'export DADAIA_*' lines for `eval $(...)` workflows.
    """
    mode_upper = mode.upper()
    if mode_upper not in _BIND_MODE_ALIASES:
        err_console.print(
            f"[red]Error:[/red] Invalid mode '{mode}'. Must be one of: "
            "read, spec, implementation, review"
        )
        raise typer.Exit(1) from None

    resolved_mode = _BIND_MODE_ALIASES[mode_upper]

    # Mutating bindings identify the release whose work they intend to change.
    if resolved_mode in _MUTATING_MODES and not release:
        err_console.print(f"[red]Error:[/red] --release <id> is required for --mode {mode.lower()}")
        raise typer.Exit(1) from None

    workspace_root = resolve_workspace_root()
    sessions_dir = _sessions_dir(workspace_root)

    # Ensure directories exist
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Verify context exists and is ALIVE (AC-T11-5)
    svc = _ctx_service()
    try:
        ctx = svc.show(name)
    except ContextNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    # Mutating modes require a checked-out ALIVE context.
    if resolved_mode in _MUTATING_MODES and ctx.state != ContextState.ALIVE:
        err_console.print(
            f"[red]Error:[/red] Context '{name}' is not ALIVE (state={ctx.state.value}). "
            "Run 'dadaia context alive <name>' first."
        )
        raise typer.Exit(1) from None

    # Stable session identity (bug bind-session-id-divergence, 2026-07-15): reuse the
    # SAME resolution order the gate/hooks use. Rebinds in one session therefore UPDATE
    # one record instead of minting a divergent sess_* per invocation.
    session_id = _resolve_own_session_id(mint=True)
    if session_id is None:  # pragma: no cover — mint=True always yields one
        raise RuntimeError("session-id resolution returned None despite mint=True")
    now = _now_iso()
    runtime = os.environ.get("DADAIA_RUNTIME", "unknown")
    pid = os.getpid()

    # The persisted mode the gate reads: mutating modes carry BOUND_; READ stays bare.
    persisted_mode = f"BOUND_{resolved_mode}" if resolved_mode in _MUTATING_MODES else resolved_mode

    session_data: dict = {  # type: ignore[type-arg]
        "session_id": session_id,
        "context": name,
        "mode": persisted_mode,
        "release": release,
        "runtime": runtime,
        "pid": pid,
        "bound_at": now,
        "last_seen_at": now,
        "ttl_seconds": 300,
        "is_stale": False,
    }

    # Persist the CLI session and, when available, the harness-native session record. There
    # is deliberately no context-global "incumbent" pointer: binding is caller-scoped.
    # Exactly ONE record per session, keyed by the resolved identity. The former
    # harness-alias dual-write (env id != harness id -> second record) recreated the
    # identity divergence this resolution order exists to prevent (consumer validation
    # F-07, 2026-07-15): hooks resolve DADAIA_SESSION_ID first too, so the alias never
    # carried information the primary record does not.
    session_identity.write_session(workspace_root, session_id, session_data)

    # T-50-05 (SPEC v0.5.0 FR1, the one addition in an otherwise subtractive lane):
    # T-50-04 deleted `_adopt_attributed_bind`, the ancestry-marker path that used to make
    # THIS exact binding reachable for a caller with no harness-native id and no
    # DADAIA_CONTEXT. Without this loud warning, that deletion turns a working flow into a
    # silent no-op — printed to stderr (never stdout) so it never corrupts
    # `eval $(dadaia context bind ... --print-env)`.
    # F-06 (v0.5.0 review): an exported DADAIA_SESSION_ID keys a reachable record (the
    # hooks' identity channel), and a `--print-env` caller is mid `eval $(...)` — both
    # flows produce a working binding, so warning there is noise, not signal.
    if (
        not harness_session_id()
        and not os.environ.get("DADAIA_CONTEXT")
        and not os.environ.get("DADAIA_SESSION_ID")
        and not print_env
    ):
        err_console.print(
            f"[yellow]![/yellow] No harness-native session id and DADAIA_CONTEXT is "
            f"unset in this shell — this binding is reachable only if DADAIA_CONTEXT="
            f"{name} is exported here (e.g. `eval $(dadaia context bind {name} "
            "--mode read --print-env)`)."
        )

    # Back-compat escape: emit ONLY the legacy export lines when requested, so the output
    # stays eval-safe for operators still running `eval $(dadaia context bind ... --print-env)`.
    if print_env:
        print(f"export DADAIA_CONTEXT={name}")
        print(f"export DADAIA_SESSION_ID={session_id}")
        print(f"export DADAIA_MODE={resolved_mode}")
        return

    # Human confirmation (NOT shell-export syntax): context, mode, session id.
    console.print(
        f"[green]✓[/green] Bound to '[bold]{name}[/bold]' "
        f"(mode: {resolved_mode.lower()}, session id: {session_id})"
    )


@app.command(name="release")
def release_cmd(
    session: str | None = typer.Option(
        None,
        "--session",
        help=(
            "Session id to release (optional override). When omitted, the session id is "
            "resolved from DADAIA_SESSION_ID (eval-flow override) or the harness-native "
            "session id (CLAUDE_CODE_SESSION_ID / CODEX_SESSION_ID / CODEX_THREAD_ID) — "
            "no flag is required in the normal harness case."
        ),
    ),
) -> None:
    """Release the current session's binding and advisory presence.

    Run: dadaia context release

    Resolution order for "this session's own id": ``--session``
    override -> ``DADAIA_SESSION_ID`` (eval-flow override) -> the harness-native session id
    (:func:`harness_session_id`) -> the last bind's CLI-minted session id read back from the
    session record directory (legacy default-flow fallback). Every presence record this
    session owns (across every context) is deleted (:func:`presence.clear`, idempotent — a
    session with no presence record is a clean no-op), then the CLI session record is
    unlinked.
    """
    from dadaia_workspace.features.spec_context import presence

    workspace_root = resolve_workspace_root()
    sessions_dir = _sessions_dir(workspace_root)

    resolved_sid = _resolve_own_session_id(explicit=session)
    if not resolved_sid:
        err_console.print(
            "[red]Error:[/red] No active session. Pass --session <id> or set "
            "DADAIA_SESSION_ID (e.g. eval $(dadaia context bind ... --print-env))."
        )
        raise typer.Exit(1) from None

    session_file = sessions_dir / f"{resolved_sid}.json"

    cleared = presence.clear(workspace_root, resolved_sid)
    session_file.unlink(missing_ok=True)

    if cleared:
        console.print(
            f"[green]✓[/green] Session '[bold]{resolved_sid}[/bold]' released "
            f"(presence record(s) dropped: {cleared})"
        )
    else:
        console.print(f"[green]✓[/green] Session '[bold]{resolved_sid}[/bold]' released")


@app.command()
def heartbeat() -> None:
    """Renew the heartbeat for the current session.

    Resolves the caller-owned session from the explicit eval-flow override or
    the harness-native session id persisted by ``context bind``.

    Run: dadaia context heartbeat
    """
    session_id = _resolve_own_session_id()
    if not session_id:
        err_console.print(
            "[red]Error:[/red] No caller-owned session identity. Run "
            "'dadaia context bind <name> --mode <mode>' inside a supported harness, "
            "or use 'eval $(dadaia context bind <name> --mode <mode> --print-env)' "
            "in a plain shell."
        )
        raise typer.Exit(1) from None

    workspace_root = resolve_workspace_root()
    sessions_dir = _sessions_dir(workspace_root)

    session_data = _load_session(sessions_dir, session_id)
    if session_data is None:
        err_console.print(
            f"[red]Error:[/red] Session '{session_id}' not found. "
            "It may have already been released."
        )
        raise typer.Exit(1) from None

    # Renew this session's advisory presence record(s), the sole concurrency signal.
    from dadaia_workspace.features.spec_context import presence

    ctx_name = session_data.get("context", "")
    now = _now_iso()
    presence.renew(workspace_root, session_id)
    session_identity.touch_last_seen_at(workspace_root, session_id, now=now)
    console.print(
        f"[green]✓[/green] Heartbeat renewed for session '[bold]{session_id}[/bold]' "
        f"(context={ctx_name}, last_seen_at={now})"
    )


@app.command()
def update(
    name: str = typer.Argument(..., help="Context name to update"),
    url: str = typer.Option(..., "--url", help="New repo clone URL to persist"),
) -> None:
    """Repair a context's repo URL (FR-W2-03 c / T-011-08).

    Run: dadaia context update <name> --url <url>

    The repair path for the VPS-migration scenario where no on-disk repo is present
    to back-fill from. Persists through the store update() API, preserving the record
    shape and locking.
    """
    try:
        ctx = _ctx_service().update_url(name, url)
        console.print(
            f"[green]✓[/green] Context '[bold]{ctx.name}[/bold]' repo URL set to {ctx.repo_url}"
        )
    except ContextNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


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
