"""CLI command group: `dadaia ci <verb>` — local CI-equivalent preflight gate + chokepoints."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import typer

from dadaia_workspace.cli._specs_resolution import (
    resolve_session_id_for_cli,
    resolve_workspace_root_for_cli,
)
from dadaia_workspace.container import is_source_repo_root as _is_source_repo_root
from dadaia_workspace.core.exceptions import CiPreflightScopeError
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


def _repo_identity_root(worktree_root: Path) -> Path:
    """The repository's main working tree — its identity under ``<workspace>/repos/``.

    A linked worktree (``git worktree add``) may sit anywhere on disk; the repo it
    belongs to is named by the git common dir's parent, never by the worktree's own
    filesystem position. Falls back to *worktree_root* when git cannot answer.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=worktree_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return worktree_root
    # git prints ".git" (relative) from the main checkout and an absolute path from a
    # linked worktree; anchoring on the worktree root covers both without a git>=2.31 flag.
    return (worktree_root / out.stdout.strip()).resolve().parent


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
    from dadaia_workspace.features.chokepoints import (
        bundled_ledger_advisory,
        context_slug_for_path,
        pre_commit_decision,
    )
    from dadaia_workspace.features.spec_context import presence

    repo_root = _repo_root()
    workspace = resolve_workspace_root_for_cli(repo_root)
    ctx = context_slug_for_path(workspace, _repo_identity_root(repo_root))

    # v0.5.1 K7: the presence read is injected — `presence.others_alive` is wired
    # straight through, no adapter needed (its signature already matches). This is
    # what drops `chokepoints -> spec_context.presence` out of the import-linter
    # ignore list entirely; the retired ancestry/pid-probe wiring above it is DELETED
    # with the dead `caller_pid`/`pid_probe`/`ancestry` parameters (never read).
    decision = pre_commit_decision(
        workspace,
        ctx,
        own_sid=resolve_session_id_for_cli(),
        others_alive=presence.others_alive,
    )
    if decision.warn:
        typer.echo(decision.warn, err=True)

    # F015/F036 (20260827 audit): bundled-ledger advisory — WARN-only, never blocks.
    staged = subprocess.run(  # noqa: S603 — fixed argv, repo-root cwd
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=False,
    ).stdout.splitlines()
    bundling_warn = bundled_ledger_advisory(staged)
    if bundling_warn:
        typer.echo(bundling_warn, err=True)

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
    from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
    from dadaia_workspace.features.specs.canon import canon_violations, verdict_violations

    repo_root = _repo_root()
    workspace = resolve_workspace_root_for_cli(repo_root)

    denylist_terms = load_denylist_terms()
    baseline_patterns = load_denylist_baseline_patterns()
    own_slug = context_slug_for_path(workspace, _repo_identity_root(repo_root))
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
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
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


_SHA40_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def _first_parent_sha(repo_root: Path, sha: str) -> str | None:
    """The first-parent sha of *sha* in *repo_root*, or ``None`` (root commit, or git
    cannot resolve it — e.g. a shallow clone; the caller's CI job fetches full history).

    Delegates to the ONE first-parent implementation (F015, 20260830 audit) —
    ``git_objects.GitSubprocessObjectReader.first_parent`` — never a second raw
    subprocess with its own error modes.
    """
    from dadaia_workspace.container import build_git_object_reader

    parent: str | None = build_git_object_reader().first_parent(repo_root, sha)
    return parent


@app.command("verdict-check")
def verdict_check(
    head: str = typer.Option(
        ..., "--head", help="The PR/push head sha to prove coverage for (40-hex)."
    ),
    release_id: str = typer.Option(
        "",
        "--release-id",
        help="Optional release-id narrowing (default: search every release, live and archived).",
    ),
) -> None:
    """Require an APPROVED security-reviewer verdict covering ``--head`` (v0.4.4 FR4;
    v0.5.1 K7 — built over
    :func:`~dadaia_workspace.features.chokepoints.verdict.covering_verdict`).

    Backend for ``.github/scripts/pr-verdict-check.sh``'s ``security-verdict-gate`` CI
    job (a thin wrapper as of v0.5.1 K7): reads the COMMITTED verdict evidence under
    ``specs/releases/<id>/verdicts/`` (live) and ``specs/releases/_archive/<id>/
    verdicts/`` (archived) — never ``.dadaia/handoff/``, a workspace-local, gitignored
    directory a CI checkout never sees. Exit 0 (PASS) when a qualifying handoff's
    ``metrics.commit_sha`` is ``--head`` itself or ``--head``'s first parent; exit 1
    (FAIL) otherwise, naming the expected evidence shape.
    """
    from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE
    from dadaia_workspace.features.chokepoints.verdict import (
        covering_verdict,
        discover_verdict_candidates,
    )

    if not _SHA40_RE.match(head):
        typer.secho(
            f"[verdict-check] BLOCKED: --head '{head}' is not a 40-hex sha — refusing "
            "to use it as a git argument or coverage anchor.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    if release_id and release_id != "none" and not RELEASE_SEMVER_RE.match(release_id):
        typer.secho(
            f"[verdict-check] BLOCKED: --release-id '{release_id}' does not match the "
            "canon release-id pattern — refusing to use it to narrow the search.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    repo_root = _repo_root()
    parent = _first_parent_sha(repo_root, head)
    release_glob = release_id if (release_id and release_id != "none") else "*"
    candidates = discover_verdict_candidates(repo_root, release_glob)
    verdict = covering_verdict(candidates, head, parent)

    if verdict is None:
        typer.secho(
            f"[verdict-check] BLOCKED: no APPROVED security-reviewer verdict covers "
            f"head {head} — expected one at "
            "specs/releases/<id>/verdicts/<sha>.handoff.json or "
            "specs/releases/_archive/<id>/verdicts/<sha>.handoff.json "
            f"(sha = {head} or its first parent {parent or 'none'}).",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(
        f"[verdict-check] PASS: {verdict.path} — security-reviewer APPROVED "
        f"{verdict.commit_sha}, which covers head {head}."
    )


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
