"""Unit tests for the push-gate verdict decision (FR-W1-02 / DP-5).

Synthetic handoff files + synthetic stdin ref lines. The predicate keys ONLY on the
stdin ``local_sha`` (never ``git rev-parse HEAD``) and on ``metrics.commit_sha`` (the
single canonical field, no ``scope`` fallback).
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.service import parse_push_refs

_SHA_A = "a" * 40
_SHA_B = "b" * 40
_ZERO = "0" * 40


def _handoff(
    root: Path,
    name: str,
    *,
    agent: str = "security-reviewer",
    verdict: str | None = "APPROVED",
    commit_sha: str | None = _SHA_A,
    scope: str | None = None,
) -> None:
    ctx_dir = root / "demo-ctx"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": agent,
        "context": "demo-ctx",
        "produced_at": "2026-06-12T12:00:00Z",
        "artifact": {"type": "other"},
    }
    metrics: dict[str, object] = {}
    if commit_sha is not None:
        metrics["commit_sha"] = commit_sha
    payload["metrics"] = metrics
    if verdict is not None:
        payload["verdict"] = verdict
    if scope is not None:
        payload["scope"] = scope
    (ctx_dir / f"{name}.handoff.json").write_text(json.dumps(payload), encoding="utf-8")


def _refs(*lines: str) -> list:
    return parse_push_refs("\n".join(lines))


def test_approved_pushed_sha_passes(tmp_path: Path) -> None:
    _handoff(tmp_path, "sec-approve", commit_sha=_SHA_A)
    d = push_gate_decision(tmp_path, _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"))
    assert d.allowed, d.message


def test_stale_sha_approve_blocks(tmp_path: Path) -> None:
    # APPROVE exists but for a different (older) sha than the one being pushed.
    _handoff(tmp_path, "sec-approve", commit_sha=_SHA_B)
    d = push_gate_decision(tmp_path, _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"))
    assert not d.allowed
    assert _SHA_A[:12] in d.message


def test_no_approve_blocks_and_lists_what_was_found(tmp_path: Path) -> None:
    d = push_gate_decision(tmp_path, _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"))
    assert not d.allowed
    assert "no security-reviewer APPROVE found" in d.message


def test_rejected_verdict_does_not_count(tmp_path: Path) -> None:
    _handoff(tmp_path, "sec-reject", verdict="REJECTED", commit_sha=_SHA_A)
    d = push_gate_decision(tmp_path, _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"))
    assert not d.allowed


def test_non_security_agent_does_not_count(tmp_path: Path) -> None:
    _handoff(tmp_path, "qa-approve", agent="qa-engineer", commit_sha=_SHA_A)
    d = push_gate_decision(tmp_path, _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"))
    assert not d.allowed


def test_scope_field_is_not_a_fallback(tmp_path: Path) -> None:
    # commit_sha absent from metrics; scope carries the sha — must NOT satisfy the gate.
    _handoff(tmp_path, "sec-scope", commit_sha=None, scope=_SHA_A)
    d = push_gate_decision(tmp_path, _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"))
    assert not d.allowed


def test_branch_deletion_passes_without_verdict(tmp_path: Path) -> None:
    d = push_gate_decision(tmp_path, _refs(f"refs/heads/old {_ZERO} refs/heads/old {_SHA_A}"))
    assert d.allowed


def test_tag_push_passes_without_verdict(tmp_path: Path) -> None:
    d = push_gate_decision(tmp_path, _refs(f"refs/tags/v1 {_SHA_A} refs/tags/v1 {_ZERO}"))
    assert d.allowed


def test_multiple_refs_all_must_be_covered(tmp_path: Path) -> None:
    _handoff(tmp_path, "sec-a", commit_sha=_SHA_A)
    # SHA_B has no approve ⇒ block even though SHA_A is covered.
    d = push_gate_decision(
        tmp_path,
        _refs(
            f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}",
            f"refs/heads/feature {_SHA_B} refs/heads/feature {_ZERO}",
        ),
    )
    assert not d.allowed
    assert _SHA_B[:12] in d.message


def test_empty_stdin_no_refs_passes(tmp_path: Path) -> None:
    d = push_gate_decision(tmp_path, _refs(""))
    assert d.allowed


def test_predicate_never_consults_head(tmp_path: Path) -> None:
    # A handoff approving a sha that is NOT in the stdin refs must not let an unrelated
    # pushed sha through. This asserts the gate keys on stdin lines, not the repo HEAD.
    _handoff(tmp_path, "sec-head", commit_sha="c" * 40)
    d = push_gate_decision(tmp_path, _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"))
    assert not d.allowed


def test_malformed_handoff_skipped(tmp_path: Path) -> None:
    ctx_dir = tmp_path / "demo-ctx"
    ctx_dir.mkdir(parents=True)
    (ctx_dir / "broken.handoff.json").write_text("{ not json", encoding="utf-8")
    _handoff(tmp_path, "sec-good", commit_sha=_SHA_A)
    d = push_gate_decision(tmp_path, _refs(f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"))
    assert d.allowed
