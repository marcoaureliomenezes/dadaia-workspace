"""The fold of the push gate's remedy, on real git in a tmp repo.

The module's own arguments: the git client and object reader the container builds, and a
``decide(repo, held)`` that answers what the gate lists.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.container import build_git_client, build_git_object_reader
from dadaia_workspace.features.chokepoints import Decision
from tests.fixtures.real_git import PushRepo, git
from tests.helpers.oslib import write_text

_MODULE = "dadaia_workspace.features.chokepoints.fold"
_LEAK = "zz-secret-term"


@pytest.fixture()
def repo(tmp_path: Path) -> PushRepo:
    pushed = PushRepo(tmp_path)
    pushed.commit({"README.md": "init\n"}, "init")
    pushed.publish()
    return pushed


def _rewrite(repo: PushRepo, oldest: str, message: str | None, listed: set[str]) -> Any:
    fold = importlib.import_module(_MODULE)
    return fold.rewrite_unpublished(
        repo.path,
        oldest,
        message,
        git=build_git_client(),
        reader=build_git_object_reader(),
        decide=lambda _repo, _held: Decision(False, listed=frozenset(listed)),
    )


def _count(repo: PushRepo) -> int:
    return int(git(repo.path, "rev-list", "--count", "origin/feature/0.0.1..HEAD"))


def _leak_then_other(repo: PushRepo) -> str:
    first = repo.commit({"leak.txt": f"a {_LEAK}\n"}, "fix(x): first message")
    repo.commit({"other.txt": "b\n"}, "chore(x): second message")
    write_text(repo.path / "leak.txt", "a\n")
    return first


def test_the_subject_is_the_message_whenever_given_and_the_gate_lists_no_message(
    repo: PushRepo,
) -> None:
    oldest = _leak_then_other(repo)
    _rewrite(repo, oldest, "looks reviewed", {"leak.txt"})
    assert _count(repo) == 1
    assert git(repo.path, "log", "-1", "--format=%s") == "looks reviewed"


def test_every_folded_message_stays_in_the_body_under_the_given_subject(repo: PushRepo) -> None:
    oldest = _leak_then_other(repo)
    _rewrite(repo, oldest, "looks reviewed", {"leak.txt"})
    assert git(repo.path, "log", "-1", "--format=%B") == (
        "looks reviewed\n\nfix(x): first message\n\nchore(x): second message"
    )


def test_a_mixed_range_makes_a_test_commit_then_the_rest(repo: PushRepo) -> None:
    oldest = repo.commit({"src/a.py": f"x = '{_LEAK}'\n"}, "fix(x): the fix")
    repo.commit({"tests/t.py": "assert True\n"}, "test(x): the red")
    write_text(repo.path / "src/a.py", "x = ''\n")
    _rewrite(repo, oldest, None, {"src/a.py"})
    assert _count(repo) == 2
    assert git(repo.path, "log", "--reverse", "--format=%s", "origin/feature/0.0.1..HEAD") == (
        "test(x): the red\nfix(x): the fix"
    )
    assert git(repo.path, "show", "--name-only", "--format=", "HEAD~1") == "tests/t.py"
    assert "leak" not in git(repo.path, "show", "HEAD:src/a.py")


def test_a_failed_fold_leaves_head_where_it_was(repo: PushRepo) -> None:
    oldest = _leak_then_other(repo)
    write_text(repo.path / "stray.txt", "x\n")
    git(repo.path, "add", "stray.txt")
    before = git(repo.path, "rev-parse", "HEAD")
    fold = importlib.import_module(_MODULE)
    with pytest.raises(fold.FoldRefusal) as refused:
        _rewrite(repo, oldest, None, {"leak.txt"})
    assert refused.value.fix
    assert git(repo.path, "rev-parse", "HEAD") == before


def test_the_module_imports_no_typer() -> None:
    spec = importlib.util.find_spec(_MODULE)
    assert spec is not None and spec.origin
    tree = ast.parse(Path(spec.origin).read_text(encoding="utf-8"))
    roots = {
        (n.module or "").split(".")[0] if isinstance(n, ast.ImportFrom) else a.name.split(".")[0]
        for n in ast.walk(tree)
        if isinstance(n, ast.Import | ast.ImportFrom)
        for a in (getattr(n, "names", None) or [n])
    }
    assert "typer" not in roots
