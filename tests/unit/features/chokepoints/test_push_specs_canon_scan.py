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


def _branch(sha: str, remote: str = ZERO) -> str:
    return f"refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {remote}"


def test_a_fully_canon_conformant_tree_passes(repo: PushRepo) -> None:
    sha = repo.commit({"specs/AGENTS.md": "# a\n", "specs/backlog/BACKLOG.json": "{}\n"})
    decision = _decide(repo, _branch(sha))
    assert decision.allowed, decision.message


def test_a_non_canon_path_refuses_naming_the_fix_hint(repo: PushRepo) -> None:
    sha = repo.commit({"specs/AGENTS.md": "# a\n", "specs/backlog/loose-entry.md": "x\n"})
    decision = _decide(repo, _branch(sha))
    assert not decision.allowed
    assert "specs/backlog/loose-entry.md" in decision.message
    assert "delete the path; canon: specs/AGENTS.md" in decision.message


def test_a_non_canon_path_outside_the_pushed_range_never_blocks(repo: PushRepo) -> None:
    """Bug ``pre-push-canon-scan-not-range-scoped`` (operator ruling 2026-09-13): a
    pre-migration tree already published never blocks a push whose range touches only
    canon paths — published history never needs a rewrite."""
    published = repo.commit(
        {"specs/_archive/legacy/SPEC.md": "x\n", "specs/backlog/candidates.md": "x\n"}
    )
    repo.publish()
    sha = repo.commit({"specs/memory/product/atom.md": "x\n", "README.md": "x\n"})
    decision = _decide(repo, _branch(sha, published))
    assert decision.allowed, decision.message


def test_a_non_canon_path_inside_the_pushed_range_still_blocks(repo: PushRepo) -> None:
    published = repo.commit({"specs/AGENTS.md": "# a\n"})
    repo.publish()
    sha = repo.commit({"specs/_archive/new.md": "x\n"})
    decision = _decide(repo, _branch(sha, published))
    assert not decision.allowed
    assert "specs/_archive/new.md" in decision.message


def test_a_stray_dotfile_refuses(repo: PushRepo) -> None:
    sha = repo.commit({"specs/.gitkeep": ""})
    decision = _decide(repo, _branch(sha))
    assert not decision.allowed
    assert "specs/.gitkeep" in decision.message


def test_a_deletion_ref_is_never_scanned(repo: PushRepo) -> None:
    decision = _decide(repo, f"refs/heads/feature/0.0.1 {ZERO} refs/heads/feature/0.0.1 {'a' * 40}")
    assert decision.allowed, decision.message


def test_a_tag_push_is_scanned_too(repo: PushRepo) -> None:
    sha = repo.commit({"specs/backlog/loose.md": "x\n"})
    decision = _decide(repo, f"refs/tags/v9.9.9 {sha} refs/tags/v9.9.9 {ZERO}")
    assert not decision.allowed
    assert "specs/backlog/loose.md" in decision.message


def test_canon_scan_runs_before_the_denylist_scan(repo: PushRepo) -> None:
    """The canon refusal fires with zero denylist terms configured — step 2 runs
    independently of, and before, step 3."""
    sha = repo.commit({"specs/rogue.md": "x\n"})
    decision = _decide(repo, _branch(sha))
    assert not decision.allowed
    assert "specs/rogue.md" in decision.message
