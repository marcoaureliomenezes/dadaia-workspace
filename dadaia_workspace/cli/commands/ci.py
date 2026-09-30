"""CLI command group: `dadaia ci <verb>` — local CI-equivalent preflight gate + chokepoints."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

import typer

from dadaia_workspace.cli._fail import fail
from dadaia_workspace.cli._specs_resolution import repo_owner, resolve_workspace_root_for_cli
from dadaia_workspace.container import is_source_repo_root as _is_source_repo_root
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.exceptions import CiPreflightScopeError
from dadaia_workspace.core.gitflow import Gitflow, work_branch
from dadaia_workspace.features.chokepoints.branch_policy import GateFixes
from dadaia_workspace.features.ci_preflight import (
    all_passed,
    checks_for,
    failed_names,
    run_preflight,
    subprocess_runner,
)
from dadaia_workspace.features.spec_context.service import install_git_hooks

app = typer.Typer(help="Local CI-equivalent preflight gate + git-hook chokepoints.")


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
    """Run the library's locally runnable ci.yml checks; exit non-zero if any fail.

    In order: ruff format --check, ruff check, mypy --strict, repo hygiene, dadaia
    doctor, lint-imports, pytest (coverage floor). Run it before pushing — locally-solvable
    failures must never reach a push.
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
            f"`{fix_line(None, 'ci', 'preflight')}` targets the dadaia-workspace source repo; "
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
        typer.echo(f"\nPre-push gate FAILED: {', '.join(failed_names(results))}", err=True)
        for result in results:
            if not result.passed:
                tail = "\n".join(result.output.strip().split("\n")[-20:])
                if tail:
                    typer.echo(f"\n--- {result.name} ---\n{tail}", err=True)
        raise typer.Exit(1)

    typer.echo("\nAll preflight checks passed.")


def _no_canon_violations(paths: Iterable[str]) -> list[str]:
    """The canon predicate for a specs/ tree stamped below the canonical pattern: the
    v6 canon does not describe it, so no path in it is a v6 violation."""
    return []


def _gate_inputs(repo_root: Path, head: str) -> tuple[Gitflow, GateFixes]:
    """The gitflow through the ONE reader (ADR 0048: committed first, one warning on the
    default; an associated repo reads its owner's main repo) and the fix inputs: the repo,
    the live work branch by the ONE rule (cut locally or not) and HEAD's branch."""
    from dadaia_workspace.container import build_git_client

    git = build_git_client()
    workspace = resolve_workspace_root_for_cli(repo_root)
    owner = repo_owner(workspace, repo_root)
    main = workspace / "repos" / owner[2] if owner else None
    gitflow, warning = git.gitflow(repo_root, main)
    if warning:
        typer.echo(f"[pre-push] WARNING: {warning}", err=True)
    work = work_branch(repo_root / "specs", gitflow)
    cut = bool(git.git(repo_root, "for-each-ref", "--format=%(refname)", f"refs/heads/{work}"))
    return gitflow, GateFixes(repo=str(repo_root), work=work, cut=cut, head=head)


@app.command("push-gate-check")
def push_gate_check() -> None:
    """Pre-push gate: branch policy by the project gitflow + the range-scoped denylist scan.

    Branch model: the constitution's gitflow block (`dd-gitflow-default`).

    Reads the pre-push ref lines from stdin (``<local-ref> <local-sha> <remote-ref>
    <remote-sha>``). Every non-deletion ref (tags included) is scanned for new objects
    carrying a denylisted term — a work-branch push is the first publication to ``origin``.
    Branch deletions are never scanned; tag pushes are scanned but never gated on branch
    policy. No security verdict is checked here — that runs as a PR gate.

    The object source, denylist terms and baseline patterns are all built here and
    injected; a call site that fails to wire the object reader is a defect, never a
    bypass. No repo or context name is a term source.
    """
    from dadaia_workspace.container import (
        build_git_client,
        build_git_object_reader,
        load_denylist_baseline_patterns,
        load_denylist_terms,
    )
    from dadaia_workspace.core.specs_version import state
    from dadaia_workspace.features.chokepoints import push_gate_decision
    from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
    from dadaia_workspace.features.specs.canon import canon_violations

    repo_root = _repo_root()
    denylist_terms = load_denylist_terms()
    baseline_patterns = load_denylist_baseline_patterns()

    mode = (
        "operator denylist + baseline"
        if denylist_terms
        else "baseline only (no operator denylist; private names go in "
        "$DADAIA_PRIVACY_DENYLIST or .dadaia/states/privacy_denylist.json)"
    )
    typer.echo(f"[pre-push] denylist scan mode: {mode}", err=True)

    stdin_text = sys.stdin.read() if not sys.stdin.isatty() else ""
    refs, malformed = parse_push_stdin(stdin_text)
    # `git push origin HEAD` names its source "HEAD": the branch checked out IS that ref.
    git = build_git_client()
    branch = git.current_branch(repo_root)
    refs = [
        replace(r, local_ref=f"refs/heads/{branch}") if r.local_ref == "HEAD" and branch else r
        for r in refs
    ]
    gitflow, fixes = _gate_inputs(repo_root, branch)
    # The pushed commit's tree state, never the checkout's; foreign/v6 carry no v6 canon.
    sha = next((r.local_sha for r in refs if not r.is_deletion), "HEAD")
    canon_fn = canon_violations
    if git.git(repo_root, "ls-tree", sha, "specs"):
        shown = git.git(repo_root, "ls-tree", "--name-only", sha, "specs/constitution.md")
        text = git.git(repo_root, "show", f"{sha}:{shown}") if shown else ""
        kind, fix = state(repo_root / "specs", text)
        if kind in ("foreign", "upgradable"):
            canon_fn = _no_canon_violations
        if fix:
            typer.echo(f"[pre-push] the pushed specs/ tree is {kind}\nfix: {fix}", err=True)
    decision = push_gate_decision(
        refs,
        object_source=build_git_object_reader(),
        repo=repo_root,
        canon_violations_fn=canon_fn,
        gitflow=gitflow,
        fixes=fixes,
        malformed_lines=malformed,
        denylist_terms=denylist_terms,
        baseline_patterns=baseline_patterns,
    )
    if decision.warn:
        typer.echo(decision.warn, err=True)

    if not decision.allowed:
        fail(decision.message)


@app.command("install-hook")
def install_hook(
    force: bool = typer.Option(False, "--force", help="Overwrite existing git hooks."),
    repo: Path | None = typer.Option(None, "--repo", help="Target repo. Default: cwd's repo."),
) -> None:
    """Install the pre-push CI/security gate."""
    repo = repo or _repo_root()
    try:
        installed = install_git_hooks(repo, force=force)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from None
    if not installed:
        fix = fix_line(None, "ci", "install-hook", "--force", "--repo", str(repo))
        fail(f"pre-push hook already exists, not overwritten.\nfix: {fix}")
    for target in installed:
        typer.echo(f"Installed pre-push CI + security gate -> {target}")
