"""CLI command group: `dadaia ci <verb>` — local CI-equivalent preflight gate + chokepoints."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer

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
    """Warn about other live context presence, then run scoped backlog checks.

    Concurrent-session detection is advisory and always allows the commit.
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

    # Backlog-consistency backstop (v0.1.25 R1, ADR-D): a hand-written divergent twin (and
    # planted BL-SCHEMA/DUP/CONFLICT/STALE violations) is rejected at the commit boundary even
    # though specs/backlog/ is gitignored + ADDITIVE. Runs over the committing repo's specs/.
    _run_backlog_doctor_gate(repo_root)


def _staged_backlog_paths(repo_root: Path) -> list[str]:
    """Return the paths staged for the pending commit that live under ``specs/backlog/``.

    Uses ``git diff --cached --name-only -- specs/backlog`` (pathspec-filtered) run from the
    repo root, the same ``subprocess`` seam this cli module already uses in ``_repo_root``.
    An empty list means the staged changeset does not touch the backlog. Any git failure
    (no repo, no git) yields an empty list — the caller then skips the gate (fail-open, the
    CI full sweep remains the backstop).
    """
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--", "specs/backlog"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def _run_backlog_doctor_gate(repo_root: Path) -> None:
    """Run BL-* over ``<repo_root>/specs`` at the pre-commit chokepoint (v0.1.25 R1).

    A no-op when the repo has no ``specs/backlog/`` (not an SDD spec context). Any ERROR
    finding blocks the commit with an actionable per-finding listing.

    W1-4 scoping: the blocking BL-* sweep runs ONLY when the staged changeset intersects
    ``specs/backlog/**``. A commit that stages no backlog file is never blocked by
    pre-existing backlog debt (bugs ``precommit-backlog-doctor-blocks-unrelated-commits`` +
    ``backlog-doctor-blocks-consumed-item-refactor-commit``). The full, unscoped sweep still
    runs in CI via ``dadaia backlog doctor`` (the ci.yml backlog-doctor job) — unchanged.
    """
    specs_dir = repo_root / "specs"
    if not (specs_dir / "backlog").is_dir():
        return
    if not _staged_backlog_paths(repo_root):
        typer.echo(
            "[pre-commit] no staged specs/backlog changes — skipping backlog doctor gate.",
            err=True,
        )
        return
    from dadaia_workspace.cli.anchors import derive_cli_anchors
    from dadaia_workspace.features.backlog.doctor import Severity, run_backlog_doctor

    # Code refs in committed intents are REPO-ROOT-relative (e.g.
    # ``dadaia_workspace/core/models/lifecycle.py#Sym``), so the registry's source root is the
    # repo root — anchors are derived as ``<repo-relative-path>#symbol`` matching the refs.
    source_root = repo_root
    workspace = _resolve_workspace_root(repo_root)
    alias_map_path = workspace / ".dadaia" / "states" / "backlog_subject_aliases.txt"

    findings = run_backlog_doctor(
        specs_dir=specs_dir,
        source_root=source_root,
        catalog_path=specs_dir / "memory" / "product" / "catalog.json",
        alias_map_path=alias_map_path,
        archive_root=specs_dir / "_archive",
        cli_anchors=derive_cli_anchors(),
    )
    errors = [f for f in findings if f.severity is Severity.ERROR]
    if errors:
        typer.secho(
            f"[pre-commit] BLOCKED: backlog doctor found {len(errors)} error(s):",
            fg=typer.colors.RED,
            err=True,
        )
        for finding in errors:
            slug = f" [{finding.slug}]" if finding.slug else ""
            typer.echo(f"  {finding.code.value}{slug} {finding.message}", err=True)
        raise typer.Exit(1)


@app.command("push-gate-check")
def push_gate_check() -> None:
    """Pre-push security-verdict gate (FR-W1-02): require a security-reviewer APPROVE per sha.

    Reads the pre-push ref lines from stdin (``<local-ref> <local-sha> <remote-ref>
    <remote-sha>``). For each non-zero, non-tag local sha a ``security-reviewer`` APPROVE
    handoff (``metrics.commit_sha`` == sha) must exist under ``.dadaia/handoff/``. Branch
    deletions and tag-only pushes pass. Commits are never review-blocked here.
    """
    from dadaia_workspace.features.chokepoints import push_gate_decision
    from dadaia_workspace.features.chokepoints.service import parse_push_refs

    repo_root = _repo_root()
    workspace = _resolve_workspace_root(repo_root)
    handoff_root = workspace / ".dadaia" / "handoff"

    stdin_text = sys.stdin.read() if not sys.stdin.isatty() else ""
    refs = parse_push_refs(stdin_text)
    decision = push_gate_decision(handoff_root, refs)
    if not decision.allowed:
        typer.secho(decision.message, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


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
