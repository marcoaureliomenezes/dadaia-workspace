"""Wiring the specs/ canon scan into ``push_gate_decision`` (v0.5.0 specs-canon
closure, operator ruling 2026-08-28).

Intent: CONTRACT — v0.5.0 specs-canon closure

Every range is a real git range read by the real ``GitSubprocessObjectReader`` (AC9.4).
Covers: canon paths pass; a stray/non-canon path in the range refuses (naming the fix
hint); a non-canon path already published never blocks; the scan reaches every
non-deletion ref (tags included), never a deletion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from tests.fakes import gate_fixes
from tests.fixtures.real_git import ZERO, PushRepo


@pytest.fixture()
def repo(tmp_path: Path) -> PushRepo:
    return PushRepo(tmp_path)


def _decide(repo: PushRepo, line: str) -> Any:
    return push_gate_decision(
        parse_push_stdin(line)[0],
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=GitSubprocessObjectReader(),
        repo=repo.path,
        canon_violations_fn=canon_violations,
    )


_TAG = "refs/tags/v9.9.9 {sha} refs/tags/v9.9.9 " + ZERO
_BRANCH = "refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {remote}"
_DELETION = f"refs/heads/feature/0.0.1 {ZERO} refs/heads/feature/0.0.1 {'a' * 40}"


# fmt: off
@pytest.mark.parametrize(("published", "files", "line", "refused"), [
    pytest.param(None, {"specs/AGENTS.md": "# a\n", "specs/backlog/BACKLOG.json": "{}\n"}, _BRANCH, None, id="canon-tree-passes"),
    pytest.param(None, {"specs/AGENTS.md": "# a\n", "specs/backlog/loose-entry.md": "x\n"}, _BRANCH, "specs/backlog/loose-entry.md", id="non-canon-refuses"),
    pytest.param({"specs/_archive/legacy/SPEC.md": "x\n", "specs/backlog/candidates.md": "x\n"},
                 {"specs/memory/product/atom.md": "x\n", "README.md": "x\n"}, _BRANCH, None,
                 id="pre-push-canon-scan-not-range-scoped-published-never-blocks"),
    pytest.param({"specs/AGENTS.md": "# a\n"}, {"specs/_archive/new.md": "x\n"}, _BRANCH, "specs/_archive/new.md", id="non-canon-inside-range-blocks"),
    pytest.param(None, {"specs/.gitkeep": ""}, _BRANCH, "specs/.gitkeep", id="stray-dotfile"),
    pytest.param(None, {}, _DELETION, None, id="deletion-never-scanned"),
    pytest.param(None, {"specs/backlog/loose.md": "x\n"}, _TAG, "specs/backlog/loose.md", id="tag-scanned-too"),
    pytest.param(None, {"specs/rogue.md": "x\n"}, _BRANCH, "specs/rogue.md", id="runs-with-zero-denylist-terms"),
])
# fmt: on
def test_the_canon_scan_refuses_a_non_canon_path_in_the_pushed_range(
    repo: PushRepo, published: dict[str, str] | None, files: dict[str, str], line: str, refused: str | None
) -> None:
    """Bug ``pre-push-canon-scan-not-range-scoped``: only the pushed range is judged; published history never needs a rewrite."""
    remote = ZERO
    if published:
        remote = repo.commit(published)
        repo.publish()
    sha = repo.commit(files) if files else ZERO
    decision = _decide(repo, line.format(sha=sha, remote=remote))
    assert decision.allowed is (refused is None), decision.message
    if refused:
        assert refused in decision.message
        assert "delete the path; canon: specs/AGENTS.md" in decision.message
