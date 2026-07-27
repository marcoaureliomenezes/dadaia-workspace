"""Golden byte-identical behavior lock for the FR2 panel-api decomposition (T-55-30, AC-2).

v0.1.55 FR2 splits the 1,279-line ``features/panel/views/api.py`` (24 functions / 8 domains)
into per-domain view modules (``api_servers`` / ``api_contexts`` / ``api_agents`` /
``api_workflows`` / ``api_sessions`` / ``api_academy`` / ``api_reports`` / ``api_health``) and
DELETES ``api.py`` (no facade, no re-export barrel). The refactor MUST be behavior-preserving:
every panel route's ``(status, content_type, body)`` has to be byte-identical to the pre-split
tree.

This lock captures the ``(status, content_type, body)`` triple for a representative route from
EACH of the eight domains (every ``render_api_*`` / report-view render function's happy path plus
the key 400/403/404/503 error paths) on a single deterministic fixture panel state → a committed
golden. Post-split the SAME golden is reproduced from the per-domain modules (only the import
source moves; the captured bytes do not).

Determinism (AC-2 / R-4 analogue):

* **Fixed fake services** — servers/contexts/agents/workflows/sessions/academy are driven by
  hand-built fakes with fixed data; reports use a real ``ReportRetentionService`` over a
  ``tmp_path`` reports tree whose route-relative paths never leak an absolute path.
* **Timestamp + version normalization** — every ISO-8601 timestamp in a captured body is replaced
  with the token ``<TS>`` and the ``render_health`` package version with ``<VER>`` so the golden is
  machine- and clock-independent. Agent ``status`` is pinned to ``inactive`` via
  ``last_activity_at=None`` (never a relative-date time bomb).

Regenerate the golden (ONLY when a deliberate behavior change is approved) with:
``UPDATE_API_GOLDEN=1 pytest tests/unit/features/panel/test_api_golden.py``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from dadaia_workspace.core.models.agent import (
    AgentDTO,
    AgentNotFoundError,
    AgentPromptResult,
    InvalidAgentIdError,
)
from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService

# --- render functions under lock (per-domain modules post-FR2-split; the bytes do not move) ---
from dadaia_workspace.features.panel.views.api_academy import render_api_academy
from dadaia_workspace.features.panel.views.api_agents import (
    render_api_agent_prompt,
    render_api_agents_canonical,
)
from dadaia_workspace.features.panel.views.api_contexts import render_api_contexts
from dadaia_workspace.features.panel.views.api_health import render_health
from dadaia_workspace.features.panel.views.api_reports import (
    delete_report_file,
    mark_report_important,
    render_api_reports,
    serve_report_file,
    unmark_report_important,
)
from dadaia_workspace.features.panel.views.api_servers import render_api_servers
from dadaia_workspace.features.panel.views.api_sessions import render_api_sessions
from dadaia_workspace.features.panel.views.workflow_policy import render_api_workflow_catalog
from dadaia_workspace.features.reports.retention import ReportRetentionService
from dadaia_workspace.features.telemetry.aggregator.models import AgentSummary, TokenTotals

pytestmark = pytest.mark.unit

_HERE = Path(__file__).resolve().parent
_GOLDEN = _HERE / "_golden" / "api_golden_v0155.json"

_AGENT_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,63}[a-z0-9])?$")
# Any ISO-8601 timestamp (with or without fractional seconds / offset / Z).
_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")
_VERSION_RE = re.compile(r'"version":\s*"[^"]*"')

# Every panel domain must appear at least once in the capture (guards against a golden that
# silently narrowed away from a domain, which would make its byte-identity vacuous).
_ALL_DOMAINS = {
    "servers",
    "contexts",
    "agents",
    "workflows",
    "sessions",
    "academy",
    "reports",
    "health",
}


# ---------------------------------------------------------------------------
# Fakes (fixed data → deterministic responses)
# ---------------------------------------------------------------------------


class _FakeRegistry:
    def __init__(self, entries: list[tuple[PortEntry, PortStatus]]) -> None:
        self._entries = entries

    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[tuple[PortEntry, PortStatus]]:
        return list(self._entries)


class _FakeSpecContext:
    def __init__(self, contexts: list[SpecContextProject]) -> None:
        self._contexts = contexts

    def list_all(self) -> list[SpecContextProject]:
        return list(self._contexts)


class _FakeAcademy:
    def list_module_catalog(self) -> list[dict[str, object]]:
        return [
            {
                "module": "07_codex",
                "module_number": 7,
                "title": "Codex for dadaia-workspace",
                "lesson_count": 1,
                "lessons": [{"lesson": "01_codex_mental_model.md", "title": "01. Codex Mental"}],
            }
        ]


class _FakeTelemetry:
    """Returns fixed AgentSummary rows and a fixed session aggregate."""

    def list_agents(self, window_days: int = 180, context_slug: Any = None, limit: int = 50) -> Any:
        summary = AgentSummary(
            agent_id="software-engineer",
            display_name="software-engineer",
            providers=["claude"],
            dominant_model="claude-opus-4-8",
            is_subagent=False,
            session_count=3,
            total_cost_usd=1.5,
            cost_known=True,
            last_activity_at="",  # empty -> view maps to None; pins status "inactive" (no time bomb)
            token_totals=TokenTotals(input=100, cache_creation=20, cache_read=80, output=40),
            context_breakdown=[],
            recent_sessions=[],
            suspect_count=0,
        )
        return SimpleNamespace(
            generated_at="2026-05-17T10:00:00Z",
            window_days=window_days,
            pricing_age_days=12,
            pricing_model_date="2026-05-01",
            agents=[summary],
        )

    def aggregate_sessions(self, runtime: str) -> Any:
        return SimpleNamespace(
            runtime=runtime,
            total_sessions=5,
            active_sessions=2,
            total_cost_usd=0.42,
            cost_known=True,
            total_messages=87,
            top_agent=SimpleNamespace(name="software-engineer", session_count=3),
            generated_at="2026-05-19T10:00:00Z",
        )


class _FakeAgentsProvider:
    """Backs get_agent_prompt: mirrors production regex/not-found error contract."""

    def read_canonical_agents(self, workspace_root: Path) -> list[AgentDTO]:
        return []

    def get_prompt(self, agent_id: str, workspace_root: Path) -> AgentPromptResult:
        if not _AGENT_ID_RE.match(agent_id):
            raise InvalidAgentIdError(agent_id)
        if agent_id != "software-engineer":
            raise AgentNotFoundError(agent_id)
        return AgentPromptResult(
            body="# software-engineer\n\nSystem prompt body.\n",
            source_path=workspace_root / ".claude" / "agents" / "software-engineer.md",
        )


class _FakeDadaiaWorkflowsService:
    """Backs governed workflow membership in the agents catalog."""

    def _wf(self) -> SimpleNamespace:
        step = SimpleNamespace(
            order=1,
            label="Define",
            role="product-engineer",
            purpose="Author SPEC.",
            is_gate=False,
            harness_options=["claude"],
            model_options={"claude": ["claude-opus-4-8"]},
            runtime_kind="model",
            fragment_id="release_definition/define",
        )
        return SimpleNamespace(
            name="release_definition",
            display_name="Release Definition",
            purpose="Author SPEC/PLAN/TASKS.",
            availability="available",
            step_count=1,
            steps=[step],
            diagram_svg="<svg role='img'><g/></svg>",
        )

    def list_dadaia_workflows(self) -> list[SimpleNamespace]:
        return [self._wf()]

    def get_dadaia_workflow(self, name: str) -> SimpleNamespace | None:
        return self._wf() if name == "release_definition" else None


class _FakeWorkflowCatalog:
    def __init__(self) -> None:
        step = SimpleNamespace(
            label="release_scope",
            role="product-engineer",
            default_harness="codex",
            default_profile="codex-implementation-standard",
            default_profiles={"codex": "codex-implementation-standard"},
        )
        self.workflows = (SimpleNamespace(workflow_id="release_definition", steps=(step,)),)

    def workflow(self, workflow_id: str) -> SimpleNamespace | None:
        return self.workflows[0] if workflow_id == "release_definition" else None


class _FakeWorkflowResolver:
    def resolve(self, workflow_id: str, *, context: str) -> SimpleNamespace:
        entry = SimpleNamespace(
            harness="codex",
            model_profile="codex-implementation-standard",
            model="gpt-5.5",
            reasoning="medium",
            source=SimpleNamespace(value="library-default"),
            fragments=("release_definition.definition_draft",),
            output_schema="agent-run-result-v1",
        )
        return SimpleNamespace(step=lambda label: entry)


def _make_entry() -> tuple[PortEntry, PortStatus]:
    return (
        PortEntry(
            port=3000,
            project="dadaia-workspace",
            reserved_at="2026-01-01T00:00:00+00:00",
            expires_at="2026-01-01T08:00:00+00:00",
            url="http://localhost:3000",
            pid=1234,
            description="dev server",
        ),
        PortStatus.ACTIVE,
    )


def _make_context() -> SpecContextProject:
    return SpecContextProject(
        name="dadaia-workspace",
        state=ContextState.ALIVE,
        repo_slug="dadaia-workspace",
        repo_url="https://github.com/org/dadaia-workspace",
        created_at="2026-01-01T00:00:00+00:00",
        alive_since="2026-01-01T00:00:00+00:00",
        dead_since=None,
        current_branch="main",
    )


def _make_dto() -> AgentDTO:
    return AgentDTO(
        id="software-engineer",
        name="software-engineer",
        description="A software engineer agent.",
        dispatch_band=3,
        skills=["dadaia-task-manager"],
        tools=["Read", "Write"],
        model="claude-opus-4-8",
        max_turns=60,
        input_contract=None,
        gate_role="implementer",
    )


def _build_service(tmp_path: Path, *, telemetry: Any) -> PanelService:
    svc = PanelService(
        registry=_FakeRegistry([_make_entry()]),
        spec_context=_FakeSpecContext([_make_context()]),
        workspace_root=tmp_path,
        telemetry=telemetry,
        academy=_FakeAcademy(),
        report_retention=ReportRetentionService(tmp_path),
        agents_provider=_FakeAgentsProvider(),
        workflows_service=_FakeDadaiaWorkflowsService(),
    )
    svc._canonical_agents_override = [_make_dto()]  # type: ignore[attr-defined]
    return svc


def _seed_report_tree(tmp_path: Path) -> None:
    # A FRESH report (mtime = now) survives ``retention.cleanup()`` deterministically: its
    # effective timestamp is always within the 48h TTL window, so no clock-relative flakiness
    # and no self-deletion mid-capture. No handoff is seeded (the enrichment path is covered by
    # tests/unit/features/panel/test_api_contract.py); created_at falls to the mtime and is
    # normalized to ``<TS>``.
    report = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer" / "report.html"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("<html><head><title>t</title></head><body>ok</body></html>", encoding="utf-8")


def _normalize(body: bytes, workspace_root: Path) -> str:
    text = body.decode("utf-8")
    # Strip the absolute fixture workspace root (leaks into e.g. /api/contexts repo_path) so the
    # golden is machine-independent — the fixture lives on a per-run tmp_path. Cover the POSIX,
    # raw, and JSON-escaped (Windows `\\`) renderings, then canonicalize the separators of any
    # <WS>-anchored path tail — the golden locks route behavior, not OS path rendering.
    ws_escaped = json.dumps(str(workspace_root))[1:-1]
    text = (
        text.replace(workspace_root.as_posix(), "<WS>")
        .replace(ws_escaped, "<WS>")
        .replace(str(workspace_root), "<WS>")
    )
    # Canonicalize Windows path separators anywhere in the JSON body text. At this
    # (single-decoded) level a separator is EXACTLY two backslash chars (the JSON escape
    # of `\`), while an escaped newline (`\n`) is one backslash + `n` — so a two-backslash
    # match between path-ish characters is unambiguous (covers <WS>-anchored tails AND
    # relative paths like `.claude\agents\<name>.md` nested in stringified JSON bodies).
    text = re.sub(
        r"(?<=[\w.>\-])\\\\(?=[\w.\-])",
        "/",
        text,
    )
    text = _TS_RE.sub("<TS>", text)
    text = _VERSION_RE.sub('"version": "<VER>"', text)
    return text


def _capture(tmp_path: Path) -> dict[str, dict[str, object]]:
    """Invoke a representative route per domain and record normalized responses.

    The capture ORDER matters for the reports domain: the read routes
    (``api_reports``, ``reports_serve``) run before the mutating ones
    (``mark`` -> ``unmark`` -> ``delete``, which removes the report file last).
    """
    _seed_report_tree(tmp_path)
    service = _build_service(tmp_path, telemetry=_FakeTelemetry())
    service_no_tel = _build_service(tmp_path, telemetry=None)
    workflow_catalog = _FakeWorkflowCatalog()

    rpath = "ctx/qa-engineer/report.html"
    plan: list[tuple[str, str, Any, dict[str, object]]] = [
        ("servers", "api_servers", render_api_servers(service), {}),
        ("contexts", "api_contexts", render_api_contexts(service), {}),
        ("agents", "api_agents", render_api_agents_canonical(service), {}),
        (
            "agents",
            "api_agents_400",
            render_api_agents_canonical(service),
            {"active_window_days": 0},
        ),
        (
            "workflows",
            "api_workflow_catalog",
            render_api_workflow_catalog(workflow_catalog, lambda context: _FakeWorkflowResolver()),
            {},
        ),
        (
            "agents",
            "api_agent_prompt",
            render_api_agent_prompt(service),
            {"agent_id": "software-engineer"},
        ),
        (
            "agents",
            "api_agent_prompt_400",
            render_api_agent_prompt(service),
            {"agent_id": "../../etc"},
        ),
        (
            "agents",
            "api_agent_prompt_404",
            render_api_agent_prompt(service),
            {"agent_id": "ghost-agent"},
        ),
        ("sessions", "api_sessions", render_api_sessions(service), {"qs": {"runtime": ["claude"]}}),
        ("sessions", "api_sessions_503", render_api_sessions(service_no_tel), {"qs": {}}),
        ("academy", "api_academy", render_api_academy(service), {}),
        # Reports: READS first (api_reports runs retention.cleanup(); the fresh report survives),
        # then the mutating routes; delete removes the file LAST.
        ("reports", "api_reports", render_api_reports(service), {}),
        ("reports", "reports_serve", serve_report_file(service), {"path": rpath}),
        ("reports", "reports_serve_403", serve_report_file(service), {"path": "../../etc/passwd"}),
        ("reports", "reports_serve_404", serve_report_file(service), {"path": "ctx/missing.html"}),
        ("reports", "mark_report", mark_report_important(service), {"path": rpath}),
        ("reports", "unmark_report", unmark_report_important(service), {"path": rpath}),
        ("reports", "delete_report", delete_report_file(service), {"path": rpath}),
        ("health", "health", render_health(), {}),
    ]

    captured: dict[str, dict[str, object]] = {}
    for domain, route, view, kwargs in plan:
        status, content_type, body = view(**kwargs)
        captured[route] = {
            "domain": domain,
            "status": status,
            "content_type": content_type,
            "body": _normalize(body, tmp_path),
        }
    return captured


def test_api_routes_are_byte_identical_to_golden(tmp_path: Path) -> None:
    """The FR2 decomposition preserves every route's (status, content_type, body) (AC-2)."""
    current = json.dumps(_capture(tmp_path), indent=2, ensure_ascii=False, sort_keys=True)
    if os.environ.get("UPDATE_API_GOLDEN"):
        _GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        _GOLDEN.write_text(current + "\n", encoding="utf-8")
        pytest.skip("regenerated api golden (UPDATE_API_GOLDEN set)")
    golden = _GOLDEN.read_text(encoding="utf-8")
    assert current + "\n" == golden, (
        "Panel api route responses diverged from the pre-split golden — the FR2 decomposition "
        "changed observable behavior (status/content-type/body). Fix the split, never the golden."
    )


def test_golden_spans_all_eight_domains(tmp_path: Path) -> None:
    """Sanity: the capture covers >=1 route from EACH of the eight panel domains (AC-2)."""
    captured = _capture(tmp_path)
    domains = {str(entry["domain"]) for entry in captured.values()}
    assert domains == _ALL_DOMAINS, (
        f"golden capture must span all eight domains; got {sorted(domains)}, "
        f"missing {sorted(_ALL_DOMAINS - domains)}"
    )
