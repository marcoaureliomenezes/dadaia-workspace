#!/usr/bin/env python3
"""Read-only facts about the workspace's canonical worktrees: git (every child runs with
`GIT_*` scrubbed from its env) and the gitflow the CLI's context record carries (ADR 0144)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

from _worktree_kinds import _NAME_RE, LOCK, Refusal

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
    """One read-only run of the workspace CLI — the owner of every package grammar."""
    bins = (root / ".dadaia/.venv/bin/dadaia", root / ".dadaia/.venv/Scripts/dadaia.exe")
    exe = next((b for b in bins if b.exists()), None)
    if exe is None:
        raise Refusal(
            f"no workspace CLI under {root / '.dadaia/.venv'}", "uvx dadaia-workspace init"
        )
    return subprocess.run([str(exe), *args], cwd=root, env=_env(), capture_output=True, text=True)


def doctor(root: Path) -> str:
    return f"{root / '.dadaia/.venv/bin/dadaia'} doctor"


def gitflows(root: Path) -> dict[str, dict[str, str]]:
    """Each registered repo's gitflow `{principal, integration, work}`, read by the one
    reader through `context list --json` (ADR 0144); a repo whose record has none is absent."""
    done = cli(root, "context", "list", "--json")
    if done.returncode:
        raise Refusal(f"context list failed: {done.stderr.strip()}", doctor(root))
    return {
        repo: row["gitflow"]
        for row in json.loads(done.stdout)
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
    for name, flow in sorted(gitflows(root).items()):
        repo = root / "repos" / name
        for row in ours(repo) if (repo / ".git").exists() else []:
            tree = Path(row["path"])
            admin = Path(git(tree, "rev-parse", "--path-format=absolute", "--git-dir").strip())
            ahead = git(
                repo,
                "rev-list",
                "--count",
                f"{flow['work']}{row['v']}..wt/{tree.name}",
                check=False,
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
