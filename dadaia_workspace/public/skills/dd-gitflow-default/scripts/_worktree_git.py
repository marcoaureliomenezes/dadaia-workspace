#!/usr/bin/env python3
"""Read-only facts about the workspace's canonical worktrees: git (every child runs with
`GIT_*` scrubbed from its env) and the gitflow the CLI's context record carries."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

from _git import git as git, parse_worktrees, scrubbed_env as scrubbed_env  # isort: skip
from _grammar import SEMVER_RE, TAG_RE, sole_live
from _platform import git_line as git_line
from _platform import head
from _platform import quote as quote  # (`as`: re-exported to the worktree verbs)
from _specs import script as script
from _specs import workspace_cli
from _specs import workspace_of as workspace_of
from _worktree_names import SCRIPT, Refusal, base_of, branch, name_of, tree_path


def diff_sha256(tree: Path, work: str, tip: str) -> str:
    """The sha256 of *tip*'s plumbing diff over its merge-base with *work*: it names blob ids, so it binds the exact bytes a fast-forward lands."""
    base = git(tree, "merge-base", work, tip).strip()
    return hashlib.sha256(git(tree, "diff-tree", "-r", "-z", "--full-index", base, tip).encode()).hexdigest()  # fmt: skip


def dirty(tree: Path) -> bool:
    """Whether *tree* holds an uncommitted change or an untracked file."""
    return bool(git(tree, "status", "--porcelain").strip())


def cli(root: Path, *args: str, tree: Path | None = None) -> subprocess.CompletedProcess[str]:
    """One read-only run of the workspace CLI — the owner of every package grammar. With *tree*
    the run acts on that tree alone: its cwd, every root above it fenced."""
    run = subprocess.run  # stdin closed: a CLI never waits on the caller's pipe
    fence = (
        {"DADAIA_FENCED_ROOTS": os.pathsep.join(map(str, tree.resolve().parents))} if tree else {}
    )
    return run(
        [str(workspace_cli(root)), *args],
        cwd=tree or root,
        env=scrubbed_env() | fence,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )  # fmt: skip


def cli_line(root: Path, *args: str) -> str:
    """The fix line running :func:`cli` with *args*, quoted for the host shell."""
    return " ".join((head(str(workspace_cli(root))), *map(quote, args)))


def gitflows(root: Path) -> dict[str, dict[str, str]]:
    """Each registered repo's gitflow `{principal, integration, work, main}` (`main`: its
    context's main repo), read by the one
    reader through `context list --json`; a repo whose record has none is absent."""
    done = cli(root, "context", "list", "--json")
    try:
        listed = json.loads(done.stdout) if not done.returncode else None
    except ValueError:
        listed = None
    if not isinstance(listed, list):
        raise Refusal(
            f"context list failed: {done.stderr.strip() or done.stdout.strip()}",
            cli_line(root, "doctor"),
        )
    return {
        repo: {**row["gitflow"], "main": row["main_repo"]}
        for row in listed
        if row.get("gitflow")
        for repo in (row["main_repo"], *(a["slug"] for a in row["associated_repos"]))
    }


def flow_for(root: Path, repo: Path) -> dict[str, str]:
    flow = gitflows(root).get(repo.name)
    if flow is None:
        raise Refusal(f"no context on disk owns repos/{repo.name}", cli_line(root, "doctor"))
    return flow


def work_versions(repo: Path, flow: dict[str, str]) -> list[str]:
    """The versions of the repo's local work-prefix branches, whatever release is live."""
    prefix = flow["work"]
    branches = git(repo, "branch", "--list", f"{prefix}*", "--format=%(refname:short)").split()
    return [b[len(prefix) :] for b in branches if SEMVER_RE.match(b[len(prefix) :])]


def next_version(repo: Path, flow: dict[str, str]) -> str:
    """The version of the work branch to create when the repo has none."""
    tags = [tuple(map(int, m.groups())) for t in git(repo, "tag").split() if (m := TAG_RE.match(t))]
    major, minor, patch = max(tags, default=(0, 0, 0))
    return sole_live(repo.parent / flow["main"] / "specs") or (f"{major}.{minor}.{patch + 1}" if tags else "0.1.0")  # fmt: skip


class SeveralWork(Refusal):
    """Several local work branches; *keep* is the version the rule keeps."""

    def __init__(self, message: str, fix: str, keep: str) -> None:
        super().__init__(message, fix)
        self.keep = keep


def work_version(repo: Path, flow: dict[str, str]) -> str:
    prefix = flow["work"]
    versions = work_versions(repo, flow)
    if len(versions) == 1:
        return versions[0]
    if versions:
        ordered = sorted(versions, key=lambda v: tuple(map(int, v.split("."))))
        low, high = f"{prefix}{ordered[0]}", f"{prefix}{ordered[-1]}"
        drop = git_line(repo, "branch", "-d", low)
        merged = git(repo, "branch", "--merged", high, "--list", low).strip()
        raise SeveralWork(f"{len(versions)} work branches", drop if merged else f"Agent action: merge {low} into {high}, then run {drop}", ordered[-1])  # fmt: skip
    nxt = next_version(repo, flow)
    remote = git(
        repo, "branch", "-r", "--list", f"*/{prefix}{nxt}", "--format=%(refname:short)"
    ).split()
    raise Refusal(
        f"no work branch {prefix}<M.m.p>",
        git_line(repo, "branch", f"{prefix}{nxt}", remote[0] if remote else flow["integration"]),
    )


def not_a_name(name: str, live: str = "") -> Refusal:
    """The one refusal of a name the grammar does not take; its one fix lists the trees."""
    shape = live or "0.5.0"
    return Refusal(
        f"not a worktree name: {name!r} (expected {shape}/rc-<N>/wt-rc, {shape}/rc-<N>/job-<n>/wt-main, {shape}/rc-<N>/job-<n>/wt-task-<kkk>, {shape}/wt-backlog-<slug> or {shape}/wt-hotfix-<bug>)",  # fmt: skip
        f"{script(SCRIPT)} list",
    )


def _trees(repo: Path) -> list[dict[str, str]]:
    """Every linked worktree of *repo* (the main checkout excluded), from git's porcelain."""
    return parse_worktrees(git(repo, "worktree", "list", "--porcelain"))


def ours(repo: Path) -> list[dict[str, str]]:
    """Our worktrees of *repo*: a tree at `worktrees/<repo>/<name>` on its canonical
    `wt/<name>` branch, locked or not — merge's own re-attach leaves one unlocked."""
    home = tree_path(repo.parents[1], repo.name)
    return [
        {"path": t["worktree"], "name": name}
        for t in _trees(repo)
        if (name := name_of(t.get("branch", "").removeprefix("refs/heads/")))
        and Path(t["worktree"]).resolve() == (home / name).resolve()
    ]


def _row(repo: Path, path: str, state: str, age: float = 0.0, **facts: object) -> dict[str, object]:
    """One worktree: WARN past a day or off-canon; `fix` shown only when ready or orphan;
    `exit`, the line a hold names — `clean` for an empty tree, else `merge`."""
    verb = "clean" if state == "empty" else "merge"
    line = f"{script(SCRIPT)} {verb} {quote(path)}"
    # merge cannot clear a directory git does not know
    if state == "orphan" and Path(path).exists():
        line = f"Agent action: remove the directory {path}, then run `{line}`"
    return {"repo": repo.name, "path": path, "state": state, "age_hours": age, "registered": True,
            **facts, "warn": state not in ("ready", "open", "empty") or age > 24,
            "fix": line if state in ("ready", "orphan") else "",
            "exit": line if state in ("ready", "open", "empty", "orphan") else ""}  # fmt: skip


def _age(repo: Path, name: str) -> float:
    """Hours since the branch of tree *name* was born (its oldest reflog entry; now when none)."""
    born = git(repo, "reflog", "show", "--date=unix", "--format=%gd", branch(name), check=False)
    stamps = re.findall(r"@\{(\d+)\}", born) or [str(int(time.time()))]
    return round((time.time() - int(stamps[-1])) / 3600, 1)


def _ours(repo: Path, flow: dict[str, str], name: str, path: str) -> dict[str, object]:
    """Our tree *name*: `empty` (nothing ahead), `ready` (ahead, clean) or `open` (ahead, dirty)."""
    span = f"{base_of(name, flow['work'])}..{branch(name)}"
    ahead, changed = (
        int(git(repo, "rev-list", "--count", span, check=False) or 0),
        dirty(Path(path)),
    )
    state = "empty" if not ahead else "open" if changed else "ready"
    return _row(repo, path, state, _age(repo, name), name=name, ahead=ahead, dirty=changed)


def _strays(folder: Path, listed: set[Path], ancestors: set[Path]) -> list[Path]:
    """The leaf folders under *folder* that no tree lists nor is an ancestor of one: strays at any depth."""
    out: list[Path] = []
    for child in sorted(folder.glob("*")):
        here = child.resolve()
        if child.is_dir() and not child.is_symlink() and here not in listed:
            sub = _strays(child, listed, ancestors)
            # a level folder holding only its AGENTS.md is layout, not a stray
            layout = [p.name for p in child.iterdir()] == ["AGENTS.md"]
            out += sub if sub or here in ancestors or layout else [child]
    return out


def _absent(root: Path, repo: Path, held: set[str], found: list[dict[str, object]]) -> list[dict[str, object]]:  # fmt: skip
    """The leftovers git does not list: a `wt/*` branch with no tree (`orphan`), and each stray
    folder under `worktrees/<repo>/` (`unregistered`), one row per path whose removal is its fix."""
    out = []
    home = tree_path(root, repo.name)
    for ref in git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/wt/").split():
        if f"refs/heads/{ref}" not in held:
            row = _row(repo, str(home / ref.removeprefix("wt/")), "orphan")
            if not name_of(ref):  # a name `merge` refuses names no merge as its exit
                row |= {"fix": "", "exit": ""}
            out.append(row)
    listed = {Path(str(r["path"])).resolve() for r in (*found, *out)}
    ancestors = {p for path in listed for p in path.parents}
    return out + [
        _row(repo, str(stray), "unregistered")
        | {"fix": f"Agent action: remove the directory {stray}"}
        for stray in _strays(home, listed, ancestors)
    ]


def _repo_rows(root: Path, repo: Path, flow: dict[str, str]) -> list[dict[str, object]]:
    trees, mine = _trees(repo), {Path(r["path"]).resolve(): r["name"] for r in ours(repo)}
    out: list[dict[str, object]] = []
    for tree in trees:
        path, name = tree["worktree"], mine.get(Path(tree["worktree"]).resolve())
        if name is None or not Path(path).is_dir():
            out.append(_row(repo, path, "foreign" if name is None else "orphan"))
        else:
            out.append(_ours(repo, flow, name, path))
    return out + _absent(root, repo, {t.get("branch", "") for t in trees}, out)


def _unregistered(repo: Path, trees: list[dict[str, str]]) -> list[dict[str, object]]:
    """The linked trees of a repo no context owns: a finding whose one fix is the operator's act."""
    return [
        _row(repo, t["worktree"], "unregistered", registered=False)
        | {
            "fix": f"Agent action: land the work of {t['worktree']}, then run "
            f"`{git_line(repo, 'worktree', 'remove', '--force', '--force', t['worktree'])}`"
        }  # fmt: skip
        for t in trees
    ]


def rows(root: Path) -> list[dict[str, object]]:
    """Every worktree fact of every repo with a tree under `worktrees/`, read from git alone:
    for a registered repo ours `ready` (ahead, clean), `open` (ahead, dirty) or `empty`, an
    `orphan` wt/* with no tree, a `foreign` worktree git registers (harness-native, hand-made,
    under a TTL zone), and an `unregistered` leaf folder at any depth under `worktrees/<repo>/`
    that no tree lists; for a repo no context owns, each linked tree is `unregistered`
    with `registered: false`."""
    known, homes = gitflows(root), tree_path(root, "")
    names = sorted(
        {*known, *(d.name for d in homes.iterdir() if d.is_dir())} if homes.is_dir() else known
    )
    out: list[dict[str, object]] = []
    for name in names:
        repo = root / "repos" / name
        if (repo / ".git").exists():
            out += _repo_rows(root, repo, known[name]) if name in known else _unregistered(repo, _trees(repo))  # fmt: skip
    return out
