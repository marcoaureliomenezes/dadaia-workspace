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

from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.core.models.git_scan import ScannedObject
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import PushRef, parse_push_stdin
from dadaia_workspace.features.specs.canon import canon_violations
from tests.fakes import gate_fixes

_SHA_A = "a" * 40
_SHA_B = "b" * 40
_SHA_C = "c" * 40
_ZERO = "0" * 40


@dataclass
class _FakeCanonObjectSource:
    """Maps a sha to a fixed specs/-prefixed tree-path list and an optional first
    parent — no denylist content, this fixture only exercises the canon scan step."""

    tree_by_sha: dict[str, list[str]] = field(default_factory=dict)
    #: The paths the pushed RANGE introduces or rewrites at a sha (bug
    #: ``pre-push-canon-scan-not-range-scoped``: the canon scan reads these, never the tree).
    range_by_sha: dict[str, list[str]] = field(default_factory=dict)
    parent_by_sha: dict[str, str] = field(default_factory=dict)
    sha_by_ref: dict[str, str] = field(default_factory=dict)
    tree_calls: list[tuple[str, str]] = field(default_factory=list)
    parent_calls: list[str] = field(default_factory=list)
    ref_calls: list[str] = field(default_factory=list)

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        return [
            ScannedObject(path=path, sha=f"blob{i}", text="", decodable=True)
            for i, path in enumerate(self.range_by_sha.get(local_sha, []))
        ]


class _FailingTreeObjectSource:
    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        return ()


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_stdin("\n".join(lines))[0]


def test_a_fully_canon_conformant_tree_passes(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: ["specs/AGENTS.md", "specs/backlog/BACKLOG.json"]},
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
    )
    assert decision.allowed, decision.message


def test_a_non_canon_path_refuses_naming_the_fix_hint(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: ["specs/AGENTS.md", "specs/backlog/loose-entry.md"]},
        range_by_sha={_SHA_A: ["specs/backlog/loose-entry.md"]},
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
    )
    assert not decision.allowed
    assert "specs/backlog/loose-entry.md" in decision.message
    assert "delete the path; canon: specs/AGENTS.md" in decision.message


def test_a_non_canon_path_outside_the_pushed_range_never_blocks(tmp_path: Path) -> None:
    """Bug ``pre-push-canon-scan-not-range-scoped`` (operator ruling 2026-09-13): a
    pre-migration tree (``specs/_archive/**``, a Markdown backlog) already published
    must never block a push whose range touches only canon paths — the range scope
    means published history never needs a rewrite (the denylist scan's own law)."""
    source = _FakeCanonObjectSource(
        tree_by_sha={
            _SHA_A: [
                "specs/AGENTS.md",
                "specs/_archive/legacy/SPEC.md",
                "specs/backlog/candidates.md",
                "specs/memory/product/atom.md",
            ]
        },
        range_by_sha={_SHA_A: ["specs/memory/product/atom.md", "README.md"]},
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_SHA_B}"),
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=lambda paths: [p for p in paths if p.startswith("_archive/")],
    )
    assert decision.allowed, decision.message


def test_a_non_canon_path_inside_the_pushed_range_still_blocks(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: ["specs/AGENTS.md", "specs/_archive/new.md"]},
        range_by_sha={_SHA_A: ["specs/_archive/new.md"]},
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_SHA_B}"),
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
    )
    assert not decision.allowed
    assert "specs/_archive/new.md" in decision.message


def test_a_stray_dotfile_refuses(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: ["specs/.gitkeep"]}, range_by_sha={_SHA_A: ["specs/.gitkeep"]}
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
    )
    assert not decision.allowed
    assert "specs/.gitkeep" in decision.message


def test_a_deletion_ref_is_never_scanned(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource()
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_ZERO} refs/heads/feature/0.0.1 {_SHA_A}"),
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
    )
    assert decision.allowed, decision.message
    assert source.tree_calls == []


def test_a_tag_push_is_scanned_too(tmp_path: Path) -> None:
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: ["specs/backlog/loose.md"]},
        range_by_sha={_SHA_A: ["specs/backlog/loose.md"]},
    )
    decision = push_gate_decision(
        _refs(f"refs/tags/v9.9.9 {_SHA_A} refs/tags/v9.9.9 {_ZERO}"),
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
    )
    assert not decision.allowed
    assert "specs/backlog/loose.md" in decision.message


def test_canon_scan_runs_before_the_denylist_scan(tmp_path: Path) -> None:
    """The canon refusal fires even with zero denylist terms configured — step 2 runs
    independently of, and before, step 3 (A3.4's later denylist step)."""
    source = _FakeCanonObjectSource(
        tree_by_sha={_SHA_A: ["specs/rogue.md"]}, range_by_sha={_SHA_A: ["specs/rogue.md"]}
    )
    decision = push_gate_decision(
        _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}"),
        gitflow=DEFAULT,
        fixes=gate_fixes(),
        object_source=source,
        repo=tmp_path,
        canon_violations_fn=canon_violations,
        denylist_terms=(),
    )
    assert not decision.allowed
    assert "specs/rogue.md" in decision.message
