"""``iter_security_approvals`` — the handoff-qualification matrix (FR-W1-02 / DP-5).

Supersedes v0.6.0 T-060-04's coverage of this same qualification matrix, which lived in
the now-deleted ``test_push_gate_decision.py`` (exercised indirectly through
``push_gate_decision``'s security-verdict step). SPEC v0.4.4 A3.4 deletes that step from
the pre-push path outright (the verdict is now a PR gate, FR4) — ``iter_security_approvals``
itself is UNCHANGED and still has a live caller (``dadaia ci gc-push-verdicts --dry-run``,
``cli/commands/ci.py``), so its qualification behavior is re-targeted here, directly at
the function, rather than left uncovered.

Intent: CONTRACT — v0.4.4 A3.4 (coverage carried forward, retargeted)
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.chokepoints.service import iter_security_approvals

_SHA_A = "a" * 40
_SHA_B = "b" * 40


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


def test_no_handoffs_on_disk_yields_empty(tmp_path: Path) -> None:
    assert iter_security_approvals(tmp_path) == []


def test_approved_security_reviewer_handoff_qualifies(tmp_path: Path) -> None:
    _handoff(tmp_path, "sec-approve", commit_sha=_SHA_A)
    approvals = iter_security_approvals(tmp_path)
    assert [a.commit_sha for a in approvals] == [_SHA_A]
    assert approvals[0].source == "sec-approve.handoff.json"


def test_rejected_verdict_does_not_qualify(tmp_path: Path) -> None:
    _handoff(tmp_path, "sec-reject", verdict="REJECTED", commit_sha=_SHA_A)
    assert iter_security_approvals(tmp_path) == []


def test_non_security_agent_does_not_qualify(tmp_path: Path) -> None:
    _handoff(tmp_path, "qa-approve", agent="qa-engineer", commit_sha=_SHA_A)
    assert iter_security_approvals(tmp_path) == []


def test_scope_field_is_not_a_fallback_for_commit_sha(tmp_path: Path) -> None:
    _handoff(tmp_path, "sec-scope", commit_sha=None, scope=_SHA_A)
    assert iter_security_approvals(tmp_path) == []


def test_malformed_sibling_is_skipped_a_good_approve_still_qualifies(tmp_path: Path) -> None:
    ctx_dir = tmp_path / "demo-ctx"
    ctx_dir.mkdir(parents=True)
    (ctx_dir / "broken.handoff.json").write_text("{ not json", encoding="utf-8")
    _handoff(tmp_path, "sec-good", commit_sha=_SHA_B)

    approvals = iter_security_approvals(tmp_path)
    assert [a.commit_sha for a in approvals] == [_SHA_B]


def test_multiple_approvals_across_contexts_are_all_returned(tmp_path: Path) -> None:
    _handoff(tmp_path, "sec-a", commit_sha=_SHA_A)
    other_ctx = tmp_path / "other-ctx"
    other_ctx.mkdir(parents=True)
    payload = {
        "schema_version": "handoff-v1.1",
        "agent": "security-reviewer",
        "context": "other-ctx",
        "produced_at": "2026-06-12T12:00:00Z",
        "artifact": {"type": "other"},
        "metrics": {"commit_sha": _SHA_B},
        "verdict": "APPROVED",
    }
    (other_ctx / "sec-b.handoff.json").write_text(json.dumps(payload), encoding="utf-8")

    shas = {a.commit_sha for a in iter_security_approvals(tmp_path)}
    assert shas == {_SHA_A, _SHA_B}
