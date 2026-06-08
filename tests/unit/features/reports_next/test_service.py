"""Unit tests for ReportsNextService (T-RN-03 / FR-RN-2).

Covers the 5 minimal cases from the SPEC plus owner-parsing edge cases:
  1. No active release        -> NoActiveReleaseError
  2. PLAN.md without owners    -> NoAgentSequenceError
  3. All agents completed      -> next_agent is None
  4. Next agent identified     -> first pending agent
  5. (--json parseability is covered in the CLI integration test)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import NoActiveReleaseError, NoAgentSequenceError
from dadaia_workspace.features.reports_next.service import (
    CANONICAL_AGENTS,
    ReportsNextService,
)

_RELEASE = "rel-1"


def _build(
    tmp_path: Path,
    *,
    active: str | None = f"release: {_RELEASE}\nphase: TASKS\n",
    plan: str | None = "**Owner:** qa-engineer\n**Owner:** devops-engineer\n",
    handoffs: dict[str, str] | None = None,
) -> ReportsNextService:
    """Construct a service over a temp specs/reports layout.

    handoffs: maps agent name -> release_id to seed a handoff sidecar for that agent.
    """
    specs = tmp_path / "specs"
    releases = specs / "releases"
    (releases / _RELEASE).mkdir(parents=True)
    if active is not None:
        (releases / "ACTIVE.md").write_text(active, encoding="utf-8")
    if plan is not None:
        (releases / _RELEASE / "PLAN.md").write_text(plan, encoding="utf-8")
    reports = tmp_path / "reports"
    for agent, rel in (handoffs or {}).items():
        agent_dir = reports / "ctx" / agent
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "x.handoff.json").write_text(
            json.dumps({"release_id": rel, "agent": agent}), encoding="utf-8"
        )
    return ReportsNextService(specs_dir=specs, reports_root=reports, context_name="ctx")


# --- Case 1: no active release ---


def test_missing_active_md_raises(tmp_path: Path) -> None:
    svc = _build(tmp_path, active=None)
    with pytest.raises(NoActiveReleaseError):
        svc.resolve_next()


def test_release_none_raises(tmp_path: Path) -> None:
    svc = _build(tmp_path, active="release: none\nphase: DISCOVERY\n")
    with pytest.raises(NoActiveReleaseError):
        svc.resolve_next()


# --- Case 2: PLAN without owners ---


def test_missing_plan_raises(tmp_path: Path) -> None:
    svc = _build(tmp_path, plan=None)
    with pytest.raises(NoAgentSequenceError):
        svc.resolve_next()


def test_plan_without_owners_raises(tmp_path: Path) -> None:
    svc = _build(tmp_path, plan="# PLAN\n\nNo owners declared here.\n")
    with pytest.raises(NoAgentSequenceError):
        svc.resolve_next()


def test_non_canonical_owner_filtered_out(tmp_path: Path) -> None:
    svc = _build(tmp_path, plan="owner: TBD\n**Owner:** someone-else\n")
    with pytest.raises(NoAgentSequenceError):
        svc.resolve_next()


# --- Case 3: all completed ---


def test_all_completed_returns_none(tmp_path: Path) -> None:
    svc = _build(
        tmp_path,
        plan="**Owner:** qa-engineer\n**Owner:** devops-engineer\n",
        handoffs={"qa-engineer": _RELEASE, "devops-engineer": _RELEASE},
    )
    result = svc.resolve_next()
    assert result.next_agent is None
    assert result.pending_agents == []
    assert result.completed_agents == ["qa-engineer", "devops-engineer"]
    assert result.release_id == _RELEASE


# --- Case 4: next agent identified ---


def test_first_pending_agent_identified(tmp_path: Path) -> None:
    svc = _build(
        tmp_path,
        plan="**Owner:** qa-engineer\n**Owner:** devops-engineer\n**Owner:** software-engineer\n",
        handoffs={"qa-engineer": _RELEASE},
    )
    result = svc.resolve_next()
    assert result.next_agent == "devops-engineer"
    assert result.completed_agents == ["qa-engineer"]
    assert result.pending_agents == ["devops-engineer", "software-engineer"]


def test_handoff_for_other_release_does_not_count(tmp_path: Path) -> None:
    svc = _build(
        tmp_path,
        plan="**Owner:** qa-engineer\n",
        handoffs={"qa-engineer": "some-other-release"},
    )
    result = svc.resolve_next()
    assert result.next_agent == "qa-engineer"  # wrong-release handoff ignored


# --- Owner-parsing edge cases ---


def test_owner_pattern_parens(tmp_path: Path) -> None:
    svc = _build(tmp_path, plan="- Track A (owner: software-engineer)\n")
    assert svc.resolve_next().next_agent == "software-engineer"


def test_owner_pattern_bold(tmp_path: Path) -> None:
    svc = _build(tmp_path, plan="**Owner:** ai-engineer\n")
    assert svc.resolve_next().next_agent == "ai-engineer"


def test_owner_pattern_yaml_inline(tmp_path: Path) -> None:
    svc = _build(tmp_path, plan="owner: product-engineer\n")
    assert svc.resolve_next().next_agent == "product-engineer"


def test_sequence_order_and_dedup(tmp_path: Path) -> None:
    plan = (
        "**Owner:** qa-engineer\n"
        "(owner: devops-engineer)\n"
        "**Owner:** qa-engineer\n"  # duplicate — must not reappear
        "owner: software-engineer\n"
    )
    svc = _build(tmp_path, plan=plan)
    result = svc.resolve_next()
    assert result.pending_agents == ["qa-engineer", "devops-engineer", "software-engineer"]


def test_canonical_agents_count() -> None:
    """CANONICAL_AGENTS must match the 12-name registry (9 core + 3 plugins)."""
    assert len(CANONICAL_AGENTS) == 12


def test_canonical_agents_exact_set() -> None:
    """CANONICAL_AGENTS must equal the registry-derived set exactly."""
    expected = frozenset(
        {
            "ai-engineer",
            "code-reviewer",
            "design-specialist",
            "devops-engineer",
            "frontend-engineer",
            "product-engineer",
            "project-auditor",
            "project-manager",
            "qa-engineer",
            "security-reviewer",
            "software-architect",
            "software-engineer",
        }
    )
    assert CANONICAL_AGENTS == expected
