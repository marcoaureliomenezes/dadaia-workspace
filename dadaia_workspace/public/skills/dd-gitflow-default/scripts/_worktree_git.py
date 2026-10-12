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
from _grammar import SEMVER_RE, TAG_RE
from _platform import venv_tool
from _specs import git_line as git_line
from _specs import head
from _specs import quote as quote  # (`as`: re-exported to the worktree verbs)
from _specs import script as script
from _specs import workspace_of as workspace_of
from _worktree_names import NAME_RE, SCRIPT, Refusal, base, branch, name_of, plain, tree_path


def diff_sha256(tree: Path, work: str, tip: str) -> str:
    """The sha256 of *tip*'s plumbing diff over its merge-base with *work*: it names blob ids, so it binds the exact bytes a fast-forward lands."""
    base = git(tree, "merge-base", work, tip).strip()
    return hashlib.sha256(git(tree, "diff-tree", "-r", "-z", "--full-index", base, tip).encode()).hexdigest()  # fmt: skip


def dirty(tree: Path) -> bool:
    """Whether *tree* holds an uncommitted change or an untracked file."""
    return bool(git(tree, "status", "--porcelain").strip())


def _exe(root: Path) -> Path:
    if (exe := venv_tool(root / ".dadaia/.venv", "dadaia")).exists():
        return exe
    raise Refusal(
        "no workspace CLI", " ".join(map(quote, ("uvx", "dadaia-workspace", "init", str(root))))
    )


def cli(root: Path, *args: str, tree: Path | None = None) -> subprocess.CompletedProcess[str]:
    """One read-only run of the workspace CLI — the owner of every package grammar. With *tree*
    the run acts on that tree alone: its cwd, every root above it fenced."""
    run = subprocess.run  # stdin closed: a CLI never waits on the caller's pipe
    fence = (
        {"DADAIA_FENCED_ROOTS": os.pathsep.join(map(str, tree.resolve().parents))} if tree else {}
    )
    return run(
        [str(_exe(root)), *args],
        cwd=tree or root,
        env=scrubbed_env() | fence,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )  # fmt: skip


def cli_line(root: Path, *args: str) -> str:
    """The fix line running :func:`cli` with *args*, quoted for the host shell."""
    return " ".join((head(str(_exe(root))), *map(quote, args)))


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


def work_version(repo: Path, flow: dict[str, str]) -> str:
    prefix = flow["work"]
    branches = git(repo, "branch", "--list", f"{prefix}*", "--format=%(refname:short)").split()
    versions = [b[len(prefix) :] for b in branches if SEMVER_RE.match(b[len(prefix) :])]
    if len(versions) == 1:
        return versions[0]
    if versions:
        stale = sorted(versions, key=lambda v: tuple(map(int, v.split("."))))[0]
        raise Refusal(
            f"{len(versions)} work branches", git_line(repo, "branch", "-d", f"{prefix}{stale}")
        )
    tags = [tuple(map(int, m.groups())) for t in git(repo, "tag").split() if (m := TAG_RE.match(t))]
    major, minor, patch = max(tags, default=(0, 0, 0))
    nxt = f"{major}.{minor}.{patch + 1}" if tags else "0.1.0"
    raise Refusal(
        f"no work branch {prefix}<M.m.p>",
        git_line(repo, "branch", f"{prefix}{nxt}", flow["integration"]),
    )


def record_base(repo: Path, name: str, ref: str) -> None:
    """Persist the one base ref a plain worktree must return to."""
    git(repo, "config", "--local", f"branch.{branch(name)}.dadaia-base", ref)


def recorded_base(repo: Path, name: str, work: str = "") -> str:
    """The persisted base of a plain tree, or the grammar-derived base of a release tree."""
    if not plain(name):
        return base(name, work)
    ref = git(
        repo, "config", "--local", "--get", f"branch.{branch(name)}.dadaia-base", check=False
    ).strip()
    if not ref:
        raise Refusal(
            f"{branch(name)} has no recorded base ref",
            f"Operator action: recover the branch {branch(name)} from git history, then reopen the plain worktree",
        )
    return ref


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
    match = NAME_RE.match(name)
    assert match is not None  # `ours` admits names through this grammar.
    work = flow["work"] + (match["v"] or work_version(repo, flow)) if not plain(name) else ""
    span = f"{recorded_base(repo, name, work)}..{branch(name)}"
    ahead, changed = (
        int(git(repo, "rev-list", "--count", span, check=False) or 0),
        dirty(Path(path)),
    )
    state = "empty" if not ahead else "open" if changed else "ready"
    return _row(repo, path, state, _age(repo, name), name=name, ahead=ahead, dirty=changed)


def _absent(root: Path, repo: Path, held: set[str], found: list[dict[str, object]]) -> list[dict[str, object]]:  # fmt: skip
    """The leftovers git does not list: a `wt/*` branch with no tree (`orphan`), a directory two
    levels under `worktrees/<repo>/` or an empty one level under it (`unregistered`)."""
    out = []
    home = tree_path(root, repo.name)
    for ref in git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/wt/").split():
        if f"refs/heads/{ref}" not in held and (name := name_of(ref)):
            out.append(_row(repo, str(home / name), "orphan"))
    listed = {Path(str(r["path"])).resolve() for r in found}
    for stray in sorted(home.glob("*/*")):  # a name is two levels
        if stray.is_dir() and not {stray.resolve(), stray.parent.resolve()} & listed:
            out.append(_row(repo, str(stray), "unregistered"))
    for folder in sorted(home.glob("*")):  # an rc folder holding no tree
        named = any(Path(str(r["path"])).parent == folder for r in (*found, *out))
        if folder.is_dir() and not any(folder.iterdir()) and not named:
            out.append(_row(repo, str(folder), "unregistered"))
    return out


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
            "fix": f"Operator action: land the work of {t['worktree']}, then run "
            f"`{git_line(repo, 'worktree', 'remove', '--force', '--force', t['worktree'])}`"
        }  # fmt: skip
        for t in trees
    ]


def rows(root: Path) -> list[dict[str, object]]:
    """Every worktree fact of every repo with a tree under `worktrees/`, read from git alone:
    for a registered repo ours `ready` (ahead, clean), `open` (ahead, dirty) or `empty`, an
    `orphan` wt/* with no tree, a `foreign` worktree git registers (harness-native, hand-made,
    under a TTL zone), and an `unregistered` directory two levels under `worktrees/<repo>/` or
    an empty one level under it; for a repo no context owns, each linked tree is `unregistered`
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
