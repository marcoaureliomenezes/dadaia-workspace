"""The worktree fixtures write their non-ASCII text as UTF-8 whatever the host's default encoding
(Windows writes cp1252), because the product's checks read strict UTF-8.
Size: MEDIUM (real git, tmp workspace).
"""

from __future__ import annotations

import pathlib

import pytest

from tests.helpers.worktree_ws import commit, make_workspace

_write_text = pathlib.Path.write_text


@pytest.fixture
def cp1252_default(monkeypatch: pytest.MonkeyPatch) -> None:
    def write_text(self, data, encoding=None, errors=None, newline=None):  # type: ignore[no-untyped-def]
        return _write_text(self, data, encoding or "cp1252", errors, newline)

    monkeypatch.setattr(pathlib.Path, "write_text", write_text)


def test_the_plan_fixture_is_utf8_on_a_cp1252_host(
    cp1252_default: None, tmp_path: pathlib.Path
) -> None:
    root = make_workspace(tmp_path)
    plan = root / "repos/r/specs/releases/0.5.0/rc-1/PLAN.md"
    assert "| Job 1 | 1 | — |" in plan.read_text(encoding="utf-8")


def test_commit_writes_its_text_as_utf8_on_a_cp1252_host(
    cp1252_default: None, tmp_path: pathlib.Path
) -> None:
    root = make_workspace(tmp_path)
    commit(root / "repos/r", "a.md", "a — b\n")
    assert (root / "repos/r/a.md").read_text(encoding="utf-8") == "a — b\n"
