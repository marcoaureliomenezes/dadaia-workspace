"""v0.2.9 T4 — bounded rejection/retry digests (bug impl-reviews-retry-prompt-
exceeds-codex-window).

A legitimate review rejection once produced a retry/resume prompt carrying the FULL
findings dump, exceeding the Codex context window. The two digest seams are now
bounded: ``_render_prior_block_digest`` (resume feedback) and ``_compact_block_detail``
(the structural correction attempt in the runner) compact each value and cap the
whole, with a truncation marker pointing at the full-findings refs.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.lifecycle import BlockedState
from dadaia_workspace.features.lifecycle.agent_runner import _compact_block_detail
from dadaia_workspace.features.lifecycle.workflows._fragment_gate import (
    FragmentGateWorkflow,
)

pytestmark = pytest.mark.unit

_HUGE = "finding body with details " * 4000  # ~100 KB


def test_compact_block_detail_bounds_each_value_and_total() -> None:
    detail = {"findings": _HUGE, "verdict_reason": "one clean sentence"}
    rendered = _compact_block_detail(detail)
    assert len(rendered) <= 8000 + 100  # cap + truncation marker line
    assert "one clean sentence" in rendered
    # Per-value compaction is the primary bound (the head stays actionable).
    assert "finding body with details" in rendered
    assert _HUGE not in rendered

    # Many large values force the total cap + truncation marker.
    many = {f"key_{index:03d}": _HUGE for index in range(60)}
    rendered_many = _compact_block_detail(many)
    assert len(rendered_many) <= 8000 + 100
    assert "[digest truncated" in rendered_many


def test_compact_block_detail_small_map_passes_through() -> None:
    detail = {"a": "1", "b": "2"}
    rendered = _compact_block_detail(detail)
    assert rendered == "- a: 1\n- b: 2"


def test_prior_block_digest_is_bounded() -> None:
    blocked = BlockedState(
        reason="worker output violates review gate",
        blocked_at_step="plan_review",
        resume_token="tok",
        detail={"verdict_reason": _HUGE, "artifact": "specs/releases/v1/PLAN.md"},
    )
    rendered = FragmentGateWorkflow._render_prior_block_digest(blocked)
    assert len(rendered) <= 8000 + 100
    assert "plan_review" in rendered
    assert "specs/releases/v1/PLAN.md" in rendered
    assert _HUGE not in rendered

    many = {f"finding_{index:03d}": _HUGE for index in range(60)}
    blocked_many = BlockedState(
        reason="worker output violates review gate",
        blocked_at_step="plan_review",
        resume_token="tok",
        detail=many,
    )
    rendered_many = FragmentGateWorkflow._render_prior_block_digest(blocked_many)
    assert len(rendered_many) <= 8000 + 100
    assert "[digest truncated" in rendered_many


def test_prior_block_digest_keeps_short_details_verbatim() -> None:
    blocked = BlockedState(
        reason="gate failed",
        blocked_at_step="spec_review",
        resume_token="tok",
        detail={"verdict": "REJECTED", "missing": "SPEC.md section 3"},
    )
    rendered = FragmentGateWorkflow._render_prior_block_digest(blocked)
    assert "- verdict: REJECTED" in rendered
    assert "- missing: SPEC.md section 3" in rendered
    assert "[digest truncated" not in rendered
