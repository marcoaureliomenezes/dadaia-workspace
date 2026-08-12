"""Unit tests for the push-gate verdict decision (FR-W1-02 / DP-5).

Synthetic handoff files + synthetic stdin ref lines. The predicate keys ONLY on the
stdin ``local_sha`` (never ``git rev-parse HEAD``) and on ``metrics.commit_sha`` (the
single canonical field, no ``scope`` fallback) — per-sha re-key law.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.service import PushRef, parse_push_refs

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


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_refs("\n".join(lines))


# ---------------------------------------------------------------------------
# Kept: per-sha verdict keying — the CRITICAL invariant
# ---------------------------------------------------------------------------


def test_approved_pushed_sha_passes(tmp_path: Path) -> None:
    _handoff(tmp_path, "sec-approve", commit_sha=_SHA_A)
    d = push_gate_decision(
        tmp_path, _refs(f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}")
    )
    assert d.allowed, d.message


def test_stale_sha_approve_blocks(tmp_path: Path) -> None:
    """An APPROVE for a different (older) sha than the one being pushed never passes —
    stale approvals do not carry forward across commits (per-sha re-key law)."""
    _handoff(tmp_path, "sec-approve", commit_sha=_SHA_B)
    d = push_gate_decision(
        tmp_path, _refs(f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}")
    )
    assert not d.allowed
    assert _SHA_A[:12] in d.message


# ---------------------------------------------------------------------------
# Pass-without-verdict cases (deletion / tag / empty stdin / malformed sibling
# handoff skipped while a good approve still passes) — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ref_line", "setup"),
    [
        pytest.param(f"refs/heads/old {_ZERO} refs/heads/old {_SHA_A}", None, id="branch-deletion"),
        pytest.param(f"refs/tags/v1 {_SHA_A} refs/tags/v1 {_ZERO}", None, id="tag-push"),
        pytest.param("", None, id="empty-stdin-no-refs"),
        pytest.param(
            f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}",
            "malformed_sibling",
            id="malformed-handoff-skipped-good-approve-still-passes",
        ),
    ],
)
def test_passes_without_verdict(tmp_path: Path, ref_line: str, setup: str | None) -> None:
    if setup == "malformed_sibling":
        ctx_dir = tmp_path / "demo-ctx"
        ctx_dir.mkdir(parents=True)
        (ctx_dir / "broken.handoff.json").write_text("{ not json", encoding="utf-8")
        _handoff(tmp_path, "sec-good", commit_sha=_SHA_A)
    d = push_gate_decision(tmp_path, _refs(ref_line))
    assert d.allowed


# ---------------------------------------------------------------------------
# Non-counting verdicts / block matrix — 1 param
# ---------------------------------------------------------------------------


_DEVELOP_ONLY = (f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}",)
_DEVELOP_TWO_TIPS = (
    f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}",
    f"refs/heads/develop {_SHA_B} refs/heads/develop {_ZERO}",
)


@pytest.mark.parametrize(
    ("setup", "ref_lines", "expect_message_contains"),
    [
        pytest.param(
            lambda tp: None,
            _DEVELOP_ONLY,
            "no security-reviewer APPROVE found",
            id="no-approve-at-all",
        ),
        pytest.param(
            lambda tp: _handoff(tp, "sec-reject", verdict="REJECTED", commit_sha=_SHA_A),
            _DEVELOP_ONLY,
            None,
            id="rejected-verdict-does-not-count",
        ),
        pytest.param(
            lambda tp: _handoff(tp, "qa-approve", agent="qa-engineer", commit_sha=_SHA_A),
            _DEVELOP_ONLY,
            None,
            id="non-security-agent-does-not-count",
        ),
        pytest.param(
            lambda tp: _handoff(tp, "sec-scope", commit_sha=None, scope=_SHA_A),
            _DEVELOP_ONLY,
            None,
            id="scope-field-is-not-a-fallback-for-commit-sha",
        ),
        pytest.param(
            lambda tp: _handoff(tp, "sec-head", commit_sha="c" * 40),
            _DEVELOP_ONLY,
            None,
            id="approve-for-unrelated-sha-does-not-satisfy-pushed-sha",
        ),
        pytest.param(
            lambda tp: _handoff(tp, "sec-a", commit_sha=_SHA_A),
            _DEVELOP_TWO_TIPS,
            _SHA_B[:12],
            id="every-develop-tip-line-must-be-covered",
        ),
    ],
)
def test_non_counting_verdicts_block_matrix(
    tmp_path: Path,
    setup: object,
    ref_lines: tuple[str, ...],
    expect_message_contains: str | None,
) -> None:
    setup(tmp_path)  # type: ignore[operator]
    d = push_gate_decision(tmp_path, _refs(*ref_lines))
    assert not d.allowed
    if expect_message_contains is not None:
        assert expect_message_contains in d.message
