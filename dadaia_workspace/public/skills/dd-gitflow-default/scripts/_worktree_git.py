#!/usr/bin/env python3
"""Read-only facts about the workspace's canonical worktrees: git (every child runs with
`GIT_*` scrubbed from its env) and the gitflow the CLI's context record carries (ADR 0144)."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

from _worktree_kinds import _NAME_RE, SCRIPT, Refusal

_TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(repo: Path, *args: str, check: bool = True) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], env=_env(), capture_output=True, text=True
    )
    if check and done.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout


def find_root() -> Path:
    """The workspace above the cwd, else above this script (it is projected inside one)."""
    for start in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        for candidate in (start, *start.parents):
            if (candidate / ".dadaia" / "states" / "spec_contexts.json").is_file():
                return candidate
    raise Refusal("no workspace root above the cwd or this script", "uvx dadaia-workspace init")


def cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """One read-only run of the workspace CLI — the owner of every package grammar: the
    venv's entry point, else the package the running interpreter carries (a sandbox)."""
    bins = (root / ".dadaia/.venv/bin/dadaia", root / ".dadaia/.venv/Scripts/dadaia.exe")
    exe = next(
        ([str(b)] for b in bins if b.exists()), [sys.executable, "-m", "dadaia_workspace.cli.main"]
    )
    run = subprocess.run  # stdin closed: a CLI never waits on the caller's pipe
    return run(
        [*exe, *args],
        cwd=root,
        env=_env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )


def doctor(root: Path) -> str:
    return f"{root / '.dadaia/.venv/bin/dadaia'} doctor"


def gitflows(root: Path) -> dict[str, dict[str, str]]:
    """Each registered repo's gitflow `{principal, integration, work}`, read by the one
    reader through `context list --json` (ADR 0144); a repo whose record has none is absent."""
    done = cli(root, "context", "list", "--json")
    try:
        listed = json.loads(done.stdout) if not done.returncode else None
    except ValueError:
        listed = None
    if not isinstance(listed, list):
        raise Refusal(
            f"context list failed: {done.stderr.strip() or done.stdout.strip()}", doctor(root)
        )
    return {
        repo: row["gitflow"]
        for row in listed
        if row.get("gitflow")
        for repo in (row["main_repo"], *(a["slug"] for a in row["associated_repos"]))
    }


def flow_for(root: Path, repo: Path) -> dict[str, str]:
    flow = gitflows(root).get(repo.name)
    if flow is None:
        raise Refusal(f"no context on disk owns repos/{repo.name}", doctor(root))
    return flow


def work_version(repo: Path, flow: dict[str, str]) -> str:
    prefix = flow["work"]
    work_re = re.compile(rf"^{re.escape(prefix)}(\d+\.\d+\.\d+)$")
    branches = git(repo, "branch", "--list", f"{prefix}*", "--format=%(refname:short)").split()
    versions = [m.group(1) for b in branches if (m := work_re.match(b))]
    if len(versions) == 1:
        return versions[0]
    if versions:
        stale = sorted(versions, key=lambda v: tuple(map(int, v.split("."))))[0]
        raise Refusal(f"{len(versions)} work branches", f"git -C {repo} branch -d {prefix}{stale}")
    tags = [
        tuple(map(int, m.groups())) for t in git(repo, "tag").split() if (m := _TAG_RE.match(t))
    ]
    major, minor, patch = max(tags, default=(0, 0, 0))
    nxt = f"{major}.{minor}.{patch + 1}" if tags else "0.1.0"
    raise Refusal(
        f"no work branch {prefix}<M.m.p>",
        f"git -C {repo} branch {prefix}{nxt} {flow['integration']}",
    )


def _trees(repo: Path) -> list[dict[str, str]]:
    """Every linked worktree of *repo* (the main checkout excluded), from git's porcelain."""
    blocks = git(repo, "worktree", "list", "--porcelain").split("\n\n")
    parsed = [dict(ln.partition(" ")[::2] for ln in b.splitlines() if ln) for b in blocks]
    return [fields for fields in parsed if "worktree" in fields][1:]


def ours(repo: Path) -> list[dict[str, str]]:
    """Our worktrees of *repo*: any tree on a canonical `wt/<M.m.p><l>-<kind>` branch, locked
    or not — merge's own re-attach leaves one unlocked."""
    return [
        {"path": t["worktree"], "kind": m["k"], "id": m["v"] + m["l"], "v": m["v"], "name": m[0]}
        for t in _trees(repo)
        if (m := _NAME_RE.match(t.get("branch", "").removeprefix("refs/heads/wt/")))
    ]


def _row(repo: Path, path: str, state: str, age: float = 0.0, **facts: object) -> dict[str, object]:
    """One worktree: WARN past a day or off-canon; `fix` shown only when ready or orphan;
    `exit`, the line a hold names — `clean` for an empty tree, else `merge` (ADR 0128)."""
    verb = "clean" if state == "empty" else "merge"
    line = shlex.join(["python3", str(SCRIPT), verb, path])
    return {"repo": repo.name, "path": path, "state": state, "age_hours": age, **facts,
            "warn": state not in ("ready", "open", "empty") or age > 24,
            "fix": line if state in ("ready", "orphan") else "",
            "exit": line if state in ("ready", "open", "empty", "orphan") else ""}  # fmt: skip


def rows(root: Path) -> list[dict[str, object]]:
    """Every worktree fact of every registered repo, read from git alone (ADR 0108):
    ours `ready` (ahead, clean), `open` (ahead, dirty) or `empty`, an `orphan` wt/* with no tree, a `foreign`
    worktree git registers (harness-native, hand-made, under a TTL zone), and an
    `unregistered` directory under `worktrees/<repo>/`."""
    out: list[dict[str, object]] = []
    for name, flow in sorted(gitflows(root).items()):
        repo = root / "repos" / name
        if not (repo / ".git").exists():
            continue
        trees, mine = _trees(repo), {Path(r["path"]).resolve(): r for r in ours(repo)}
        for tree in trees:
            path = tree["worktree"]
            if (row := mine.get(Path(path).resolve())) is None:
                out.append(_row(repo, path, "foreign"))
                continue
            span = f"{flow['work']}{row['v']}..wt/{row['name']}"
            ahead = int(git(repo, "rev-list", "--count", span, check=False) or 0)
            dirty = bool(git(Path(path), "status", "--porcelain").strip())
            born = git(
                repo,
                "reflog",
                "show",
                "--date=unix",
                "--format=%gd",
                f"wt/{row['name']}",
                check=False,
            )
            stamps = re.findall(r"@\{(\d+)\}", born) or [str(int(time.time()))]
            age = round((time.time() - int(stamps[-1])) / 3600, 1)  # the branch's birth
            state = "empty" if not ahead else "ready" if not dirty else "open"
            out.append(
                _row(
                    repo, path, state, age, kind=row["kind"], id=row["id"], ahead=ahead, dirty=dirty
                )
            )
        held = {t.get("branch", "") for t in trees}
        for branch in git(
            repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/wt/"
        ).split():
            if f"refs/heads/{branch}" not in held and _NAME_RE.match(branch[3:]):
                out.append(_row(repo, str(root / "worktrees" / name / branch[3:]), "orphan"))
        listed = {Path(t["worktree"]).resolve() for t in trees}
        for stray in sorted((root / "worktrees" / name).glob("*")):
            if stray.is_dir() and stray.resolve() not in listed:
                out.append(_row(repo, str(stray), "unregistered"))
    return out
