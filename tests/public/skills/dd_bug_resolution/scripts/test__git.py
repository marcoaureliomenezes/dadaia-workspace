"""The one git runner and the one ``Refusal`` of ``dd-bug-resolution/scripts``.

* ``_git.py`` public names: ``git(repo, *args, check=True, input=None) -> str`` and
  ``parse_worktrees(text) -> list[dict[str, str]]``.
* ``git`` runs ``git -C <repo> <args>`` with every ``GIT_*`` variable of the caller removed
  so a caller's ``GIT_DIR`` or ``GIT_WORK_TREE`` never redirects it; stdout on success;
  ``RuntimeError("git <args>: <stderr>")`` on a non-zero exit when ``check`` (``check=False``
  returns stdout unchecked).
* ``git_bytes(repo, *args, input=None, timeout=None, env=None) -> CompletedProcess[bytes]`` is
  the byte-level twin on the same scrubbed env (*env* overrides on top): unchecked, stderr as
  bytes, ``subprocess.TimeoutExpired`` and ``OSError`` raised as they are.
* ``parse_worktrees(text)`` takes ``git worktree list --porcelain`` text and returns the LINKED
  worktrees, main checkout excluded, one dict per block in git's order: each ``key value`` line
  is ``key -> value``, a bare flag line (``locked``, ``detached``) is ``key -> ""``, and
  ``worktree`` is ``str(Path(value))``.
* ``_refusal.py`` holds ``Refusal(message, fix="")`` (``Exception``; ``.fix``) once; every
  skill raises and catches that one class.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import run, write_text

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
    run(["git", *args], cwd=cwd, env=_clean(), check=True)


def _repo(path: Path) -> Path:
    path.mkdir()
    _sh("init", "-q", "-b", "main", cwd=path)
    write_text(path / "f.txt", "published\n")
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
    assert Path(git(a, "rev-parse", "--show-toplevel").strip()) == a.resolve()


def test_the_scrub_drops_repo_selectors_and_keeps_the_callers_identity_and_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in ("GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_AUTHOR_NAME", "GIT_CONFIG_GLOBAL"):
        monkeypatch.setenv(key, "x")
    kept = load_owner("dd-bug-resolution", "_git").scrubbed_env()
    assert {"GIT_INDEX_FILE", "GIT_COMMON_DIR"}.isdisjoint(kept)
    assert {"GIT_AUTHOR_NAME", "GIT_CONFIG_GLOBAL"} <= set(kept)


def test_the_scrubbed_env_marks_the_child_as_a_worktree_tool_and_still_drops_repo_selectors() -> (
    None
):
    kept = load_owner("dd-bug-resolution", "_git").scrubbed_env(
        {"GIT_DIR": "x", "GIT_WORK_TREE": "y", "HOME": "h"}
    )
    assert {k: kept[k] for k in ("DADAIA_WT",)} == {"DADAIA_WT": "1"}
    assert {"GIT_DIR", "GIT_WORK_TREE"}.isdisjoint(kept)


def test_git_bytes_returns_the_raw_bytes_and_the_exit_status_unchecked(tmp_path: Path) -> None:
    git_bytes = load_owner("dd-bug-resolution", "_git").git_bytes
    repo = _repo(tmp_path / "r")
    done = git_bytes(repo, "hash-object", "--stdin", input=b"hello\n")
    assert (done.returncode, done.stdout) == (0, b"ce013625030ba8dba906f756967f9e9ca394464a\n")
    failed = git_bytes(repo, "cat-file", "-e", "f" * 40)
    assert failed.returncode != 0
    assert isinstance(failed.stderr, bytes)


def test_git_bytes_answers_for_its_repo_not_the_callers_git_env(leaked: tuple[Path, Path]) -> None:
    a, _ = leaked
    done = load_owner("dd-bug-resolution", "_git").git_bytes(a, "rev-parse", "--show-toplevel")
    assert Path(done.stdout.decode().strip()) == a.resolve()


def test_the_git_bytes_child_env_is_the_scrubbed_one_plus_the_callers_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_INDEX_FILE", "x")
    monkeypatch.setenv("GIT_COMMON_DIR", "y")
    repo = _repo(tmp_path / "r")
    done = load_owner("dd-bug-resolution", "_git").git_bytes(
        repo, "-c", "alias.dump=!env", "dump", env={"DUMP_PROBE": "on"}
    )
    child = set(done.stdout.decode().splitlines())
    assert {"DADAIA_WT=1", "DUMP_PROBE=on"} <= child
    assert not [k for k in child if k.startswith(("GIT_INDEX_FILE=", "GIT_COMMON_DIR="))]


def test_git_bytes_raises_the_timeout_it_was_given(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "r")
    with pytest.raises(subprocess.TimeoutExpired):
        load_owner("dd-bug-resolution", "_git").git_bytes(
            repo, "-c", "alias.nap=!sleep 5", "nap", timeout=0.2
        )


def test_the_scrubbed_env_forbids_bytecode_even_when_the_parent_allows_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "0")
    assert load_owner("dd-bug-resolution", "_git").scrubbed_env()["PYTHONDONTWRITEBYTECODE"] == "1"


def test_a_child_python_on_the_scrubbed_env_writes_no_bytecode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "0")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    write_text(pkg / "__init__.py", "X = 1\n")
    env = load_owner("dd-bug-resolution", "_git").scrubbed_env() | {"PYTHONPATH": str(tmp_path)}
    done = run([sys.executable, "-c", "import pkg"], env=env, cwd=tmp_path, check=False)  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert list(tmp_path.rglob("__pycache__")) == []


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
        {"worktree": str(Path("/w/worktrees/repo/a")), "HEAD": "2" * 40, "branch": "refs/heads/wt/a", "locked": ""},
        {"worktree": str(Path("/w/worktrees/repo/b")), "HEAD": "3" * 40, "detached": "", "locked": "reason text"},
    ]  # fmt: skip
    assert parse("worktree /w/repo\nHEAD " + "1" * 40 + "\n") == []


def test_one_refusal_class_for_every_import_path() -> None:
    refusal: ModuleType = load_owner("dd-bug-resolution", "_refusal")
    assert refusal.Refusal is load_owner("dd-bug-resolution", "_bugs_store").Refusal
    err = refusal.Refusal("m", "fix: x")
    assert (str(err), err.fix) == ("m", "fix: x")


def test_main_checkout_of_a_linked_worktree_and_of_its_main_checkout_answer_alike(
    tmp_path: Path,
) -> None:
    main = _repo(tmp_path / "A")
    linked = tmp_path / "linked"
    _sh("worktree", "add", "-q", "-b", "wt/x", str(linked), cwd=main)
    main_checkout = load_owner("dd-bug-resolution", "_git").main_checkout
    assert main_checkout(main) == main.resolve()
    assert main_checkout(linked) == main.resolve()


def test_main_checkout_of_a_path_that_is_no_repository_is_the_current_directory(
    tmp_path: Path,
) -> None:
    main_checkout = load_owner("dd-bug-resolution", "_git").main_checkout
    assert main_checkout(tmp_path) == Path(".")


def test_fix_commit_returns_the_older_of_two_same_subject_fixes_when_the_newer_is_reverted(
    tmp_path: Path,
) -> None:
    repo, line = _repo(tmp_path / "R"), "fix(bugs): b1 — c"
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    for subject in (line, line, f'Revert "{line}"'):
        _sh(*ident, "commit", "-q", "--allow-empty", "-m", subject, cwd=repo)
    older = run(["git", "rev-parse", "HEAD~2"], cwd=repo, env=_clean(), check=True).stdout.strip()
    found = load_owner("dd-bug-resolution", "_git").fix_commit([repo], ["b1"])
    assert found == {"b1": (repo, older)}
