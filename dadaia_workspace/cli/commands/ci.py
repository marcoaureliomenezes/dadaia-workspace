"""CLI command group: `dadaia ci <verb>` — the git-hook chokepoints."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

import typer

from dadaia_workspace.cli._fail import fail
from dadaia_workspace.cli._specs_resolution import repo_owner, resolve_workspace_root_for_cli
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.gitflow import Gitflow, work_branch
from dadaia_workspace.features.chokepoints.branch_policy import GateFixes
from dadaia_workspace.features.spec_context.service import install_git_hooks

app = typer.Typer(help="Git-hook chokepoints: the pre-push gate and its installer.")


def _repo_root() -> Path:
    """Resolve the enclosing git repo root, or fail with a clear message."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise typer.BadParameter("not inside a git repository") from exc
    return Path(out.stdout.strip())


def _no_canon_violations(paths: Iterable[str]) -> list[str]:
    """The canon predicate for a specs/ tree stamped below the canonical pattern: the
    v6 canon does not describe it, so no path in it is a v6 violation."""
    return []


def _gate_inputs(repo_root: Path, head: str) -> tuple[Gitflow, GateFixes]:
    """The gitflow through the ONE reader (ADR 0048: committed first, one warning on the
    default; an associated repo reads its owner's main repo), the fix inputs (the repo,
    the live work branch by the ONE rule, cut locally or not, and HEAD's branch)."""
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
    fixes = GateFixes(repo=str(repo_root), work=work, cut=cut, head=head)
    return gitflow, fixes


@app.command("push-gate-check")
def push_gate_check() -> None:
    """Pre-push gate: branch policy by the project gitflow + the range-scoped denylist scan.

    Branch model: the constitution's gitflow block (`dd-gitflow-default`).

    Reads the pre-push ref lines from stdin (``<local-ref> <local-sha> <remote-ref>
    <remote-sha>``). Every non-deletion ref (tags included) is scanned for new objects
    carrying a denylisted term — a work-branch push is the first publication to ``origin``.
    Branch deletions are never scanned; tag pushes are scanned but never gated on branch
    policy.

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
