#!/usr/bin/env python3
"""The one git runner of the skill scripts: every child runs with the caller's repo-selecting `GIT_*` scrubbed from its env."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path

from _grammar import SHA_RE
from _platform import run

#: `git rev-parse --local-env-vars` less the config injectors: what makes git answer for another repo. Identity, config and ssh are the caller's.
_LOCAL = frozenset({
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_INDEX_FILE", "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE", "GIT_PREFIX", "GIT_SHALLOW_FILE", "GIT_COMMON_DIR",
})  # fmt: skip


def scrubbed_env(parent: Mapping[str, str] | None = None) -> dict[str, str]:
    """A child env from *parent* (default `os.environ`): repo-selecting `GIT_*` out, bytecode off, `DADAIA_WT` marked."""
    return {
        k: v for k, v in (os.environ if parent is None else parent).items() if k not in _LOCAL
    } | {"PYTHONDONTWRITEBYTECODE": "1", "DADAIA_WT": "1"}


class GitError(RuntimeError):
    """A git command that exited non-zero; *stderr* is git's own text."""

    def __init__(self, args: tuple[str, ...], stderr: str) -> None:
        super().__init__(f"git {' '.join(args)}: {stderr}")
        self.stderr = stderr


def git(repo: Path, *args: str, check: bool = True, input: str | None = None) -> str:
    done = run(["git", "-C", str(repo), *args], env=scrubbed_env(), input=input)
    if check and done.returncode:
        raise GitError(args, done.stderr.strip())
    return done.stdout


def shallow(repo: Path) -> bool:
    """Whether *repo* is a shallow clone: its history is cut."""
    return git(repo, "rev-parse", "--is-shallow-repository", check=False).strip() == "true"


def main_checkout(repo: Path) -> Path:
    """The parent of the git common dir of *repo* (a linked worktree resolves to its main checkout); `Path(".")` when *repo* is no repository."""
    try:
        common = git(repo, "rev-parse", "--git-common-dir")
    except GitError:
        return Path(".")
    return (repo / common.strip()).resolve().parent


def reaches(repo: Path, sha: str) -> bool:
    """Whether *sha*, a hex sha, is an ancestor of the HEAD of *repo*; git is never asked about anything else."""
    if not SHA_RE.fullmatch(sha or ""):
        return False
    try:
        git(repo, "merge-base", "--is-ancestor", sha, "HEAD")
    except GitError:
        return False
    return True


def reached(repo: Path) -> set[str]:
    """Every full sha the HEAD of *repo* reaches, in one `rev-list`; a malformed sha is never in it."""
    return set(git(repo, "rev-list", "HEAD", check=False).split())


def fix_files(repo: Path, shas: Iterable[str]) -> dict[str, list[str]]:
    """The paths each of *shas* touched, all read in one `diff-tree`; a sha that is malformed or that the HEAD of *repo* does not reach is absent."""
    asked = reached(repo).intersection(shas)
    found: dict[str, list[str]] = {}
    files: list[str] = []
    cmd = ("diff-tree", "--stdin", "--root", "--name-only", "-r", "-z")
    for token in git(repo, *cmd, input="\n".join(asked) + "\n").split("\0") if asked else []:
        if token in asked:
            files = found.setdefault(token, [])
        elif token:
            files.append(token)
    return found


def parse_worktrees(text: str) -> list[dict[str, str]]:
    """Every linked worktree of a `worktree list --porcelain` *text* (the main checkout excluded)."""
    parsed = [
        dict(ln.partition(" ")[::2] for ln in b.splitlines() if ln) for b in text.split("\n\n")
    ]
    return [{**f, "worktree": str(Path(f["worktree"]))} for f in parsed if "worktree" in f][1:]
