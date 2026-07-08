"""Golden behaviour lock (T-58-10, v0.1.58 W1, AC-1) — captured BEFORE the FR1 refactor.

Three behaviour-bearing surfaces are byte-locked here so the typed-harness-registry
refactor (T-58-11) and the FR3 profile-aware doctor (W3) can be proven regression-free:

1. ``FileSystemPublicAssetManager.install()`` per-``--target`` resolution for each of
   ``{all, agents, claude, codex, pi}`` — the produced ``installed`` list, path-normalized.
   AC-1: this list must reproduce byte-identically once ``public_assets`` resolves the
   install-target vocabulary through ``core/harness_registry`` (T-58-11).
2. The panel runtime-validation accept/reject behaviour of ``render_api_workflows_list``
   and ``render_api_agents_canonical`` for ``claude`` / ``codex`` / ``pi`` and a bogus
   value. The api_agents runtime filter surfaces the accept/reject decision in the
   response body — each valid runtime yields a DISTINCT agent set (claude → the
   claude-provider agent, codex → the codex-provider agent, pi → the pi-provider agent),
   while a bogus runtime normalizes to ``claude`` — so this golden genuinely exercises the
   L1-entry-harness membership that T-58-11 repoints to
   ``harness_registry.L1_ENTRY_HARNESSES`` (a broken ``pi`` membership would flip the pi
   body to the claude body and this golden would catch it).
3. ``FileSystemPublicAssetManager.doctor()``'s full report list on a fully-installed
   all-four (no-profile) tree (Q2/A4). This is the FR3 absent-profile back-compat lock:
   W3 makes the doctor profile-aware, and AC-5 asserts byte-equality of the
   absent-profile path against THIS golden.

Determinism / v0.1.55 platform-invariant normalization:
  * Every ``.dadaia/``/``repos/`` path under the fixture ``tmp_path`` workspace is
    stripped to ``<WS>`` and ``os.sep`` is normalized to ``/`` (install/doctor lines are
    plain-text paths) so the goldens are machine- and OS-independent — the 3-OS CI matrix
    runs them.
  * Every ISO-8601 timestamp in a panel body is replaced with ``<TS>`` (the workflows
    endpoint stamps ``generated_at`` with ``datetime.now``).
  * The doctor ``git-dirty`` lines reference the LIVE source-repo working tree (not the
    fixture) and vary between the W1 capture and the W3 replay — they are environmental,
    not harness-projection behaviour, so they are dropped from the doctor golden.

Regenerate the goldens (ONLY when a deliberate, reviewed behaviour change lands) with:
``UPDATE_INSTALL_GOLDENS=1 pytest tests/unit/infrastructure/test_install_target_goldens.py``.
A byte diff without that flag is a behaviour regression — fix the consumer, never the golden.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from dadaia_workspace.core.models.agent import AgentDTO
from dadaia_workspace.core.models.telemetry import AgentSummary, TokenTotals
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api_agents import render_api_agents_canonical
from dadaia_workspace.features.panel.views.api_workflows import render_api_workflows_list
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.golden_platform import (
    assert_golden,
    is_env_doctor_line,
    norm_panel_body,
    norm_path_line,
)

pytestmark = pytest.mark.unit

_HERE = Path(__file__).resolve().parent
_GOLDEN_DIR = _HERE / "_golden"
_INSTALL_GOLDEN = _GOLDEN_DIR / "install_target_resolution_v0158.json"
_PANEL_GOLDEN = _GOLDEN_DIR / "panel_runtime_validation_v0158.json"
_DOCTOR_GOLDEN = _GOLDEN_DIR / "doctor_all_four_v0158.json"

_INSTALL_TARGETS = ("all", "agents", "claude", "codex", "pi")
_RUNTIMES = ("claude", "codex", "pi", "bogus")

# Normalization helpers (v0.1.55 platform-invariant law): consolidated into
# tests/helpers/golden_platform.py (v0.1.64 FR1) — norm_path_line, norm_panel_body,
# is_env_doctor_line, sort_line_lists/canon_env_line, assert_golden.


# ---------------------------------------------------------------------------
# Deterministic panel fakes (fixed data → deterministic responses)
# ---------------------------------------------------------------------------


class _FakeRegistry:
    def list_entries(self, project: str | None = None, include_stale: bool = True) -> list[Any]:
        return []


class _FakeSpecContext:
    def list_all(self) -> list[Any]:
        return []


class _FakeWorkflows:
    def list_summaries(self) -> list[Any]:
        return []


class _FakeTelemetry:
    """One agent per L1 runtime, each with a distinct ``providers`` list.

    This makes the api_agents runtime filter DISCRIMINATING per runtime: claude →
    software-engineer, codex → qa-engineer, pi → security-reviewer. A bogus runtime
    normalizes to claude → software-engineer.
    """

    def list_agents(
        self, window_days: int = 180, context_slug: Any = None, limit: int = 200
    ) -> Any:
        def summ(agent_id: str, providers: list[str]) -> AgentSummary:
            return AgentSummary(
                agent_id=agent_id,
                display_name=agent_id,
                providers=providers,
                dominant_model="claude-opus-4-8",
                is_subagent=False,
                session_count=1,
                total_cost_usd=0.5,
                cost_known=True,
                last_activity_at="",  # empty -> None -> status "inactive" (no time bomb)
                token_totals=TokenTotals(input=10, cache_creation=1, cache_read=2, output=3),
                context_breakdown=[],
                recent_sessions=[],
                suspect_count=0,
            )

        return SimpleNamespace(
            generated_at="2026-07-04T00:00:00Z",
            window_days=window_days,
            pricing_age_days=None,
            pricing_model_date=None,
            agents=[
                summ("software-engineer", ["claude"]),
                summ("qa-engineer", ["codex"]),
                summ("security-reviewer", ["pi"]),
            ],
        )


def _canonical_agents() -> list[AgentDTO]:
    return [
        AgentDTO(
            id=agent_id,
            name=agent_id,
            description=f"{agent_id} agent.",
            dispatch_band=3,
            skills=[],
            tools=["Read", "Write"],
            model="claude-opus-4-8",
            max_turns=60,
            input_contract=None,
            gate_role=None,
        )
        for agent_id in ("software-engineer", "qa-engineer", "security-reviewer")
    ]


def _build_panel_service(tmp_path: Path) -> PanelService:
    svc = PanelService(
        registry=_FakeRegistry(),  # type: ignore[arg-type]
        spec_context=_FakeSpecContext(),  # type: ignore[arg-type]
        workspace_root=tmp_path,
        telemetry=_FakeTelemetry(),
    )
    svc._canonical_agents_override = _canonical_agents()  # type: ignore[attr-defined]
    svc._workflows_service_override = _FakeWorkflows()  # type: ignore[attr-defined]
    return svc


# ---------------------------------------------------------------------------
# Capture functions
# ---------------------------------------------------------------------------


def _capture_install(tmp_path: Path) -> dict[str, list[str]]:
    mgr = FileSystemPublicAssetManager()
    result: dict[str, list[str]] = {}
    for target in _INSTALL_TARGETS:
        ws = tmp_path / f"install_{target}"
        ws.mkdir()
        installed = mgr.install(ws, target=target)
        result[target] = [norm_path_line(line, ws) for line in installed]
    return result


def _capture_panel(tmp_path: Path) -> dict[str, dict[str, object]]:
    service = _build_panel_service(tmp_path)
    workflows_view = render_api_workflows_list(service)
    agents_view = render_api_agents_canonical(service)
    result: dict[str, dict[str, object]] = {}
    for runtime in _RUNTIMES:
        for name, view in (("api_workflows", workflows_view), ("api_agents", agents_view)):
            status, content_type, body = view(qs={"runtime": [runtime]})
            result[f"{name}:{runtime}"] = {
                "status": status,
                "content_type": content_type,
                "body": norm_panel_body(body, tmp_path),
            }
    return result


def _capture_doctor(tmp_path: Path) -> list[str]:
    ws = tmp_path / "doctor_all_four"
    ws.mkdir()
    mgr = FileSystemPublicAssetManager()
    mgr.install(ws, target="all")
    report = mgr.doctor(ws)
    return [norm_path_line(line, ws) for line in report if not is_env_doctor_line(line)]


# ---------------------------------------------------------------------------
# Golden compare / update — tests.helpers.golden_platform.assert_golden
# ---------------------------------------------------------------------------


def _v0158_message(what: str) -> str:
    return (
        f"{what} diverged from the committed v0.1.58 W1 golden — the change altered "
        "observable behaviour. Fix the consumer, never the golden."
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_install_target_resolution_is_byte_identical(tmp_path: Path) -> None:
    """AC-1: install() per-target ``installed`` lists reproduce byte-identically."""
    assert_golden(
        _INSTALL_GOLDEN,
        _capture_install(tmp_path),
        "install-target-resolution",
        message=_v0158_message("install-target-resolution"),
    )


def test_panel_runtime_validation_is_byte_identical(tmp_path: Path) -> None:
    """AC-1: panel runtime accept/reject responses reproduce byte-identically."""
    assert_golden(
        _PANEL_GOLDEN,
        _capture_panel(tmp_path),
        "panel-runtime-validation",
        message=_v0158_message("panel-runtime-validation"),
    )


def test_doctor_all_four_report_is_byte_identical(tmp_path: Path) -> None:
    """AC-1/Q2/A4: doctor()'s all-four (no-profile) report is the FR3 back-compat lock."""
    assert_golden(
        _DOCTOR_GOLDEN,
        _capture_doctor(tmp_path),
        "doctor-all-four",
        message=_v0158_message("doctor-all-four"),
    )


def test_panel_runtime_accept_reject_is_discriminating(tmp_path: Path) -> None:
    """Guard: the panel golden actually distinguishes each L1 runtime (not a vacuous lock).

    claude/codex/pi must each produce a DISTINCT api_agents body, and a bogus runtime must
    reproduce the claude body (normalized). If this ever collapses, the golden would stop
    catching an L1-membership regression in T-58-11.
    """
    captured = _capture_panel(tmp_path)
    claude_body = captured["api_agents:claude"]["body"]
    codex_body = captured["api_agents:codex"]["body"]
    pi_body = captured["api_agents:pi"]["body"]
    bogus_body = captured["api_agents:bogus"]["body"]
    assert claude_body != codex_body
    assert claude_body != pi_body
    assert codex_body != pi_body
    assert bogus_body == claude_body
