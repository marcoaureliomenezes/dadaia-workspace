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
from dadaia_workspace.features.reports.next import ReportsNextService

_RELEASE = "rel-1"


def _build(
    tmp_path: Path,
    *,
    active: str | None = f"release: {_RELEASE}\nphase: TASKS\n",
    plan: str | None = "**Owner:** qa-engineer\n**Owner:** product-engineer\n",
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


# --- Kept: first pending agent identified + wrong-release handoff excluded ---


def test_first_pending_agent_identified_and_other_release_handoff_excluded(
    tmp_path: Path,
) -> None:
    svc = _build(
        tmp_path,
        plan="**Owner:** qa-engineer\n**Owner:** product-engineer\n**Owner:** software-engineer\n",
        handoffs={"qa-engineer": _RELEASE},
    )
    result = svc.resolve_next()
    assert result.next_agent == "product-engineer"
    assert result.completed_agents == ["qa-engineer"]
    assert result.pending_agents == ["product-engineer", "software-engineer"]

    other_release_svc = _build(
        tmp_path.parent / (tmp_path.name + "-other-release"),
        plan="**Owner:** qa-engineer\n",
        handoffs={"qa-engineer": "some-other-release"},
    )
    other_release_result = other_release_svc.resolve_next()
    assert other_release_result.next_agent == "qa-engineer"  # wrong-release handoff ignored


# --- Error-raises matrix (no active release / no owners / non-canonical) ---


_DEFAULT_ACTIVE = f"release: {_RELEASE}\nphase: TASKS\n"
_DEFAULT_PLAN = "**Owner:** qa-engineer\n**Owner:** product-engineer\n"


@pytest.mark.parametrize(
    ("active", "plan", "expected_exc"),
    [
        pytest.param(None, _DEFAULT_PLAN, NoActiveReleaseError, id="missing-active-md"),
        pytest.param(
            "release: none\nphase: DISCOVERY\n",
            _DEFAULT_PLAN,
            NoActiveReleaseError,
            id="release-none",
        ),
        pytest.param(_DEFAULT_ACTIVE, None, NoAgentSequenceError, id="missing-plan"),
        pytest.param(
            _DEFAULT_ACTIVE,
            "# PLAN\n\nNo owners declared here.\n",
            NoAgentSequenceError,
            id="plan-without-owners",
        ),
        pytest.param(
            _DEFAULT_ACTIVE,
            "owner: TBD\n**Owner:** someone-else\n",
            NoAgentSequenceError,
            id="non-canonical-owner-filtered-out",
        ),
    ],
)
def test_error_raises_matrix(
    tmp_path: Path, active: str | None, plan: str | None, expected_exc: type[Exception]
) -> None:
    svc = _build(tmp_path, active=active, plan=plan)
    with pytest.raises(expected_exc):
        svc.resolve_next()


# --- All-completed + owner-pattern variants + dedup — 1 param table ---


@pytest.mark.parametrize(
    ("plan", "handoffs", "assert_fn"),
    [
        pytest.param(
            "**Owner:** qa-engineer\n**Owner:** product-engineer\n",
            {"qa-engineer": _RELEASE, "product-engineer": _RELEASE},
            lambda r: (
                r.next_agent is None
                and r.pending_agents == []
                and r.completed_agents == ["qa-engineer", "product-engineer"]
                and r.release_id == _RELEASE
            ),
            id="all-completed-returns-none",
        ),
        pytest.param(
            "- Track A (owner: software-engineer)\n",
            {},
            lambda r: r.next_agent == "software-engineer",
            id="owner-pattern-parens",
        ),
        pytest.param(
            "**Owner:** ai-engineer\n",
            {},
            lambda r: r.next_agent == "ai-engineer",
            id="owner-pattern-bold",
        ),
        pytest.param(
            "owner: product-engineer\n",
            {},
            lambda r: r.next_agent == "product-engineer",
            id="owner-pattern-yaml-inline",
        ),
        pytest.param(
            (
                "**Owner:** qa-engineer\n"
                "(owner: product-engineer)\n"
                "**Owner:** qa-engineer\n"  # duplicate — must not reappear
                "owner: software-engineer\n"
            ),
            {},
            lambda r: r.pending_agents == ["qa-engineer", "product-engineer", "software-engineer"],
            id="sequence-order-and-dedup",
        ),
    ],
)
def test_resolution_matrix(tmp_path: Path, plan: str, handoffs: dict[str, str], assert_fn) -> None:  # type: ignore[no-untyped-def]
    svc = _build(tmp_path, plan=plan, handoffs=handoffs)
    result = svc.resolve_next()
    assert assert_fn(result)
