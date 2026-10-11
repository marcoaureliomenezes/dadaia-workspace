#!/usr/bin/env python3
"""The one git runner of the skill scripts: every child runs with the caller's `GIT_*` scrubbed from its env."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(repo: Path, *args: str, check: bool = True, input: str | None = None) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], env=_env(), capture_output=True, text=True, encoding="utf-8", errors="replace", input=input
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
