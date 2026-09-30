#!/usr/bin/env python3
"""Read-only git facts about the workspace's canonical worktrees; every child runs with
`GIT_*` scrubbed from its env."""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from _worktree_kinds import _NAME_RE, LOCK, Refusal

_WORK_RE = re.compile(r"^feature/(\d+\.\d+\.\d+)$")
_TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def git(repo: Path, *args: str, check: bool = True) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    done = subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True, text=True)
    if check and done.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout


def find_root() -> Path:
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".dadaia" / "states" / "spec_contexts.json").is_file():
            return candidate
    raise Refusal("no workspace root above the cwd", "cd <workspace root>")


def work_version(repo: Path) -> str:
    branches = git(repo, "branch", "--list", "feature/*", "--format=%(refname:short)").split()
    versions = [m.group(1) for b in branches if (m := _WORK_RE.match(b))]
    if len(versions) == 1:
        return versions[0]
    if versions:
        stale = sorted(versions, key=lambda v: tuple(map(int, v.split("."))))[0]
        raise Refusal(f"{len(versions)} work branches", f"git -C {repo} branch -d feature/{stale}")
    tags = [
        tuple(map(int, m.groups())) for t in git(repo, "tag").split() if (m := _TAG_RE.match(t))
    ]
    major, minor, patch = max(tags, default=(0, 0, 0))
    nxt = f"{major}.{minor}.{patch + 1}" if tags else "0.1.0"
    raise Refusal("no work branch feature/<M.m.p>", f"git -C {repo} branch feature/{nxt} main")


def ours(repo: Path) -> list[dict[str, str]]:
    """Our `dadaia:`-locked worktrees of *repo*, from `git worktree list --porcelain`."""
    rows: list[dict[str, str]] = []
    for block in git(repo, "worktree", "list", "--porcelain").split("\n\n"):
        fields = dict(line.partition(" ")[::2] for line in block.splitlines() if line)
        reason = fields.get("locked", "")
        if reason.startswith(LOCK) and (m := _NAME_RE.match(Path(fields["worktree"]).name)):
            rows.append(
                {"path": fields["worktree"], "kind": m["k"], "id": m["v"] + m["l"], "v": m["v"]}
            )
    return rows


def rows(root: Path) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for repo in sorted(p for p in (root / "repos").iterdir() if (p / ".git").exists()):
        for row in ours(repo):
            tree = Path(row["path"])
            admin = Path(git(tree, "rev-parse", "--path-format=absolute", "--git-dir").strip())
            ahead = git(
                repo, "rev-list", "--count", f"feature/{row['v']}..wt/{tree.name}", check=False
            )
            out.append(
                {
                    "repo": repo.name,
                    "path": row["path"],
                    "kind": row["kind"],
                    "id": row["id"],
                    "age_hours": round(
                        (time.time() - (admin / "locked").stat().st_mtime) / 3600, 1
                    ),
                    "ahead": int(ahead or 0),
                    "dirty": bool(git(tree, "status", "--porcelain").strip()),
                }
            )
    return out
