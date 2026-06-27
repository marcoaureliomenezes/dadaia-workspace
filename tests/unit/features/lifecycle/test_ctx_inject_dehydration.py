"""A30 — lifecycle prompts are fully selector-composed, with NO ctx-inject side effect.

WS-C (v0.1.30 / T-30-E-05) dehydrates ``ctx_inject`` to a lean session bootstrap: nothing in
the lifecycle prompt path reads the hook's injection or its sentinel. These tests prove that
directly:

1. A lifecycle step prompt is composed entirely from the Python dynamic selector
   (``ContextSelector`` + ``LifecyclePromptBuilder``) — the fragment body + the
   selector-resolved dynamic context are present — WITHOUT ever invoking ``ctx_inject`` and
   WITHOUT any ctx-inject sentinel existing on disk.
2. The hook's session-bootstrap memory is dehydrated: a large ``tech-stack.md`` is reduced to
   a bounded digest (it is no longer dumped verbatim), while a small one is unchanged and the
   catalog stays the lean tldr-digest. ``bind/session`` safety + the lean generic preflight
   are unchanged (covered by ``tests/unit/hooks/test_ctx_inject*``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.workflows.audit import AuditWorkflow
from dadaia_workspace.hooks import ctx_inject
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.30"
_SENTINEL_PREFIX = "ctx-inject-fired-"


@dataclass(frozen=True)
class _Fake:
    kind: AgentRuntimeKind

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="ok",
            artifact_refs=(f".dadaia/handoff/{_CONTEXT}/s.handoff.json",),
            structured_output={"verdict": "APPROVED"},
        )


def _workspace(tmp_path: Path, *, open_bug: bool = True) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "audits").mkdir(parents=True)
    (specs / "bugs").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "memory" / "architecture.md").write_text(
        "# Architecture\nThe headless adapter base lives in infrastructure.\n", encoding="utf-8"
    )
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    if open_bug:
        # A dynamic-input the audit_scope fragment selects (open_bugs) — proves selector
        # content lands in the composed prompt. No frontmatter ⇒ open by default, and the
        # `summary` policy falls back to the leading prose lines (which carry the marker).
        (specs / "bugs" / "SELECTOR-MARKER-bug.md").write_text(
            "# SELECTOR-MARKER-OPEN-BUG\n\nSymptom: a deliberately marked open bug.\n",
            encoding="utf-8",
        )
    return tmp_path


def _audit_workflow(tmp_path: Path) -> AuditWorkflow:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )
    return AuditWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _Fake(kind),  # type: ignore[arg-type]
        context_selector=selector,
    )


# --- A30: the lifecycle step prompt is fully composed from the dynamic selector ----------


def test_lifecycle_prompt_composed_from_selector_without_ctx_inject(tmp_path: Path) -> None:
    _workspace(tmp_path)
    wf = _audit_workflow(tmp_path)

    result = wf.run("a30-run")

    assert result.completed is True
    scope_step = next(s for s in result.steps if s.label == "audit_scope")
    prompt = scope_step.prompt_text
    assert prompt is not None
    # The fragment body is present (the step's own fragment, selector-composed).
    assert "Audit scope" in prompt
    # The selector-resolved dynamic context (open_bugs) is present in the SAME prompt — the
    # context came from ContextSelector, not from any ctx-inject session-bootstrap side effect.
    assert "SELECTOR-MARKER-OPEN-BUG" in prompt


def test_no_ctx_inject_sentinel_created_by_running_a_lifecycle_workflow(tmp_path: Path) -> None:
    """The lifecycle prompt path never touches the ctx-inject sentinel (no side effect)."""
    _workspace(tmp_path)
    wf = _audit_workflow(tmp_path)
    wf.run("a30-side")

    tmp_dir = tmp_path / ".dadaia" / "tmp"
    sentinels = (
        [p for p in tmp_dir.iterdir() if p.name.startswith(_SENTINEL_PREFIX)]
        if tmp_dir.is_dir()
        else []
    )
    assert sentinels == [], "running a lifecycle workflow must not create a ctx-inject sentinel"


def test_lifecycle_prompt_does_not_carry_ctx_inject_bootstrap_banner(tmp_path: Path) -> None:
    """The hook's '=== workspace memory ===' bootstrap banner never leaks into a step prompt."""
    _workspace(tmp_path)
    wf = _audit_workflow(tmp_path)
    result = wf.run("a30-banner")

    for step in result.steps:
        if step.prompt_text is not None:
            assert "=== workspace memory (tech + catalog) ===" not in step.prompt_text
            assert "=== end memory bootstrap ===" not in step.prompt_text


# --- WS-C dehydration: the session bootstrap reduces a large tech-stack to a digest -------


def test_large_tech_stack_is_dehydrated_to_a_bounded_digest() -> None:
    big = "# tech-stack\n\n" + "\n".join(f"- dependency-{i} pinned" for i in range(200))
    digest = ctx_inject._digest_tech_stack(big)  # noqa: SLF001 — white-box digest assertion.
    # Strictly smaller than the source, and carries the self-pull pointer.
    assert len(digest) < len(big)
    assert "self-pull specs/memory/tech-stack.md" in digest
    # The leading content is preserved (orientation intact).
    assert "dependency-0 pinned" in digest
    # A deep line is dropped (genuinely bounded, not the full body).
    assert "dependency-199 pinned" not in digest


def test_small_tech_stack_is_emitted_verbatim() -> None:
    small = "# tech\nPython 3.12\nNode 20\n"
    digest = ctx_inject._digest_tech_stack(small)  # noqa: SLF001
    assert "Python 3.12" in digest
    assert "Node 20" in digest
    # No truncation pointer for a small atom.
    assert "self-pull" not in digest


def test_build_memory_uses_the_tech_stack_digest_not_the_full_body(tmp_path: Path) -> None:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    mem = specs / "memory" / "product"
    mem.mkdir(parents=True)
    big = "# tech-stack\n\n" + "\n".join(f"- dependency-{i} pinned" for i in range(200))
    (specs / "memory" / "tech-stack.md").write_text(big, encoding="utf-8")
    (mem / "catalog.json").write_text('{"features": []}', encoding="utf-8")

    out = ctx_inject._build_memory(specs)  # noqa: SLF001

    assert "=== end memory bootstrap ===" in out  # bind/session bootstrap contract intact.
    assert "dependency-0 pinned" in out
    assert "dependency-199 pinned" not in out  # the full body is NOT dumped.
    assert "self-pull specs/memory/tech-stack.md" in out
