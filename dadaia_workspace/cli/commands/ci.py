"""CLI command group: `dadaia ci <verb>` — the git-hook chokepoints."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import replace
from pathlib import Path

import typer

from dadaia_workspace.cli._fail import fail
from dadaia_workspace.cli._specs_resolution import (
    repo_owner,
    resolve_workspace_root_for_cli,
    scope,
)
from dadaia_workspace.core import platform
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.gitflow import Gitflow, SeveralWorkBranches, work_branch
from dadaia_workspace.core.platform import act
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.features.chokepoints.branch_policy import (
    HEADS_PREFIX,
    Decision,
    GateFixes,
    PushRef,
    check_ref_policy,
    parse_push_stdin,
)
from dadaia_workspace.features.chokepoints.denylist_scan import BaselinePatternLike
from dadaia_workspace.features.spec_context.service import install_git_hooks

app = typer.Typer(help="Git-hook chokepoints: the pre-push and ref gates and their installer.")


def _repo_root() -> Path:
    """Resolve the enclosing git repo root, or fail with a clear message."""
    try:
        out = platform.run(["git", "rev-parse", "--show-toplevel"], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        fail("not inside a git repository", act("agent", "run it inside a git repository"))
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
    except SeveralWorkBranches as several:
        typer.echo(f"[pre-push] WARNING: {several.message}\nhint: {several.fix}", err=True)
        work = gitflow.work_prefix + several.keep
    except load_owner("dd-bug-resolution", "_refusal").Refusal as refusal:
        fail(f"[pre-push] BLOCKED: {refusal}", fix=refusal.fix)
    cut = bool(git.git(repo_root, "for-each-ref", "--format=%(refname)", f"refs/heads/{work}"))
    fixes = GateFixes(repo=str(repo_root), work=work, cut=cut, head=head)
    return gitflow, fixes


def _denylist(
    tag: str, repo: Path
) -> tuple[tuple[tuple[str, str], ...], tuple[BaselinePatternLike, ...]]:
    """The operator terms and the baseline patterns, the scan mode on stderr."""
    from dadaia_workspace.container import load_denylist_baseline_patterns, load_denylist_terms

    terms, patterns = load_denylist_terms(repo), load_denylist_baseline_patterns()
    mode = (
        "operator denylist + baseline"
        if terms
        else "baseline only (no operator denylist; private names go in "
        "$DADAIA_PRIVACY_DENYLIST or .dadaia/states/privacy_denylist.json)"
    )
    typer.echo(f"{tag} denylist scan mode: {mode}", err=True)
    return terms, patterns


def _canon_fn(repo_root: Path, sha: str, tag: str) -> Callable[[Sequence[str]], Sequence[str]]:
    """The canon predicate for the specs/ tree commit *sha* holds: foreign/v6 carry no v6 canon."""
    from dadaia_workspace.container import build_git_client
    from dadaia_workspace.core.specs_version import state
    from dadaia_workspace.features.specs.canon import canon_violations

    git = build_git_client()
    if not git.git(repo_root, "ls-tree", sha, "specs"):
        return canon_violations
    shown = git.git(repo_root, "ls-tree", "--name-only", sha, "specs/constitution.md")
    kind, fix = state(repo_root / "specs", git.git(repo_root, "show", f"{sha}:{shown}") if shown else "")  # fmt: skip
    if fix:
        typer.echo(f"{tag} the pushed specs/ tree is {kind}\nhint: {fix}", err=True)
    return _no_canon_violations if kind in ("foreign", "upgradable") else canon_violations


def _gate_decision(repo_root: Path, read_refs: Callable[[], str]) -> Decision:
    """The push gate's decision over the pre-push ref lines *read_refs* returns, from the
    repo's gitflow, denylist and canon."""
    from dadaia_workspace.container import build_git_client, build_git_object_reader
    from dadaia_workspace.features.chokepoints import push_gate_decision

    terms, patterns = _denylist("[pre-push]", repo_root)
    refs, malformed = parse_push_stdin(read_refs())
    sha = next((r.local_sha for r in refs if not r.is_deletion), "HEAD")
    canon_fn = _canon_fn(repo_root, sha, "[pre-push]")
    # `git push origin HEAD` names its source "HEAD": the branch checked out IS that ref.
    branch = build_git_client().current_branch(repo_root)
    refs = [
        replace(r, local_ref=f"refs/heads/{branch}") if r.local_ref == "HEAD" and branch else r
        for r in refs
    ]
    gitflow, fixes = _gate_inputs(repo_root, branch)
    return push_gate_decision(
        refs,
        object_source=build_git_object_reader(),
        repo=repo_root,
        canon_violations_fn=canon_fn,
        gitflow=gitflow,
        fixes=fixes,
        malformed_lines=malformed,
        denylist_terms=terms,
        baseline_patterns=patterns,
    )


def _content_decision(repo: Path, held: str, tag: str) -> Decision:
    """The push gate's content half over HEAD's branch published over *held*: what a branch no
    push could carry, a task's, still holds."""
    from dadaia_workspace.container import build_git_client, build_git_object_reader
    from dadaia_workspace.features.chokepoints import content_decision

    git = build_git_client()
    branch = git.current_branch(repo)
    ref = f"refs/heads/{branch or 'HEAD'}"
    tip = git.git(repo, "rev-parse", "HEAD")
    terms, patterns = _denylist(tag, repo)
    return content_decision(
        [PushRef(ref, tip, ref, held)],
        object_source=build_git_object_reader(),
        repo=repo,
        canon_violations_fn=_canon_fn(repo, tip, tag),
        fixes=GateFixes(repo=str(repo), head=branch or ""),
        denylist_terms=terms,
        baseline_patterns=patterns,
        tag=tag,
    )


@app.command("push-gate-check")
def push_gate_check(
    repo: Path | None = typer.Option(
        None, "--repo", help="Repo --onto judges. Default: cwd's repo."
    ),
    onto: str | None = typer.Option(
        None,
        "--onto",
        help="Merge gate: judge the content of `<onto>..HEAD` of the repo, no branch policy.",
    ),
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

    The merge gate of a worktree judges the same content with --onto, on a branch of any name.
    """
    if onto is not None:
        from dadaia_workspace.container import build_git_client

        repo = repo or _repo_root()
        base = build_git_client().git(repo, "rev-parse", "--verify", f"{onto}^{{commit}}")
        decision = _content_decision(repo, base, "[merge]")
    else:
        decision = _gate_decision(
            _repo_root(), lambda: "" if sys.stdin.isatty() else sys.stdin.read()
        )
    if decision.warn:
        typer.echo(decision.warn, err=True)
    if not decision.allowed:
        fail(decision.message)


@app.command("ref-gate-check")
def ref_gate_check() -> None:
    """Reference-transaction gate: a work-branch update must land on origin's sha.

    Reads ``<old> <new> <ref>`` lines on stdin. The reference-transaction hook resolves a zero
    old sha to the ref's current value before it calls this verb, so an existing ref's old sha
    arrives resolved; a descendant move touching only ``specs/audits/**`` passes.
    """
    from dadaia_workspace.container import build_git_client

    repo_root = _repo_root()
    lines = [raw.split() for raw in sys.stdin.read().splitlines() if raw.strip()]
    if any(len(parts) != 3 for parts in lines):
        fail(
            "[ref-gate] BLOCKED: a ref line is not `<old> <new> <ref>`",
            act(
                "agent",
                "pipe one line per ref update, each holding the old sha, the new sha and the ref name",
            ),
        )
    git = build_git_client()
    gitflow = _gitflow(repo_root)[0]

    def moved(old: str, new: str) -> tuple[bool, list[str]]:
        # rev-list exits 0 either way, so only a real fault raises; --no-renames keeps both paths of a rename
        behind = git.git(repo_root, "rev-list", "-n1", f"{new}..{old}")
        paths = git.git(repo_root, "diff", "--no-renames", "--name-only", f"{old}..{new}")
        anchor = Path(repo_root.anchor)
        zones: list[str] = [
            scope(anchor, anchor / "repos" / repo_root.name / p)[1] for p in paths.splitlines()
        ]
        return not behind, zones

    for old, new, ref in lines:
        tracking = f"refs/remotes/origin/{ref.removeprefix(HEADS_PREFIX)}"
        held = git.git(repo_root, "for-each-ref", "--format=%(objectname)", tracking)
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
    """Install the pre-push and reference-transaction gates."""
    repo = repo or _repo_root()
    installed = install_git_hooks(repo, force=force)
    if not installed:
        fail(
            "pre-push hook already exists, not overwritten.",
            fix_line(None, "ci", "install-hook", "--force", "--repo", str(repo)),
        )
    for target in installed:
        typer.echo(f"Installed {target.name} hook -> {target}")
