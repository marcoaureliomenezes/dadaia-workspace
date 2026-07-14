"""Golden byte-identical behaviour lock for the FR1 fragment-workflow dedup (T-57-10, AC-1).

v0.1.57 FR1 extracts one ``FragmentGateWorkflow`` base + a ``_FragmentAssemblyMixin`` behind
the handoff-ledger workflow bodies (``release_definition`` / ``audit``) and the
``backlog_definition`` assembly seam. The refactor MUST be
behaviour-preserving: each body's **built worker prompt** and its **produced ledger payload**
have to serialize byte-identically to the pre-extraction tree.

These goldens are captured BEFORE any extraction and committed as the lock (T-57-10). After
the T-57-11 extraction they must remain byte-identical — *fix-the-split-never-the-golden*.

Capture is DETERMINISTIC:

* **Deterministic specs tree** — a small fixture ``repos/<ctx>/specs`` tree under ``tmp_path``
  with authored constitution / memory / release artifacts, so every resolved static/dynamic
  input renders fixed content. Every embedded ref is a POSIX ``specs_dir``-relative tail
  (``ContextSelector._specs_ref`` uses ``.as_posix()``), so the prompt bytes are
  machine-independent.
* **Scope-aware fake runtime** — returns a canned ``SUCCEEDED`` result whose single
  ``artifact_ref`` is derived from the request's first ``allowed_path`` so EVERY step (incl.
  the ADDITIVE ``bug_write`` step, scoped to ``specs/bugs/**``) passes the runner's
  evidence/scope gate, and the whole sequence completes and produces every ledger payload.
* **Frozen clock** — the workflow-step handoff resolver's clock is pinned so the produced
  envelopes are deterministic.
* **Path normalization (v0.1.55)** — the serialized capture strips the ``tmp_path`` workspace
  root (POSIX / raw / JSON-escaped renderings) to ``<WS>`` and canonicalizes any Windows
  ``\\`` separator nested in the JSON body, so the golden passes on BOTH separators.

**(Q1) The scope capture EXCLUDES the model-selection fields** (``model_profile`` /
``resolved_model``): the golden pins only role / allowed_paths / required_evidence / task_id +
prompt (+ the produced ledger payload). The backlog ``_scope`` model-threading convergence
(Problem #8) is proven by the T-57-11 RED-first ``resolved_model is not None`` test, never by
a golden diff.

**(Q2) Byte-identity is locked only through end-of-W1** (pre-FR2). W2's role→atom prompt
injection and W3's per-input policies intentionally re-baseline the affected goldens under
their own RED-first gates — recorded in each wave's AC-12 ledger; that is NOT fixing the split.

Regenerate the goldens (ONLY when a deliberate behaviour change is approved) with:
``UPDATE_FRAGMENT_GOLDEN=1 pytest tests/unit/features/lifecycle/test_fragment_gate_goldens.py``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecycleRun,
)
from dadaia_workspace.features.backlog.classifier import BoundItem
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline, implementation_ladder
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.features.lifecycle.workflows.audit import AuditWorkflow
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    AuthoredItem,
    BacklogDefinitionWorkflow,
    BacklogDemand,
    ProposedIntent,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    ReleaseDefinitionWorkflow,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

pytestmark = pytest.mark.unit

_HERE = Path(__file__).resolve().parent
_GOLDEN_DIR = _HERE / "_golden"
_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.57"
_ANCHOR_A = "pkg/a.py#A"


def _clock() -> str:
    return "2026-06-27T12:00:00Z"


class _GoldenFake:
    """Scope-aware deterministic ``AgentRuntimePort`` recording every request.

    The canned result's single ``artifact_ref`` is derived from the request's first
    ``allowed_path`` (``**`` -> ``step.step-output.json``) so every step — including the
    ADDITIVE ``bug_write`` step scoped to ``specs/bugs/**`` — is in-scope and the whole
    sequence completes/produces. The requests are recorded in call order for prompt capture.
    """

    def __init__(self) -> None:
        self.received_requests: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        allowed = (
            request.allowed_paths[0]
            if request.allowed_paths
            else ".dadaia/tmp/lifecycle-worker/x/**"
        )
        artifact = allowed.replace("**", "step.step-output.json")
        step = (request.task_id or "").rsplit(":", 1)[-1]
        audit_payloads: dict[str, dict[str, object]] = {
            "audit_scope": {
                "summary": "Bound architecture drift.",
                "audit_question": "Does implementation match architecture memory?",
                "lenses": [
                    {"name": "architecture", "rationale": "Contract fidelity."}
                ],
                "surfaces": ["pkg/a.py"],
                "acceptance_criteria": [
                    {"lens": "architecture", "pass_condition": "No contract drift."}
                ],
            },
            "drift_scan": {
                "summary": "No drift found.",
                "verdict": "APPROVED",
                "verdict_reason": "Every scoped lens passed.",
                "lens_results": [
                    {
                        "lens": "architecture",
                        "status": "PASS",
                        "evidence": ["pkg/a.py:1"],
                    }
                ],
                "findings": [],
            },
            "triage": {
                "summary": "No findings require routing.",
                "source_verdict": "APPROVED",
                "dispositions": [],
            },
        }
        domain_payload = audit_payloads.get(step, {})
        verdict = domain_payload.get("verdict", "APPROVED")
        structured: dict[str, str] = {"verdict": str(verdict)}
        reason = domain_payload.get("verdict_reason")
        if isinstance(reason, str):
            structured["verdict_reason"] = reason
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=str(domain_payload.get("summary", "golden step ok")),
            artifact_refs=(artifact,),
            structured_output=structured,
            domain_payload=domain_payload,
        )


def _seed_workspace(tmp_path: Path) -> Path:
    """Author a deterministic ``repos/<ctx>/specs`` tree; return the specs dir."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)
    (specs / "bugs").mkdir(parents=True)
    (specs / "audits").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text(
        "# Constitution\n\nGolden fixture constitution body.\n", encoding="utf-8"
    )
    (specs / "memory" / "architecture.md").write_text(
        "# Architecture\n\nGolden fixture architecture body.\n", encoding="utf-8"
    )
    (specs / "memory" / "quality-assurance.md").write_text(
        "# Quality Assurance\n\nGolden fixture QA body.\n", encoding="utf-8"
    )
    (specs / "memory" / "product" / "catalog.json").write_text(
        '{"features": [{"slug": "demo", "tldr": "demo feature"}]}\n', encoding="utf-8"
    )
    (specs / "releases" / _RELEASE / "SPEC.md").write_text(
        "# SPEC.md\n\nGolden fixture SPEC.md body.\n", encoding="utf-8"
    )
    (specs / "releases" / _RELEASE / "PLAN.md").write_text(
        "# PLAN.md\n\nGolden fixture PLAN.md body.\n\n"
        "## Validation Dependency Table\n\n"
        "| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |\n"
        "|---|---|---|---|---|\n"
        "| WS-1 | value | direct unit tests | None | None |\n",
        encoding="utf-8",
    )
    (specs / "releases" / _RELEASE / "TASKS.md").write_text(
        "# TASKS.md\n\nGolden fixture TASKS.md body.\n", encoding="utf-8"
    )
    return specs


def _selector(specs: Path, tmp_path: Path) -> ContextSelector:
    return ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )


def _resolver(tmp_path: Path) -> WorkflowHandoffResolver:
    return WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=_clock,
    )


def _registry(tmp_path: Path, specs: Path) -> Registry:
    """A registry binding ``pkg/a.py#A`` (planted source) — enough for the clean demand."""
    root = specs.parent
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("class A:\n    pass\n", encoding="utf-8")
    return build_registry(
        source_root=root,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )


def _clean_demand() -> BacklogDemand:
    return BacklogDemand(
        proposed_intents=(ProposedIntent(kind=SubjectKind.CODE, ref=_ANCHOR_A, change="add A"),),
        existing=(),
        authored=AuthoredItem(
            slug="new-item",
            is_new=True,
            bound=BoundItem(slug="new-item", anchor_changes={_ANCHOR_A: "add A"}),
        ),
    )


# ---------------------------------------------------------------------------
# capture + normalization
# ---------------------------------------------------------------------------


def _capture_requests(fake: _GoldenFake) -> list[dict[str, object]]:
    """Pin ONLY the non-model scope fields per step (Q1): role / allowed_paths /
    required_evidence / task_id + prompt. ``model_profile`` / ``resolved_model`` are excluded.
    """
    return [
        {
            "task_id": req.task_id,
            "role": req.role,
            "allowed_paths": list(req.allowed_paths),
            "required_evidence": [kind.value for kind in req.required_evidence],
            "prompt": req.prompt,
        }
        for req in fake.received_requests
    ]


def _capture_ledger(
    resolver: WorkflowHandoffResolver, run: LifecycleRun
) -> list[dict[str, object]]:
    """Pin the produced ledger payload of each producing step (schema + payload body)."""
    out: list[dict[str, object]] = []
    for record in sorted(run.workflow_steps, key=lambda r: (r.producer_step, r.attempt)):
        resolved = resolver.resolve_required(
            run, producer_step=record.producer_step, attempt=record.attempt
        )
        out.append(
            {
                "producer_step": record.producer_step,
                "attempt": record.attempt,
                "output_schema": record.output_schema,
                "payload": resolved.payload,
            }
        )
    return out


def _normalize(text: str, workspace_root: Path) -> str:
    """Strip the ``tmp_path`` root to ``<WS>`` and canonicalize Windows separators (v0.1.55)."""
    ws_escaped = json.dumps(str(workspace_root))[1:-1]
    text = (
        text.replace(workspace_root.as_posix(), "<WS>")
        .replace(ws_escaped, "<WS>")
        .replace(str(workspace_root), "<WS>")
    )
    # A path separator nested in a JSON string is EXACTLY two backslash chars (the JSON escape
    # of a single ``\``); an escaped newline is one backslash + ``n``. A two-backslash match
    # between path-ish characters is unambiguous — canonicalize it to ``/`` so a Windows
    # capture is byte-identical to the POSIX golden.
    return re.sub(r"(?<=[\w.>\-])\\\\(?=[\w.\-])", "/", text)


def _assert_golden(name: str, capture: dict[str, object], workspace_root: Path) -> None:
    text = json.dumps(capture, indent=2, ensure_ascii=False, sort_keys=True)
    normalized = _normalize(text, workspace_root) + "\n"
    golden_path = _GOLDEN_DIR / f"gate_{name}.json"
    if os.environ.get("UPDATE_FRAGMENT_GOLDEN"):
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(normalized, encoding="utf-8")
        pytest.skip(f"regenerated fragment-gate golden {golden_path.name}")
    assert normalized == golden_path.read_text(encoding="utf-8"), (
        f"fragment-gate golden {golden_path.name} diverged — the FR1 extraction changed an "
        "observable built prompt or produced ledger payload. Fix the split, never the golden."
    )


# ---------------------------------------------------------------------------
# the four goldens
# ---------------------------------------------------------------------------


def test_release_definition_golden(tmp_path: Path) -> None:
    specs = _seed_workspace(tmp_path)
    fake = _GoldenFake()
    resolver = _resolver(tmp_path)
    wf = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=_selector(specs, tmp_path),
        handoff_resolver=resolver,
    )
    result = wf.run("rd-golden")
    assert result.completed is True
    run = JsonLifecycleRunStore(tmp_path).load("rd-golden")
    assert run is not None
    _assert_golden(
        "release_definition",
        {"steps": _capture_requests(fake), "ledger": _capture_ledger(resolver, run)},
        tmp_path,
    )


def test_audit_golden(tmp_path: Path) -> None:
    specs = _seed_workspace(tmp_path)
    fake = _GoldenFake()
    resolver = _resolver(tmp_path)
    wf = AuditWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=_selector(specs, tmp_path),
        handoff_resolver=resolver,
    )
    result = wf.run("au-golden")
    assert result.completed is True
    run = JsonLifecycleRunStore(tmp_path).load("au-golden")
    assert run is not None
    _assert_golden(
        "audit",
        {"steps": _capture_requests(fake), "ledger": _capture_ledger(resolver, run)},
        tmp_path,
    )


def test_backlog_definition_golden(tmp_path: Path) -> None:
    specs = _seed_workspace(tmp_path)
    fake = _GoldenFake()
    resolver = _resolver(tmp_path)
    wf = BacklogDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=_selector(specs, tmp_path),
        registry=_registry(tmp_path, specs),
        handoff_resolver=resolver,
    )
    result = wf.run("bd-golden", _clean_demand())
    assert result.completed is True
    run = JsonLifecycleRunStore(tmp_path).load("bd-golden")
    assert run is not None
    assert run.workflow_steps.find("intake_grill", 0) is not None
    assert run.workflow_steps.find("backlog_author", 0) is not None
    _assert_golden(
        "backlog_definition",
        {"steps": _capture_requests(fake), "ledger": _capture_ledger(resolver, run)},
        tmp_path,
    )


def test_pipeline_ladder_golden(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    fake = _GoldenFake()
    # The production pipeline wires NO ContextSelector (the implementation.* fragment inputs
    # are unregistered selectors); mirror that so the ladder's fragment-only prompts render.
    pipeline = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=None,
    )
    result = pipeline.run("pl-golden", implementation_ladder(AgentRuntimeKind.FAKE))
    assert result.completed is True
    _assert_golden("pipeline", {"steps": _capture_requests(fake), "ledger": []}, tmp_path)


def _all_steps(capture: dict[str, object]) -> list[dict[str, object]]:
    steps = capture["steps"]
    assert isinstance(steps, list)
    return steps


def test_goldens_are_non_vacuous() -> None:
    """Guard: every committed golden pins >=1 step whose prompt cites a fragment banner."""
    for name in (
        "release_definition",
        "audit",
        "backlog_definition",
        "pipeline",
    ):
        path = _GOLDEN_DIR / f"gate_{name}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        steps = _all_steps(data)
        assert steps, f"golden {name} pins no steps"
        assert any("<!-- fragment:" in str(step.get("prompt", "")) for step in steps), (
            f"golden {name} pins no fragment-sourced prompt"
        )
