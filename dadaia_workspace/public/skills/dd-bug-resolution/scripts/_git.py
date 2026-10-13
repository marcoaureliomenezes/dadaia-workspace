#!/usr/bin/env python3
"""The one git runner of the skill scripts: every child runs with the caller's repo-selecting `GIT_*` scrubbed from its env."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

#: `git rev-parse --local-env-vars` less the config injectors: what makes git answer for another repo. Identity, config and ssh are the caller's.
_LOCAL = frozenset({
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_INDEX_FILE", "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE", "GIT_PREFIX", "GIT_SHALLOW_FILE", "GIT_COMMON_DIR",
})  # fmt: skip


def scrubbed_env(parent: Mapping[str, str] | None = None) -> dict[str, str]:
    """A child env from *parent* (default `os.environ`): repo-selecting `GIT_*` out, bytecode off."""
    return {
        k: v for k, v in (os.environ if parent is None else parent).items() if k not in _LOCAL
    } | {"PYTHONDONTWRITEBYTECODE": "1"}


def git(repo: Path, *args: str, check: bool = True, input: str | None = None) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], env=scrubbed_env(), capture_output=True, text=True, encoding="utf-8", errors="replace", input=input
    )  # fmt: skip
    if check and done.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout


def parse_worktrees(text: str) -> list[dict[str, str]]:
    """Every linked worktree of a `worktree list --porcelain` *text* (the main checkout excluded)."""
    parsed = [
        dict(ln.partition(" ")[::2] for ln in b.splitlines() if ln) for b in text.split("\n\n")
    ]
    return [{**f, "worktree": str(Path(f["worktree"]))} for f in parsed if "worktree" in f][1:]
