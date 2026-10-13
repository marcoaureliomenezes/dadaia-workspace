"""The one git runner of ``dd-bug-resolution/scripts``.

Contract:

* ``_git.py`` public names: ``git(repo, *args, check=True, input=None) -> str`` and
  ``parse_worktrees(text) -> list[dict[str, str]]``.
* ``git`` runs ``git -C <repo> <args>`` with every ``GIT_*`` variable of the caller removed
  so a caller's ``GIT_DIR`` or ``GIT_WORK_TREE``
  never redirects it; stdout on success; ``RuntimeError("git <args>: <stderr>")`` on a non-zero
  exit when ``check`` (``check=False`` returns stdout unchecked). ``_ledger._published_text``
  calls it instead of its private ``subprocess`` runner.
* ``parse_worktrees(text)`` takes ``git worktree list --porcelain`` text and returns the LINKED
  worktrees, main checkout excluded, one dict per block in git's order: each ``key value`` line
  is ``key -> value``, a bare flag line (``locked``, ``detached``) is ``key -> ""``, and
  ``worktree`` is ``str(Path(value))``. ``_worktree_git._trees`` and
  ``git_subprocess.unrecoverable`` both read it.
* ``_refusal.py`` holds ``Refusal(message, fix="")`` (``Exception``; ``.fix``) once; ``_bugs_store``
  imports that class, so every skill raises and catches one object.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

from dadaia_workspace.core.skill_owner import load_owner

_PORCELAIN = (
    "worktree /w/repo\nHEAD 1111111111111111111111111111111111111111\nbranch refs/heads/main\n\n"
    "worktree /w/worktrees/repo/a\nHEAD 2222222222222222222222222222222222222222\n"
    "branch refs/heads/wt/a\nlocked\n\n"
    "worktree /w/worktrees/repo/b\nHEAD 3333333333333333333333333333333333333333\n"
    "detached\nlocked reason text\n"
)


def _clean() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _sh(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, env=_clean(), check=True, capture_output=True)


def _repo(path: Path) -> Path:
    path.mkdir()
    _sh("init", "-q", "-b", "main", cwd=path)
    (path / "f.txt").write_text("published\n", encoding="utf-8")
    _sh("add", "f.txt", cwd=path)
    _sh("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c", cwd=path)
    return path


@pytest.fixture
def leaked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Repo A, with the environment of a hook running inside repo B."""
    a, b = _repo(tmp_path / "A"), _repo(tmp_path / "B")
    monkeypatch.setenv("GIT_DIR", str(b / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(b))
    return a, b


def test_git_answers_for_its_repo_not_the_callers_git_env(leaked: tuple[Path, Path]) -> None:
    a, _ = leaked
    git = load_owner("dd-bug-resolution", "_git").git
    assert git(a, "rev-parse", "--show-toplevel").strip() == str(a.resolve())


def test_the_scrub_drops_repo_selectors_and_keeps_the_callers_identity_and_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in ("GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_AUTHOR_NAME", "GIT_CONFIG_GLOBAL"):
        monkeypatch.setenv(key, "x")
    kept = load_owner("dd-bug-resolution", "_git").scrubbed_env()
    assert {"GIT_INDEX_FILE", "GIT_COMMON_DIR"}.isdisjoint(kept)
    assert {"GIT_AUTHOR_NAME", "GIT_CONFIG_GLOBAL"} <= set(kept)


def test_ledger_published_text_reads_its_repo_not_the_callers_git_env(
    leaked: tuple[Path, Path], tmp_path: Path
) -> None:
    a, _ = leaked
    origin = tmp_path / "origin.git"
    _sh("init", "-q", "--bare", str(origin), cwd=tmp_path)
    _sh("remote", "add", "origin", str(origin), cwd=a)
    _sh("push", "-q", "origin", "main", cwd=a)
    ledger = load_owner("dd-bug-resolution", "_ledger")
    assert ledger._published_text(a / "f.txt") == "published\n"


def test_git_failure_raises_and_check_false_returns_stdout(tmp_path: Path) -> None:
    a = _repo(tmp_path / "A")
    git = load_owner("dd-bug-resolution", "_git").git
    with pytest.raises(RuntimeError, match="git rev-parse --verify nope"):
        git(a, "rev-parse", "--verify", "nope")
    assert git(a, "rev-parse", "--verify", "nope", check=False) == ""


def test_parse_worktrees_returns_the_linked_rows() -> None:
    parse = load_owner("dd-bug-resolution", "_git").parse_worktrees
    assert parse(_PORCELAIN) == [
        {"worktree": "/w/worktrees/repo/a", "HEAD": "2" * 40, "branch": "refs/heads/wt/a", "locked": ""},
        {"worktree": "/w/worktrees/repo/b", "HEAD": "3" * 40, "detached": "", "locked": "reason text"},
    ]  # fmt: skip
    assert parse("worktree /w/repo\nHEAD " + "1" * 40 + "\n") == []


def test_one_refusal_class_for_every_import_path() -> None:
    refusal: ModuleType = load_owner("dd-bug-resolution", "_refusal")
    assert refusal.Refusal is load_owner("dd-bug-resolution", "_bugs_store").Refusal
    err = refusal.Refusal("m", "fix: x")
    assert (str(err), err.fix) == ("m", "fix: x")
