"""Wiring the specs/ canon scan into ``push_gate_decision`` (v0.5.0 specs-canon
closure, operator ruling 2026-08-28).

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
from dadaia_workspace.features.specs.doctor_adr import cites_an_accepted_adr
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from tests.fakes import gate_fixes
from tests.fixtures.real_git import ZERO, PushRepo, git


@pytest.fixture()
def repo(tmp_path: Path) -> PushRepo:
    return PushRepo(tmp_path)


def _decide(repo: PushRepo, line: str, ledger: str | None = None) -> Any:
    return push_gate_decision(
        parse_push_stdin(line)[0],
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=GitSubprocessObjectReader(),
        repo=repo.path,
        canon_violations_fn=canon_violations,
        cites_accepted_adr=cites_an_accepted_adr(ledger),
    )


_TAG = "refs/tags/v9.9.9 {sha} refs/tags/v9.9.9 " + ZERO
_BRANCH = "refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {remote}"
_DELETION = f"refs/heads/feature/0.0.1 {ZERO} refs/heads/feature/0.0.1 {'a' * 40}"


# fmt: off
@pytest.mark.parametrize(("published", "side", "files", "line", "refused"), [
    pytest.param(None, None, {"specs/AGENTS.md": "# a\n", "specs/backlog/BACKLOG.json": "{}\n"}, _BRANCH, None, id="canon-tree-passes"),
    pytest.param(None, None, {"specs/AGENTS.md": "# a\n", "specs/backlog/loose-entry.md": "x\n"}, _BRANCH, "specs/backlog/loose-entry.md", id="non-canon-refuses"),
    pytest.param({"specs/_archive/legacy/SPEC.md": "x\n", "specs/backlog/candidates.md": "x\n"}, None,
                 {"specs/memory/product/area/atom.md": "x\n", "README.md": "x\n"}, _BRANCH, None,
                 id="pre-push-canon-scan-not-range-scoped-published-never-blocks"),
    pytest.param({"specs/AGENTS.md": "# a\n"}, None, {"specs/_archive/new.md": "x\n"}, _BRANCH, "specs/_archive/new.md", id="non-canon-inside-range-blocks"),
    pytest.param(None, None, {"specs/.gitkeep": ""}, _BRANCH, "specs/.gitkeep", id="stray-dotfile"),
    pytest.param(None, None, {}, _DELETION, None, id="deletion-never-scanned"),
    pytest.param(None, None, {"specs/backlog/loose.md": "x\n"}, _TAG, "specs/backlog/loose.md", id="tag-scanned-too"),
    pytest.param(None, None, {"specs/rogue.md": "x\n"}, _BRANCH, "specs/rogue.md", id="runs-with-zero-denylist-terms"),
    pytest.param({"specs/AGENTS.md": "# a\n"}, None, {"specs/rogue.md": None}, _BRANCH, None,
                 id="pre-push-canon-scan-judges-paths-the-range-deletes"),
    pytest.param({"specs/AGENTS.md": "# a\n"}, {"specs/backlog/candidates.md": "x\n"}, {"README.md": "x\n"}, _BRANCH, None,
                 id="pre-push-canon-scan-judges-paths-the-range-deletes-merge-of-published-history"),
    pytest.param({"specs/backlog/candidates.md": "x\n"}, None, {}, _TAG, None, id="pre-push-canon-scan-judges-paths-the-range-deletes-ref-at-a-published-commit"),
    pytest.param({"specs/AGENTS.md": "# a\n"}, {"specs/backlog/candidates.md": "x\n"}, {"specs/rogue.md": "x\n"}, _BRANCH,
                 "specs/rogue.md", id="pre-push-canon-scan-judges-paths-the-range-deletes-merge-then-non-canon-refuses"),
])
# fmt: on
def test_the_canon_scan_refuses_a_non_canon_path_in_the_pushed_range(
    repo: PushRepo,
    published: dict[str, str] | None,
    side: dict[str, str] | None,
    files: dict[str, str | None], line: str, refused: str | None
) -> None:
    """Bugs ``pre-push-canon-scan-not-range-scoped``, ``pre-push-canon-scan-judges-paths-the-range-deletes``:
    only the net tree the range publishes is judged — a None path is added then deleted inside the range;
    *side* is published as develop from the published tip, then merged."""
    remote = ZERO
    if published:
        remote = repo.commit(published)
        repo.publish()
    if side:
        git(repo.path, "switch", "-q", "-c", "develop")
        repo.commit(side)
        repo.publish()
        git(repo.path, "switch", "-q", "-")
        git(repo.path, "merge", "-q", "--no-ff", "-m", "merge", "develop")
    sha = repo.commit({p: t or "x\n" for p, t in files.items()}) if files else remote
    for gone in [p for p, t in files.items() if t is None]:
        (repo.path / gone).unlink()
        sha = repo.commit({})
    decision = _decide(repo, line.format(sha=sha, remote=remote))
    assert decision.allowed is (refused is None), decision.message
    if refused:
        assert refused in decision.message
        assert "delete the path; canon: specs/AGENTS.md" in decision.message


def test_a_push_allows_an_uncited_law_edit(repo: PushRepo) -> None:
    remote = repo.commit({"AGENTS.md": "# law\n- keep\n- drop\n"})
    repo.publish()
    (repo.path / "AGENTS.md").write_text("# law\n- keep\n", encoding="utf-8")
    sha = repo.commit({}, "chore: simplify law")

    decision = _decide(repo, _BRANCH.format(sha=sha, remote=remote))

    assert decision.allowed, decision.message
