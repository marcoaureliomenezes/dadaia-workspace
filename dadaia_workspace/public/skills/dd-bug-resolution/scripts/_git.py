#!/usr/bin/env python3
"""The one git runner of the skill scripts: every child runs with the caller's repo-selecting `GIT_*` scrubbed from its env."""

from __future__ import annotations

import os
import re
import subprocess
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path

from _grammar import SHA_RE
from _platform import run, run_bytes

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
    """A git command that exited non-zero; *stderr* is git's own text, *argv* the command that failed."""

    def __init__(self, args: tuple[str, ...], stderr: str, repo: Path | None = None) -> None:
        super().__init__(f"git {' '.join(args)}: {stderr}")
        self.stderr = stderr
        self.argv = ("git", *(("-C", str(repo)) if repo else ()), *args)


def git(repo: Path, *args: str, check: bool = True, input: str | None = None) -> str:
    done = run(["git", "-C", str(repo), *args], env=scrubbed_env(), input=input)
    if check and done.returncode:
        raise GitError(args, done.stderr.strip(), repo)
    return done.stdout


def git_bytes(
    repo: Path,
    *args: str,
    input: bytes | None = None,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """`git -C repo args` on the scrubbed env plus *env*: raw bytes, the exit status unchecked; a missing git raises `OSError`, a run past *timeout* `subprocess.TimeoutExpired`."""
    return run_bytes(
        ["git", "-C", str(repo), *args],
        env=scrubbed_env() | dict(env or {}),
        input=input,
        timeout=timeout,
    )


def shallow(repo: Path) -> bool:
    """Whether *repo* is a shallow clone: its history is cut."""
    return git(repo, "rev-parse", "--is-shallow-repository", check=False).strip() == "true"


def main_checkout(repo: Path) -> Path:
    """The parent of the git common dir of *repo* (a linked worktree resolves to its main checkout). Raises `GitError` when *repo* is no repository."""
    return (repo / git(repo, "rev-parse", "--git-common-dir").strip()).resolve().parent


def reaches(repo: Path, sha: str) -> bool:
    """Whether *sha*, a hex sha, is an ancestor of the HEAD of *repo*; git is never asked about anything else."""
    if not SHA_RE.fullmatch(sha or ""):
        return False
    try:
        git(repo, "merge-base", "--is-ancestor", sha, "HEAD")
    except GitError:
        return False
    return True


#: A bug-fix line of a commit message: `fix(bugs): <id>[, <id>…] — …` or the REBUILD `refactor(bugs): …`.
_FIX_LINE = re.compile(r"^(?:fix|refactor)\(bugs\): (.*?) — ", re.M)


def _canon(subject: str) -> str:
    """A subject with git's `Reapply "S"` spelled as the `Revert "Revert "S""` it stands for."""
    return f'Revert "Revert "{subject[9:]}"' if subject.startswith('Reapply "') else subject


def fix_commit(repos: Iterable[Path], ids: Iterable[str]) -> dict[str, tuple[Path, str]]:
    """For each of *ids*, the repo and sha of the newest commit whose message holds a bug-fix line naming it (a group lists its ids separated by commas or blanks), that the HEAD of a repo of *repos* reaches; each repo is pulled and read in one `git log` only while an id is missing. A commit subjected `Revert "<S>"` retires exactly one older commit subjected `<S>`, the nearest, and a retired revert registers nothing."""
    wanted, found = set(ids), dict[str, tuple[Path, str]]()
    for each in repos if wanted else ():
        retired = Counter[str]()
        for entry in git(each, "log", "--format=%x1e%H%x00%B", check=False).split("\x1e")[1:]:
            sha, _, message = entry.partition("\0")
            subject = _canon(message.partition("\n")[0])
            if retired[subject]:
                retired[subject] -= 1
                continue
            if subject.startswith('Revert "'):
                retired[_canon(subject[8:-1])] += 1
            for head in _FIX_LINE.findall(message):
                for bug in re.split(r"[,\s]+", head):
                    if bug in wanted:
                        found.setdefault(bug, (each, sha))
        if wanted <= found.keys():  # after the body: the next repo is not even pulled
            break
    return found


def fix_files(repo: Path, shas: Iterable[str]) -> dict[str, list[str]]:
    """The paths each of *shas*, commits of *repo*, touched, all read in one `diff-tree`."""
    asked = set(shas)
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
