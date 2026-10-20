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
from functools import cache
from pathlib import Path

from _git import git as git, parse_worktrees, scrubbed_env as scrubbed_env  # isort: skip
from _grammar import SEMVER_RE, TAG_RE, sole_live
from _ledger import denylist_file
from _platform import act, cli_argv, command, git_inline, git_line, inline, is_link, venv_dir
from _specs import run_cli
from _specs import workspace_of as workspace_of
from _worktree_names import (
    LAUNCH,
    LOCK,
    Refusal,
    base_of,
    branch,
    is_bare_level,
    kind_of,
    name_of,
    tree_path,
)


def locked_add(name: str, *opts: str) -> tuple[str, ...]:
    """The git words that add tree *name* with *opts*, locked: the one spelling of the lock reason."""
    return ("worktree", "add", *opts, "--lock", "--reason", f"{LOCK}{name}")


def reattach(repo: Path, tree: Path, name: str) -> str:
    """The fix line that re-adds the removed tree *name* at *tree* on its branch, locked as `new` locks it."""
    return git_line(repo, *locked_add(name, "-f", "-f"), str(tree), branch(name))


def diff_sha256(tree: Path, work: str, tip: str) -> str:
    """The sha256 of *tip*'s plumbing diff over its merge-base with *work*: it names blob ids, so it binds the exact bytes a fast-forward lands."""
    base = git(tree, "merge-base", work, tip).strip()
    return hashlib.sha256(git(tree, "diff-tree", "-r", "-z", "--full-index", base, tip).encode()).hexdigest()  # fmt: skip


def dirty(tree: Path) -> bool:
    """Whether *tree* holds an uncommitted change or an untracked file."""
    return bool(git(tree, "status", "--porcelain").strip())


def cli_words(root: Path, *args: str) -> tuple[str, ...]:
    """The words that run the workspace CLI with *args*, its head from the kernel's `cli_argv`."""
    return (*cli_argv(venv_dir(root)), *args)


def cli(root: Path, *args: str, tree: Path | None = None) -> subprocess.CompletedProcess[str]:
    """One read-only run of the workspace CLI — the owner of every package grammar. With *tree*
    the run acts on that tree alone: its cwd, every root above it fenced, so the workspace's
    denylist file is handed over by the loader's own `$DADAIA_PRIVACY_DENYLIST` input."""
    fence = (
        {"DADAIA_FENCED_ROOTS": os.pathsep.join(map(str, tree.resolve().parents))}
        | ({"DADAIA_PRIVACY_DENYLIST": str(file)} if (file := denylist_file(root)) else {})
        if tree
        else {}
    )
    return run_cli(root, *args, cwd=tree or root, env=scrubbed_env() | fence, stdin=subprocess.DEVNULL)  # fmt: skip


@cache  # ponytail: per-process, the CLI runs one verb per process; thread it through merge if a long-lived caller appears
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
            command(*cli_words(root, "doctor")),
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
        raise Refusal(f"no context on disk owns repos/{repo.name}", command(*cli_words(root, "doctor")))  # fmt: skip
    return flow


def work_versions(repo: Path, flow: dict[str, str], ref: str = "refs/heads") -> list[str]:
    """The versions of the work-prefix branches under *ref* (`refs/heads` or `refs/remotes/origin`)."""
    head = f"{ref}/{flow['work']}"
    names = git(repo, "for-each-ref", "--format=%(refname)", f"{head}*").split()
    return [v for n in names if SEMVER_RE.match(v := n[len(head) :])]


def next_version(repo: Path, flow: dict[str, str]) -> str:
    """The version of the work branch to create when the repo has none."""
    tags = [tuple(map(int, m.groups())) for t in git(repo, "tag").split() if (m := TAG_RE.match(t))]
    major, minor, patch = max(tags, default=(0, 0, 0))
    return sole_live(repo.parent / flow["main"] / "specs") or (f"{major}.{minor}.{patch + 1}" if tags else "0.1.0")  # fmt: skip


class SeveralWork(Refusal):
    """Several local work branches; *keep* is the version the rule keeps, *text* the unlabeled act."""

    def __init__(self, message: str, text: str, keep: str) -> None:
        super().__init__(message, act("agent", text))
        self.text, self.keep = text, keep


def _switch(repo: Path, high: str) -> str:
    return f"run `{git_inline(repo, 'switch', high)}`"


def drop_argv(repo: Path, low: str, high: str) -> list[list[str]]:
    """The git argv that retire *low* once merged into *high*: upstream unset if any, then `-d`; empty when unmerged."""
    merged = git(repo, "for-each-ref", "--merged", high, "--format=x%(upstream)", f"refs/heads/{low}").strip()  # fmt: skip
    return [*([["branch", "--unset-upstream", low]] if merged != "x" else []), ["branch", "-d", low]] if merged else []  # fmt: skip


def drop_steps(repo: Path, low: str, high: str) -> list[str]:
    """The act steps that retire *low* once merged into *high*: `high` checked out (`-d` judges the checkout), then each `drop_argv`."""
    argv = drop_argv(repo, low, high)
    return [_switch(repo, high), *(f"run `{git_inline(repo, *a)}`" for a in argv)] if argv else []


def several_work(repo: Path, flow: dict[str, str], versions: list[str], ref: str = "refs/heads") -> tuple[str, str]:  # fmt: skip
    """The highest of several *versions* and the unlabeled act over the local branches ("" for an origin read)."""
    ordered = sorted(versions, key=lambda v: tuple(map(int, v.split("."))))
    if ref != "refs/heads":
        return ordered[-1], ""
    low, high = (f"{flow['work']}{ordered[i]}" for i in (0, -1))
    return ordered[-1], ", then ".join(drop_steps(repo, low, high) or [_switch(repo, high), f"merge {low} into {high}"])  # fmt: skip


def work_version(repo: Path, flow: dict[str, str], ref: str = "refs/heads") -> str:
    prefix = flow["work"]
    versions = work_versions(repo, flow, ref)
    if len(versions) == 1:
        return versions[0]
    if versions:
        keep, text = several_work(repo, flow, versions, ref)
        raise SeveralWork(f"{len(versions)} work branches", text, keep)
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
    shape = live or "<M.m.p>"
    return Refusal(
        f"not a worktree name: {name!r} (expected {shape}/rc-<N>/wt-rc, {shape}/rc-<N>/job-<n>/wt-main, {shape}/rc-<N>/job-<n>/wt-task-<kkk>, {shape}/wt-backlog-<slug> or {shape}/wt-hotfix-<bug>)",  # fmt: skip
        command(*LAUNCH, "list"),
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
    `exit`, the line a hold names — `clean` for an empty tree, `resume` for a paused one, else `merge`."""
    verb = {"empty": "clean", "paused": "resume"}.get(state, "merge")
    line = command(*LAUNCH, verb, path)
    # merge cannot clear a directory git does not know
    if state == "orphan" and Path(path).exists():
        line = act(
            "agent", f"remove the directory {path}, then run `{inline(*LAUNCH, verb, path)}`"
        )
    return {"repo": repo.name, "path": path, "state": state, "age_hours": age, "registered": True,
            "kind": None, **facts, "warn": state not in ("ready", "open", "empty", "paused") or age > 24,
            "fix": line if state in ("ready", "orphan") else "",
            "exit": line if state in ("ready", "open", "empty", "orphan", "paused") else ""}  # fmt: skip


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
    return _row(repo, path, state, _age(repo, name), name=name, kind=kind_of(name), ahead=ahead, dirty=changed)  # fmt: skip


def _strays(home: Path, folder: Path, listed: set[Path], ancestors: set[Path]) -> list[Path]:
    """The leaf folders under *folder* that no tree lists nor is an ancestor of one, a bare level
    folder of *home* aside: strays at any depth."""
    out: list[Path] = []
    for child in sorted(folder.glob("*")):
        here = child.resolve()
        if child.is_dir() and not is_link(child) and here not in listed:
            sub = _strays(home, child, listed, ancestors)
            out += sub if sub or here in ancestors or is_bare_level(home, child) else [child]
    return out


def _absent(root: Path, repo: Path, flow: dict[str, str], held: set[str], found: list[dict[str, object]]) -> list[dict[str, object]]:  # fmt: skip
    """The leftovers git does not list: a `wt/*` branch with no tree (`orphan`), and each stray
    folder under `worktrees/<repo>/` (`unregistered`), one row per path whose removal is its fix."""
    out = []
    home = tree_path(root, repo.name)
    live = work_versions(repo, flow)  # the one live work branch judges a merged orphan
    work = f"{flow['work']}{live[0]}" if len(live) == 1 else ""
    for ref in git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/wt/").split():
        if f"refs/heads/{ref}" not in held:
            name = ref.removeprefix("wt/")
            row = _row(repo, str(home / name), "orphan", kind=kind_of(name))
            # `merge` refuses a name off the grammar: git drops a branch HEAD holds; one with
            # commits of its own has no exit (the unpublished-branch rule of `context dead` owns
            # it) and a fix that waits on an agent
            if not name_of(ref):
                if work and (steps := drop_steps(repo, ref, work)):
                    line = act("agent", ", then ".join(steps))
                    row |= {"fix": line, "exit": line}
                else:
                    row |= {"fix": act("agent", f"land or archive the wt/* branch {ref}, then close again"), "exit": ""}  # fmt: skip
            out.append(row)
    listed = {Path(str(r["path"])).resolve() for r in (*found, *out)}
    ancestors = {p for path in listed for p in path.parents}
    return out + [
        _row(repo, str(stray), "unregistered")
        | {"fix": act("agent", f"remove the directory {stray}")}
        for stray in _strays(home, home, listed, ancestors)
    ]


def _repo_rows(root: Path, repo: Path, flow: dict[str, str]) -> list[dict[str, object]]:
    trees, mine = _trees(repo), {Path(r["path"]).resolve(): r["name"] for r in ours(repo)}
    out: list[dict[str, object]] = []
    for tree in trees:
        path, name = tree["worktree"], mine.get(Path(tree["worktree"]).resolve())
        if name is None:
            out.append(_row(repo, path, "foreign") | {"fix": act("agent", f"land the work of the linked worktree {path}, then remove it: no tree of this workspace")})  # fmt: skip
        elif not Path(path).is_dir():
            out.append(_row(repo, path, "orphan", name=name, kind=kind_of(name)))
        else:
            out.append(_ours(repo, flow, name, path))
    return out + _absent(root, repo, flow, {t.get("branch", "") for t in trees}, out)


def _unregistered(repo: Path, trees: list[dict[str, str]]) -> list[dict[str, object]]:
    """The linked trees of a repo no context owns: a finding whose one fix is the operator's act."""
    return [
        _row(repo, t["worktree"], "unregistered", registered=False)
        | {
            "fix": act(
                "agent",
                f"land the work of {t['worktree']}, then run "
                f"`{git_inline(repo, 'worktree', 'remove', '--force', '--force', t['worktree'])}`",
            )
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
