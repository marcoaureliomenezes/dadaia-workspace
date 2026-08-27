"""CLI command group: `dadaia ci <verb>` — local CI-equivalent preflight gate + chokepoints."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import typer

from dadaia_workspace.container import is_source_repo_root as _is_source_repo_root
from dadaia_workspace.core.exceptions import CiPreflightScopeError
from dadaia_workspace.features.chokepoints import (
    GcOutcome,
    gc_consumed_push_verdicts,
    iter_security_approvals,
)
from dadaia_workspace.features.chokepoints.service import LEDGER_RELPATH
from dadaia_workspace.features.ci_preflight import (
    all_passed,
    checks_for,
    failed_names,
    run_preflight,
    subprocess_runner,
)

app = typer.Typer(help="Local CI-equivalent preflight gate + git-hook chokepoints.")

# .../dadaia_workspace/cli/commands/ci.py -> parents[2] == .../dadaia_workspace
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "public" / "scripts"
_HOOK_SOURCE = _SCRIPTS_DIR / "pre-push-ci-gate.sh"
_PRE_COMMIT_HOOK_SOURCE = _SCRIPTS_DIR / "pre-commit-presence-gate.sh"


def _repo_root() -> Path:
    """Resolve the enclosing git repo root, or fail with a clear message."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise typer.BadParameter("not inside a git repository") from exc
    return Path(out.stdout.strip())


@app.command()
def preflight(
    quick: bool = typer.Option(False, "--quick", help="Skip the slow e2e suite."),
    fail_fast: bool = typer.Option(
        True, "--fail-fast/--no-fail-fast", help="Stop at the first failing check."
    ),
) -> None:
    """Run ruff + mypy --strict + pytest locally; exit non-zero if any fail.

    This is the gate the pre-push hook calls. Locally-solvable failures must
    never reach a push.
    """
    root = _repo_root()
    # The checks are structurally bound to this repo: they lint `dadaia_workspace/` and
    # `tests/`, type-check `dadaia_workspace/`, and read this repo's setup.cfg. In a
    # consumer repo none of those paths exist and the consumer venv has no ruff/mypy, so
    # the gate reported a phantom lint FAIL and blamed a missing poetry — sending the
    # operator to install a tool that would not have helped
    # (bug ci-preflight-unusable-outside-the-source-repo). Refuse honestly instead. The
    # source-repo test is the existing one, not a second definition.
    if not _is_source_repo_root(root):
        raise CiPreflightScopeError(
            f"`dadaia ci preflight` targets the dadaia-workspace source repo; "
            f"{str(root)!r} is not it. The gate lints and type-checks the library's own "
            "paths, which do not exist here. Run your repo's own CI checks instead."
        )
    checks = checks_for(quick=quick)
    typer.echo(f"Running {len(checks)} preflight check(s){' (quick)' if quick else ''}…")
    results = run_preflight(checks, subprocess_runner(root), fail_fast=fail_fast)

    for result in results:
        marker = "PASS" if result.passed else "FAIL"
        typer.echo(f"  [{marker}] {result.name}")

    if not all_passed(results):
        typer.secho(
            f"\nPre-push gate FAILED: {', '.join(failed_names(results))}",
            fg=typer.colors.RED,
            err=True,
        )
        for result in results:
            if not result.passed:
                tail = "\n".join(result.output.strip().splitlines()[-20:])
                if tail:
                    typer.echo(f"\n--- {result.name} ---\n{tail}", err=True)
        raise typer.Exit(1)

    typer.secho("\nAll preflight checks passed.", fg=typer.colors.GREEN)


def _resolve_workspace_root(repo_root: Path) -> Path:
    """Resolve the workspace root from inside a (possibly sub-) repo. Falls back to the repo."""
    if env := os.environ.get("WORKSPACE_ROOT"):
        return Path(env)
    from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    try:
        return resolve_workspace_root(repo_root)
    except WorkspaceNotInitializedError:
        return repo_root


@app.command("pre-commit-check")
def pre_commit_check() -> None:
    """Warn about other live context presence. Advisory only — never blocks the commit.

    Concurrent-session detection is advisory and always allows the commit (NO-LOCKS
    DOCTRINE, v0.1.76). v0.5.0 FR9/D9: the backlog-doctor BLOCK that used to run here
    is DELETED — CI's `backlog-doctor` job already runs the unscoped sweep over the
    whole tree; blocking a commit on pre-existing backlog debt only ever punished
    humans and agents on a shared tree (bug
    `precommit-backlog-doctor-blocks-unrelated-commits`). The installed
    `pre-commit-presence-gate.sh` wrapper additionally guarantees exit 0 unconditionally,
    regardless of what this command does.
    """
    from dadaia_workspace.container import build_process_ancestry
    from dadaia_workspace.features.chokepoints import context_slug_for_path, pre_commit_decision

    repo_root = _repo_root()
    workspace = _resolve_workspace_root(repo_root)
    ctx = context_slug_for_path(workspace, repo_root)

    # Wire the read-only ancestry adapter and the pid-liveness probe from the composition root.
    ancestry_adapter = build_process_ancestry()
    pid_probe = None
    try:
        from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe

        probe = OsProcessProbe()
        pid_probe = probe.is_pid_alive
    except Exception:  # noqa: BLE001 — no liveness seam ⇒ TTL-only (cross-platform safe).
        pid_probe = None

    decision = pre_commit_decision(
        workspace,
        ctx,
        caller_pid=os.getpid(),
        env_sid=os.environ.get("DADAIA_SESSION_ID"),
        pid_probe=pid_probe,
        ancestry=ancestry_adapter.is_ancestor,
    )
    if decision.warn:
        typer.echo(decision.warn, err=True)
    if not decision.allowed:
        typer.secho(decision.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


def _foreign_repo_slugs(
    workspace: Path,
    own_slug: str | None,
    registry_identities: Iterable[tuple[str, str]],
) -> list[str]:
    """The v0.11.0 FR5 registry-derived foreign-name set, union'd with the v0.9.0 FR3
    directory-derived set, minus the pushed repo's own identities.

    ``{registry context names} UNION {registry repo_slugs} UNION {repos/ dir names} -
    {own context name, own repo slug}`` (SPEC v0.11.0 FR5). *own_slug* is the pushed
    repo's directory name under ``repos/`` (``context_slug_for_path``); *own_name* is
    resolved from *registry_identities* as the ``name`` of whichever entry's
    ``repo_slug`` equals *own_slug* — ``None`` when the pushed repo is not itself
    registered (a fresh/unregistered checkout), in which case only the slug is
    subtracted, exactly as v0.9.0 did.

    **Both** self-identities are subtracted (A5.2): a context's ``name`` and its
    ``repo_slug`` are separate fields (``core/models/spec_context.py``) and may
    differ — subtracting only the slug would re-open the A3.2 regression (matching the
    pushed repo's own slug would block every push of this repository) through the new
    door the registry-derived NAME opens.

    DEAD and relocated registry contexts contribute their terms just like ALIVE ones
    (the whole point of FR5 — a context whose repo directory is absent no longer
    silently loses its protection). Hidden directory entries (dotfiles) are skipped; a
    missing ``repos/`` directory (e.g. the library repo run standalone) contributes no
    directory-derived term, and a missing/empty/malformed registry (already swallowed
    by :func:`container.load_registry_context_identities`, A5.4) contributes no
    registry-derived term — the union degrades gracefully to whichever source is
    healthy, never crashing the push hook.
    """
    identities = list(registry_identities)
    own_name = next((name for name, slug in identities if slug == own_slug), None)
    own_identities = {value for value in (own_slug, own_name) if value}

    registry_terms = {value for name, slug in identities for value in (name, slug) if value}

    repos_dir = workspace / "repos"
    dir_terms: set[str] = set()
    if repos_dir.is_dir():
        dir_terms = {
            entry.name
            for entry in repos_dir.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        }

    return sorted((registry_terms | dir_terms) - own_identities)


@app.command("push-gate-check")
def push_gate_check() -> None:
    """Pre-push gate: branch-name validation + the range-scoped denylist scan.

    Branch model: `DADAIA.md` §4 (Gitflow) + `dd-gitflow-default` — this docstring
    states it nowhere else.

    Reads the pre-push ref lines from stdin (``<local-ref> <local-sha> <remote-ref>
    <remote-sha>``). Every non-deletion ref (tags included) is then scanned for new
    objects carrying a denylisted term (v0.9.0 FR1/FR2) — under v2 this feature push is
    the first publication to ``origin``. Branch deletions are never scanned; tag pushes
    are scanned but were never gated on branch policy. There is no security-verdict
    check on this path (v0.4.4 A3.4) — it runs as a PR gate instead (FR4).

    The object source, denylist terms, baseline patterns and foreign-slug set are ALL
    built and passed here — the CLI is the sole composition point for the injected
    ``GitObjectReader`` port (FR7); a production call site that failed to wire one
    would be a defect, never a bypass (FR6 row 4). The foreign-slug set is now
    REGISTRY-DERIVED (v0.11.0 FR5): it reaches the registry through the
    ``container.load_registry_context_identities`` seam, never through a direct
    ``infrastructure`` import (``cli-no-infrastructure``).
    """
    from dadaia_workspace.container import (
        build_git_object_reader,
        load_denylist_baseline_patterns,
        load_denylist_terms,
        load_registry_context_identities,
    )
    from dadaia_workspace.features.chokepoints import context_slug_for_path, push_gate_decision
    from dadaia_workspace.features.chokepoints.service import parse_push_stdin

    repo_root = _repo_root()
    workspace = _resolve_workspace_root(repo_root)

    denylist_terms = load_denylist_terms()
    baseline_patterns = load_denylist_baseline_patterns()
    own_slug = context_slug_for_path(workspace, repo_root)
    registry_result = load_registry_context_identities(workspace)
    if registry_result.degraded:
        # SPEC v0.4.2 FR8(2)/GRILL P13/A8.3: a malformed registry no longer shrinks the
        # foreign-name layer silently — exactly one stderr note names the degradation,
        # and the scan still proceeds against the repos/ directory-derived fallback.
        typer.echo(
            "[pre-push] context registry is malformed or unreadable — the "
            "registry-derived foreign-name layer falls back to the repos/ "
            "directory-derived set only; the scan still proceeds.",
            err=True,
        )
    foreign_slugs = _foreign_repo_slugs(workspace, own_slug, registry_result.identities)

    mode = (
        "operator denylist + baseline" if denylist_terms else "baseline only (no operator denylist)"
    )
    typer.echo(f"[pre-push] denylist scan mode: {mode}", err=True)

    stdin_text = sys.stdin.read() if not sys.stdin.isatty() else ""
    refs, malformed = parse_push_stdin(stdin_text)
    decision = push_gate_decision(
        refs,
        object_source=build_git_object_reader(),
        repo=repo_root,
        malformed_lines=malformed,
        denylist_terms=denylist_terms,
        baseline_patterns=baseline_patterns,
        foreign_slugs=foreign_slugs,
    )
    if decision.warn:
        typer.echo(decision.warn, err=True)
    if not decision.allowed:
        typer.secho(decision.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


_LEDGER_BASENAME = Path(*LEDGER_RELPATH).name


@app.command("gc-push-verdicts")
def gc_push_verdicts(
    sha: list[str] = typer.Option(
        ...,
        "--sha",
        help=(
            "A merged PR head sha the caller has ALREADY confirmed landed (repeatable "
            "— pass one --sha per newly-merged PR head). Never pass a sha before the "
            "PR merge it names is confirmed."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Report what would be consumed without touching the filesystem.",
    ),
) -> None:
    """FR24 (v0.4.3 T-043-39 / M-1 six-axis-review rider / v0.4.4 D5): delete the
    APPROVED security-verdict handoff(s) a merged PR just consumed.

    Cadence contract (v0.4.4 D5 — re-keyed from the pushed ``develop`` tip to the
    merged PR head sha; the security verdict itself is now a PR gate, not a push gate,
    per FR3/FR4 — see ``features/chokepoints/service.py``'s module docstring for the
    two sanctioned observation points this verb realizes, observation point (b)): the
    ship flow runs this verb IMMEDIATELY AFTER a PR merges into ``develop`` or
    ``main`` — never before. Each ``--sha`` is a merged PR head sha the caller has
    already confirmed landed.

    Idempotent and best-effort by design: exits 0 even when nothing matches (no verdict
    handoff covers the given sha(s)), even when the AG.1 lane guard refuses a candidate,
    and even when the audit-ledger append fails for one handoff — a GC sweep run
    strictly AFTER the merge it cleans up after has already landed can never change
    that merge's outcome, so a non-zero exit here would be a failure signal a caller
    could misread as a merge problem, and this verb never emits one.
    """
    repo_root = _repo_root()
    workspace = _resolve_workspace_root(repo_root)
    shas = {value for value in sha if value}

    if dry_run:
        handoff_root = workspace / ".dadaia" / "handoff"
        matches = [a for a in iter_security_approvals(handoff_root) if a.commit_sha in shas]
        typer.echo(
            f"dadaia ci gc-push-verdicts (dry-run): would consume {len(matches)} "
            f"verdict(s); ledger {_LEDGER_BASENAME}."
        )
        for approval in matches:
            typer.echo(f"  would consume: {approval.source}")
        return

    outcome: GcOutcome = gc_consumed_push_verdicts(workspace, shas)
    skipped = len(outcome.append_failed) + len(outcome.lane_guard_refused)
    typer.echo(
        f"dadaia ci gc-push-verdicts: consumed {len(outcome.deleted)} verdict(s), "
        f"skipped {skipped}; ledger {_LEDGER_BASENAME}."
    )
    for name in outcome.deleted:
        typer.echo(f"  consumed: {name}")
    for name in outcome.append_failed:
        typer.echo(f"  skipped (ledger append failed): {name}")
    for name in outcome.lane_guard_refused:
        typer.echo(f"  skipped (lane guard refused): {name}")


def _install_one(source: Path, target: Path, *, label: str, force: bool) -> None:
    """Copy a hook script into ``.git/hooks/`` (0755), honoring ``--force``."""
    if target.exists() and not force:
        typer.secho(
            f"{target.name} hook already exists at {target}; use --force to overwrite.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(1)
    shutil.copyfile(source, target)
    target.chmod(0o755)
    typer.secho(f"Installed {label} -> {target}", fg=typer.colors.GREEN)


@app.command("install-hook")
def install_hook(
    force: bool = typer.Option(False, "--force", help="Overwrite existing git hooks."),
) -> None:
    """Install the pre-commit presence check and pre-push CI/security gate."""
    root = _repo_root()
    hooks_dir = root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        raise typer.BadParameter(f"{hooks_dir} not found (is this a git repository?)")
    _install_one(
        _PRE_COMMIT_HOOK_SOURCE,
        hooks_dir / "pre-commit",
        label="pre-commit presence check",
        force=force,
    )
    _install_one(
        _HOOK_SOURCE,
        hooks_dir / "pre-push",
        label="pre-push CI + security gate",
        force=force,
    )
