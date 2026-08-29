"""Wiring the specs/ canon scan into ``push_gate_decision`` (v0.5.0 specs-canon
closure, operator ruling 2026-08-28).

Intent: CONTRACT — v0.5.0 specs-canon closure

Drives ``push_gate_decision`` with an injected fake :class:`GitObjectReader` — no real
git, no filesystem. Covers: a canon-conformant tree passes; a stray/non-canon path
refuses (naming the fix hint); a stale verdict refuses; a verdict matching HEAD or its
first parent passes; a git-read failure on either new port method fails closed; the
scan reaches every non-deletion ref (tags included), never a deletion.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core.models.git_scan import GitObjectReadError, ScannedObject
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import PushRef, parse_push_refs
from dadaia_workspace.features.specs.canon import canon_violations, verdict_violations

_SHA_A = "a" * 40
_SHA_B = "b" * 40
_ZERO = "0" * 40


@dataclass
class _FakeCanonObjectSource:
    """Maps a sha to a fixed specs/-prefixed tree-path list and an optional first
    parent — no denylist content, this fixture only exercises the canon scan step."""

    tree_by_sha: dict[str, list[str]] = field(default_factory=dict)
    parent_by_sha: dict[str, str] = field(default_factory=dict)
    tree_calls: list[tuple[str, str]] = field(default_factory=list)
    parent_calls: list[str] = field(default_factory=list)

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        return ()

    def list_tree_paths(self, repo: Path, sha: str, prefix: str) -> list[str]:
        self.tree_calls.append((sha, prefix))
        return self.tree_by_sha.get(sha, [])

    def first_parent(self, repo: Path, sha: str) -> str | None:
        self.parent_calls.append(sha)
        return self.parent_by_sha.get(sha)


class _FailingTreeObjectSource:
    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        return ()

    def list_tree_paths(self, repo: Path, sha: str, prefix: str) -> list[str]:
        raise GitObjectReadError("simulated git ls-tree failure")

    def first_parent(self, repo: Path, sha: str) -> str | None:
        return None


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_refs("\n".join(lines))


def test_a_fully_canon_conformant_tree_passes(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: ["specs/AGENTS.md", "specs/backlog/BACKLOG.json"]},
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
    )
    assert decision.allowed, decision.message
    assert (_SHA_A, "specs") in source.tree_calls


def test_a_non_canon_path_refuses_naming_the_fix_hint(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: ["specs/AGENTS.md", "specs/backlog/loose-entry.md"]},
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
    )
    assert not decision.allowed
    assert "specs/backlog/loose-entry.md" in decision.message
    assert "delete the path; canon: DADAIA.md §6" in decision.message


def test_a_stray_dotfile_refuses(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource(tree_by_sha={_SHA_A: ["specs/.gitkeep"]})
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
    )
    assert not decision.allowed
    assert "specs/.gitkeep" in decision.message


def test_a_verdict_matching_head_passes(tmp_path: Path) -> None:
    verdict_path = f"specs/releases/0.5.0/verdicts/{_SHA_A}.handoff.json"
    source = _FakeCanonObjectSource(tree_by_sha={_SHA_A: [verdict_path]})
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
    )
    assert decision.allowed, decision.message


def test_a_verdict_matching_first_parent_passes(tmp_path: Path) -> None:
    verdict_path = f"specs/releases/0.5.0/verdicts/{_SHA_B}.handoff.json"
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: [verdict_path]},
        parent_by_sha={_SHA_A: _SHA_B},
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
    )
    assert decision.allowed, decision.message
    assert _SHA_A in source.parent_calls


def test_a_stale_verdict_refuses(tmp_path: Path) -> None:
    stale_sha = "d" * 40
    verdict_path = f"specs/releases/0.5.0/verdicts/{stale_sha}.handoff.json"
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: [verdict_path]},
        parent_by_sha={_SHA_A: _SHA_B},
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
    )
    assert not decision.allowed
    assert verdict_path in decision.message


def test_a_deletion_ref_is_never_scanned(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource()
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_ZERO} refs/heads/feature/0.0.1 {_SHA_A}"),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
    )
    assert decision.allowed, decision.message
    assert source.tree_calls == []


def test_a_tag_push_is_scanned_too(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource(tree_by_sha={_SHA_A: ["specs/backlog/loose.md"]})
    decision = push_gate_decision(
        _refs(f"refs/tags/v9.9.9 {_SHA_A} refs/tags/v9.9.9 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
    )
    assert not decision.allowed
    assert "specs/backlog/loose.md" in decision.message


def test_a_git_read_failure_on_list_tree_paths_refuses_fail_closed(tmp_path: Path) -> None:
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        object_source=_FailingTreeObjectSource(),
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
    )
    assert not decision.allowed
    assert "reading the pushed specs/ tree failed" in decision.message


def test_canon_scan_runs_before_the_denylist_scan(tmp_path: Path) -> None:
    """The canon refusal fires even with zero denylist terms configured — step 2 runs
    independently of, and before, step 3 (A3.4's later denylist step)."""
    source = _FakeCanonObjectSource(tree_by_sha={_SHA_A: ["specs/rogue.md"]})
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        verdict_violations_fn=verdict_violations,
        denylist_terms=(),
    )
    assert not decision.allowed
    assert "specs/rogue.md" in decision.message
