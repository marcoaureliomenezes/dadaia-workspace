"""CLI command group: `dadaia ci <verb>` — the git-hook chokepoints."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path

import typer

from dadaia_workspace.cli._fail import fail
from dadaia_workspace.cli._specs_resolution import (
    repo_owner,
    resolve_workspace_root_for_cli,
    scope,
)
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.exceptions import GitSyncError
from dadaia_workspace.core.gitflow import Gitflow, work_branch
from dadaia_workspace.core.models.git_scan import ZERO_SHA, is_zero_sha
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.features.chokepoints.branch_policy import (
    HEADS_PREFIX,
    Decision,
    GateFixes,
    check_ref_policy,
    parse_push_stdin,
)
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
    except (subprocess.CalledProcessError, FileNotFoundError):
        fail("not inside a git repository", "Agent action: run it inside a git repository")
    return Path(out.stdout.strip())


def _no_canon_violations(paths: Iterable[str]) -> list[str]:
    """The canon predicate for a specs/ tree stamped below the canonical pattern: the
    v6 canon does not describe it, so no path in it is a v6 violation."""
    return []


def _gitflow(repo_root: Path) -> tuple[Gitflow, str | None, str]:
    """The gitflow through the one reader (committed first; an associated repo reads its
    owner's main repo), its warning on the default, and the slug of the repo's main repo."""
    from dadaia_workspace.container import build_git_client

    workspace = resolve_workspace_root_for_cli(repo_root)
    owner = repo_owner(workspace, repo_root)
    main = workspace / "repos" / owner[2] if owner else None
    gitflow, warning = build_git_client().gitflow(repo_root, main)
    return gitflow, warning, owner[2] if owner else repo_root.name


def _gate_inputs(repo_root: Path, head: str) -> tuple[Gitflow, GateFixes]:
    """The gitflow with one warning on the default, the fix inputs (the repo, the live
    work branch by the ONE rule, cut locally or not, and HEAD's branch)."""
    from dadaia_workspace.container import build_git_client

    git = build_git_client()
    gitflow, warning, slug = _gitflow(repo_root)
    if warning:
        typer.echo(f"[pre-push] WARNING: {warning}", err=True)
    try:
        work = work_branch(repo_root, gitflow, slug)
    except load_owner("dd-gitflow-default", "_worktree_git").SeveralWork as several:
        typer.echo(f"[pre-push] WARNING: {several.message}\nhint: {several.fix}", err=True)
        work = gitflow.work_prefix + several.keep
    except load_owner("dd-bug-resolution", "_refusal").Refusal as refusal:
        fail(f"[pre-push] BLOCKED: {refusal}", fix=refusal.fix)
    cut = bool(git.git(repo_root, "for-each-ref", "--format=%(refname)", f"refs/heads/{work}"))
    fixes = GateFixes(repo=str(repo_root), work=work, cut=cut, head=head)
    return gitflow, fixes


def _rewrite_unpublished(repo: Path, oldest: str, message: str | None) -> None:
    """Re-commit the unpublished range of HEAD, from *oldest*, as one commit holding the
    tracked working tree. Runs only when the push gate refuses that range on a denylist hit
    or a canon violation, and only over edits or deletions of the paths the gate lists;
    *message* replaces the message only when the gate lists a commit message. The git calls
    carry the sanctioned-tool marker (``git_subprocess``): the ref gate passes them."""
    from dadaia_workspace.container import build_git_client, build_git_object_reader
    from dadaia_workspace.features.chokepoints.push_gate import GateDecision

    git = build_git_client()
    tip = git.git(repo, "rev-parse", "HEAD")
    try:
        sha = git.git(repo, "rev-parse", "--verify", f"{oldest}^{{commit}}")
    except GitSyncError:
        sha = oldest
    branch = git.current_branch(repo) or "HEAD"
    held = git.git(repo, "for-each-ref", "--format=%(objectname)", f"refs/remotes/origin/{branch}")
    line = f"refs/heads/{branch} {tip} refs/heads/{branch} {held or ZERO_SHA}"
    decision = _gate_decision(repo, lambda: line)
    listed = decision.listed if isinstance(decision, GateDecision) else frozenset()
    changed = git.git(repo, "diff", "--name-status", "--no-renames", "-z", tip).split("\0")
    stray = sorted(
        p
        for st, p in zip(changed[::2], changed[1::2], strict=False)
        if st not in ("M", "D") or p not in listed
    )
    refusal = None
    if sha not in build_git_object_reader().unpublished(repo, tip):
        refusal = (
            f"cannot rewrite {oldest}: origin already holds it, or it is not in HEAD's history",
            "Agent action: pass the oldest commit origin does not hold, as the push gate's fix line names it",
        )
    elif not listed:
        refusal = (
            "the push gate lists no denylist or canon finding in HEAD's unpublished range",
            "Agent action: land the change through a worktree; this remedy answers a push gate refusal only",
        )
    elif stray:
        refusal = (
            f"the working tree changes paths the gate did not list: {', '.join(stray)}",
            "Agent action: revert or unstage every path the gate did not list, and add no path",
        )
    elif message and not (isinstance(decision, GateDecision) and decision.message_listed):
        refusal = (
            "the push gate lists no commit message, so the message stays",
            "Agent action: run the remedy again without the message option",
        )
    if refusal:
        fail(*refusal)
    git.git(repo, "reset", "--soft", sha)
    git.git(
        repo,
        "commit",
        "-qa",
        "--amend",
        "--allow-empty",
        *(("-m", message) if message else ("--no-edit",)),
    )


def _gate_decision(repo_root: Path, read_refs: Callable[[], str]) -> Decision:
    """The push gate's decision over the pre-push ref lines *read_refs* returns, from the
    repo's gitflow, denylist and canon."""
    from dadaia_workspace.container import (
        build_git_client,
        build_git_object_reader,
        load_denylist_baseline_patterns,
        load_denylist_terms,
    )
    from dadaia_workspace.core.specs_version import state
    from dadaia_workspace.features.chokepoints import push_gate_decision
    from dadaia_workspace.features.specs.canon import canon_violations

    denylist_terms = load_denylist_terms()
    baseline_patterns = load_denylist_baseline_patterns()

    mode = (
        "operator denylist + baseline"
        if denylist_terms
        else "baseline only (no operator denylist; private names go in "
        "$DADAIA_PRIVACY_DENYLIST or .dadaia/states/privacy_denylist.json)"
    )
    typer.echo(f"[pre-push] denylist scan mode: {mode}", err=True)

    refs, malformed = parse_push_stdin(read_refs())
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
            typer.echo(f"[pre-push] the pushed specs/ tree is {kind}\nhint: {fix}", err=True)
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
    return decision


@app.command("push-gate-check")
def push_gate_check(
    rewrite_from: str | None = typer.Option(
        None, "--rewrite-from", help="Remedy: re-commit the unpublished range from this commit."
    ),
    repo: Path | None = typer.Option(None, "--repo", help="Remedy target. Default: cwd's repo."),
    message: str | None = typer.Option(None, "--message", help="Remedy: the one commit's message."),
) -> None:
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

    With ``--rewrite-from`` it runs the gate's own remedy instead (``_rewrite_unpublished``).
    """
    if rewrite_from is not None:
        return _rewrite_unpublished(repo or _repo_root(), rewrite_from, message)
    decision = _gate_decision(_repo_root(), lambda: "" if sys.stdin.isatty() else sys.stdin.read())
    if not decision.allowed:
        fail(decision.message)


@app.command("ref-gate-check")
def ref_gate_check() -> None:
    """Reference-transaction gate: ``<old> <new> <ref>`` lines on stdin; a work-branch update
    must land on origin's sha, or be a descendant move touching only ``specs/audits/**``."""
    from dadaia_workspace.container import build_git_client

    repo_root = _repo_root()
    lines = [raw.split() for raw in sys.stdin.read().splitlines() if raw.strip()]
    if any(len(parts) != 3 for parts in lines):
        fail(
            "[ref-gate] BLOCKED: a ref line is not `<old> <new> <ref>`",
            "Agent action: pipe one line per ref update, each holding the old sha, the new sha and the ref name",
        )
    git = build_git_client()
    gitflow = _gitflow(repo_root)[0]

    def moved(old: str, new: str) -> tuple[bool, list[str]]:
        # rev-list exits 0 either way, so only a real fault raises; --no-renames keeps both paths of a rename
        behind = git.git(repo_root, "rev-list", "-n1", f"{new}..{old}")
        paths = git.git(repo_root, "diff", "--no-renames", "--name-only", f"{old}..{new}")
        anchor = Path(repo_root.anchor)
        zones = [
            scope(anchor, anchor / "repos" / repo_root.name / p)[1] for p in paths.splitlines()
        ]
        return not behind, list(zones)

    for old, new, ref in lines:
        tracking = f"refs/remotes/origin/{ref.removeprefix(HEADS_PREFIX)}"
        held = git.git(repo_root, "for-each-ref", "--format=%(objectname)", tracking)
        # git hands a zero old sha for a forced move too; the ref still holds its value in `prepared`.
        if is_zero_sha(old):
            old = git.git(repo_root, "for-each-ref", "--format=%(objectname)", ref) or old
        decision = check_ref_policy(
            [f"{old} {new} {ref}"], gitflow, {ref: held}, repo_root.name, moved
        )
        if not decision.allowed:
            fail(decision.message)


@app.command("install-hook")
def install_hook(
    force: bool = typer.Option(False, "--force", help="Overwrite existing git hooks."),
    repo: Path | None = typer.Option(None, "--repo", help="Target repo. Default: cwd's repo."),
) -> None:
    """Install the pre-push CI/security gate."""
    repo = repo or _repo_root()
    installed = install_git_hooks(repo, force=force)
    if not installed:
        fail(
            "pre-push hook already exists, not overwritten.",
            fix_line(None, "ci", "install-hook", "--force", "--repo", str(repo)),
        )
    for target in installed:
        typer.echo(f"Installed pre-push CI + security gate -> {target}")
