"""T-24-10 — release-definition workflow e2e (FAKE) + adjacent-harness seam (WS-5).

CLI-level integration test driving ``lifecycle release define`` end-to-end on the
FAKE-backed sequence. It proves the four §8.5 / DoD assertions:

1. **Full happy path** — the §6.1 sequence walks all 8 model steps + the terminal
   Python ``definition_commit_gate`` and advances the release to IMPLEMENTATION.
2. **Scoped (non-generic) prompts** — at least one emitted step prompt carries
   fragment-sourced content (a ``fragment:release_definition.<step>`` id + the coherent
   ``schema = agent-run-result-v1`` output contract, NOT the domain schema as a competing
   emit target) and the generic ``"Run the … step"`` suffix never appears.
3. **Rejected review blocks** — a REJECTED verdict at a review step stops the sequence
   before ``definition_commit_gate`` and the release does NOT reach IMPLEMENTATION.
4. **Adjacent-harness seam (the key §8.5 assertion)** — two *different* harnesses run on
   adjacent steps (default ``--harness pi`` with one step overridden via the real
   ``--step-harness <label>=codex`` flag, both FAKE-backed in the test). The test asserts
   (a) both steps assemble the SAME fragment bundle for their role (harness-independent),
   (b) both pass through the same Python gate logic, and (c) the run completes identically
   to the single-harness path. This proves a step is harness-portable — no lock-in.

The adjacent-harness seam exercises the real ``--step-harness`` CLI path (which *does*
support per-step harness selection in the release-definition command — see
``cli/commands/lifecycle.py::release_define``). To keep the test hermetic, the container's
release-definition runtime factory is monkeypatched so that *every* runtime kind
(``PI_HEADLESS``, ``CODEX_EXEC``, ``FAKE``) resolves to a deterministic in-process fake
that returns an APPROVED handoff **and reports its own kind** — so the kind genuinely
varies per step while no live worker is ever spawned.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

import dadaia_workspace.container as container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.lifecycle.prompt_builder import PromptPrefix
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    HEADLESS_WORKER_PROMPT_CHAR_BUDGET,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_RELEASE = "multiharness-engine-v0116"
_CONTEXT = "dadaia-workspace"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _payload(output: str) -> dict[str, object]:
    payload = json.loads(output)
    assert isinstance(payload, dict)
    return payload


@dataclass
class _KindReportingFake:
    """A FAKE-backed runtime that *reports a chosen kind* and a chosen verdict.

    ``runtime_kind`` returns the requested kind verbatim — so the prompt builder and the
    run record see the per-step harness the operator selected — while ``run`` never
    touches a live worker. This is what makes the adjacent-harness seam test hermetic:
    PI_HEADLESS and CODEX_EXEC both resolve here, no ``pi``/``codex`` process is spawned.
    """

    kind: AgentRuntimeKind
    result: AgentRunResult
    write_create_artifacts: bool = True
    reported_content_hash: str | None = None

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if not self.write_create_artifacts:
            return self.result
        artifact_ref = _write_create_artifact(request)
        if artifact_ref is None:
            return self.result
        content_hash = (
            self.reported_content_hash
            or hashlib.sha256((Path.cwd() / artifact_ref).read_bytes()).hexdigest()
        )
        return AgentRunResult(
            status=self.result.status,
            summary=self.result.summary,
            artifact_refs=(*self.result.artifact_refs, artifact_ref),
            structured_output={**self.result.structured_output, "content_hash": content_hash},
            error=self.result.error,
        )


def _write_create_artifact(request: AgentRunRequest) -> str | None:
    for allowed in request.allowed_paths:
        if not allowed.startswith("repos/") and not allowed.startswith("specs/"):
            continue
        if not allowed.endswith(("SPEC.md", "PLAN.md", "TASKS.md")):
            continue
        path = Path.cwd() / allowed
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# {path.name}\n\nGenerated for {request.task_id}.\n",
            encoding="utf-8",
        )
        return allowed
    return None


@dataclass
class _StaticFake:
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:  # noqa: ARG002
        return self.result


def _approving_result() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake worker: APPROVED",
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/release-definition-step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _rejecting_result() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake worker: REJECTED",
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/release-definition-step.handoff.json",),
        structured_output={"verdict": "REJECTED"},
    )


def _install_fake_factory(
    monkeypatch: pytest.MonkeyPatch,
    *,
    reject_kind: AgentRuntimeKind | None = None,
    write_create_artifacts: bool = True,
    reported_content_hash: str | None = None,
) -> None:
    """Make the real release-define CLI path drive every kind through a kind-reporting fake.

    Every ``AgentRuntimeKind`` (including the real-harness PI_HEADLESS / CODEX_EXEC values
    the CLI maps ``--harness pi`` / ``--step-harness …=codex`` onto) resolves to an
    in-process fake that reports that exact kind. ``reject_kind`` makes only that one kind
    return a REJECTED verdict, so a single review step can be made to block.
    """

    def fake_factory(
        *,
        context: str,  # noqa: ARG001
        run_cwd: Path,  # noqa: ARG001
        model_by_kind: dict[AgentRuntimeKind, object],  # noqa: ARG001
    ) -> object:
        def factory(kind: AgentRuntimeKind) -> _KindReportingFake:
            if reject_kind is not None and kind is reject_kind:
                return _KindReportingFake(
                    kind,
                    _rejecting_result(),
                    write_create_artifacts=write_create_artifacts,
                    reported_content_hash=reported_content_hash,
                )
            return _KindReportingFake(
                kind,
                _approving_result(),
                write_create_artifacts=write_create_artifacts,
                reported_content_hash=reported_content_hash,
            )

        return factory

    monkeypatch.setattr(container, "_release_definition_runtime_factory", fake_factory)


def _define(args: list[str]) -> Result:
    return _runner.invoke(
        app,
        [
            "lifecycle",
            "release",
            "define",
            "--release-id",
            _RELEASE,
            "--json",
            *args,
        ],
    )


def _define_release(release_id: str, args: list[str]) -> Result:
    return _runner.invoke(
        app,
        [
            "lifecycle",
            "release",
            "define",
            "--release-id",
            release_id,
            "--json",
            *args,
        ],
    )


# 1 -- full happy path ------------------------------------------------------


def test_full_sequence_reaches_commit_gate_and_advances(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch)

    result = _define(["--harness", "fake"])

    assert result.exit_code == 0, result.output
    payload = _payload(result.output)
    assert payload["status"] == "OK"
    assert payload["completed"] is True
    assert payload["final_phase"] == "implementation"
    steps = payload["steps"]
    assert isinstance(steps, list)
    labels = [step["label"] for step in steps]
    # All 8 model steps + the terminal Python commit gate ran.
    assert labels == [
        "release_scope",
        "spec_create",
        "spec_arch_review",
        "spec_qa_review",
        "plan_create",
        "plan_review",
        "tasks_create",
        "tasks_implementability_review",
        "definition_commit_gate",
    ]
    commit_gate = steps[-1]
    assert commit_gate["label"] == "definition_commit_gate"
    assert commit_gate["is_gate"] is True
    assert commit_gate["accepted"] is True


def test_release_definition_blocks_oversized_worker_prompt_before_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch)
    workflow = container.build_release_definition_workflow(
        workspace,
        context=_CONTEXT,
        release_id=_RELEASE,
        default_runtime_kind=AgentRuntimeKind.FAKE,
        prefix=PromptPrefix(
            text="x" * (HEADLESS_WORKER_PROMPT_CHAR_BUDGET + 1),
            content_hash="oversized",
        ),
    )

    outcome = workflow.run("oversized-prompt")

    assert outcome.completed is False
    assert outcome.blocked is not None
    assert outcome.blocked.blocked_at_step == "release_scope"
    assert "worker prompt exceeds headless runtime budget" in outcome.blocked.reason
    assert outcome.blocked.detail["max_chars"] == str(HEADLESS_WORKER_PROMPT_CHAR_BUDGET)


def test_cli_fake_runtime_writes_canonical_create_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _define(["--harness", "fake"])

    assert result.exit_code == 0, result.output
    assert (workspace / "specs" / "releases" / _RELEASE / "SPEC.md").is_file()
    assert (workspace / "specs" / "releases" / _RELEASE / "PLAN.md").is_file()
    assert (workspace / "specs" / "releases" / _RELEASE / "TASKS.md").is_file()


def test_release_definition_spec_create_injects_only_selected_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch)
    backlog = workspace / "specs" / "backlog"
    bugs = workspace / "specs" / "bugs"
    backlog.mkdir(parents=True, exist_ok=True)
    bugs.mkdir(parents=True, exist_ok=True)
    (backlog / "picked-scope.md").write_text(
        "---\nname: picked-scope\nstatus: candidate\n---\n# Picked\n",
        encoding="utf-8",
    )
    (backlog / "not-picked.md").write_text(
        "---\nname: not-picked\nstatus: candidate\n---\n# Not picked\n",
        encoding="utf-8",
    )
    (bugs / "picked-bug.md").write_text(
        "---\nname: picked-bug\nstatus: Open\n---\n# Picked bug\n",
        encoding="utf-8",
    )
    (bugs / "not-picked-bug.md").write_text(
        "---\nname: not-picked-bug\nstatus: Open\n---\n# Not picked bug\n",
        encoding="utf-8",
    )

    result = _define(
        [
            "--harness",
            "fake",
            "--run-id",
            "selected-scope",
            "--backlog",
            "picked-scope",
            "--bug",
            "picked-bug",
        ]
    )

    assert result.exit_code == 0, result.output
    run_payload = json.loads(
        (workspace / ".dadaia" / "states" / "lifecycle" / "selected-scope.json").read_text()
    )
    run = run_payload["run"]
    spec_create = next(
        item for item in run["injected_context"] if item["step"] == "spec_create"
    )
    refs = set(spec_create["refs"])
    assert "specs/backlog/picked-scope.md" in refs
    assert "specs/bugs/picked-bug.md" in refs
    assert "specs/backlog/not-picked.md" not in refs
    assert "specs/bugs/not-picked-bug.md" not in refs


def test_release_definition_uses_python_hash_when_worker_reports_wrong_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch, reported_content_hash="not-a-real-sha256")

    result = _define(["--harness", "fake"])

    assert result.exit_code == 0, result.output
    payload = _payload(result.output)
    assert payload["status"] == "OK"
    spec_path = workspace / "specs" / "releases" / _RELEASE / "SPEC.md"
    assert spec_path.is_file()
    assert hashlib.sha256(spec_path.read_bytes()).hexdigest() != "not-a-real-sha256"


def test_release_definition_rejects_traversal_release_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _define_release("../outside", ["--harness", "fake"])

    assert result.exit_code != 0
    assert not (workspace.parent / "outside").exists()


# 2 -- scoped (non-generic) fragment prompts --------------------------------


def test_emitted_prompts_are_fragment_scoped_not_generic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At least one step prompt carries fragment-sourced content; no generic suffix."""
    from dadaia_workspace.features.lifecycle.workflows.release_definition import _SEQUENCE

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch)

    # Build the same workflow the CLI builds and capture the emitted prompt text. (The
    # JSON envelope omits prompt_text by design; we inspect it via the workflow object,
    # which is the exact instance the CLI runs.)
    wf = container.build_release_definition_workflow(
        workspace,
        context=_CONTEXT,
        release_id=_RELEASE,
        default_runtime_kind=AgentRuntimeKind.FAKE,
    )
    outcome = wf.run("scoped-prompt-run")

    scope_step = next(s for s in outcome.steps if s.label == "release_scope")
    assert scope_step.prompt_text is not None
    # Fragment-sourced content: the explicit fragment id is present...
    assert "fragment:release_definition.release_scope" in scope_step.prompt_text
    # ...along with the coherent worker-output contract (v0.1.32 / D-1): the single
    # transport schema is the worker emit target via `schema`; the fragment's domain schema
    # is NOT surfaced as a competing schema-to-emit in the "## Required output" section.
    required = scope_step.prompt_text[scope_step.prompt_text.index("## Required output") :]
    assert "agent-run-result-v1" in required
    assert "release-scope-handoff-v1" not in required
    # ...and the generic "Run the {label} step for release …" suffix (pipeline.py) never
    # appears for ANY release-definition step.
    for step in outcome.steps:
        if step.prompt_text is None:
            continue
        assert f"Run the {step.label} step for release" not in step.prompt_text
        assert "Run the release-define step" not in step.prompt_text
    # Sanity: every model step in the sequence emitted a fragment-scoped prompt.
    model_labels = {s.label for s in _SEQUENCE if s.fragment_id is not None}
    emitted_with_prompt = {s.label for s in outcome.steps if s.prompt_text is not None}
    assert model_labels <= emitted_with_prompt


def test_release_scope_receives_explicit_operator_scope_not_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionScopeInput,
    )

    wf = container.build_release_definition_workflow(
        workspace,
        context=_CONTEXT,
        release_id=_RELEASE,
        default_runtime_kind=AgentRuntimeKind.FAKE,
        scope_input=ReleaseDefinitionScopeInput(
            intent="Harden release-definition workflow scope input.",
            backlog_slugs=("workflow-model-governance-operator-profiles-and-context-overlays",),
            bug_slugs=(
                "release-definition-lacks-operator-intent-channel-and-infers-scope-from-run-id",
            ),
            audit_refs=("audit-123",),
        ),
    )

    outcome = wf.run("misleading-default-model-run-id")

    scope_step = next(s for s in outcome.steps if s.label == "release_scope")
    assert scope_step.prompt_text is not None
    assert "### operator_scope" in scope_step.prompt_text
    assert "Harden release-definition workflow scope input." in scope_step.prompt_text
    assert "release-definition-lacks-operator-intent-channel-and-infers-scope-from-run-id" in (
        scope_step.prompt_text
    )
    assert "Treat run_id/task_id as opaque operational identifiers" in scope_step.prompt_text


def test_release_definition_threads_step_model_by_label_not_runtime_kind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    received: list[AgentRunRequest] = []

    @dataclass
    class RecordingFake(_KindReportingFake):
        def run(self, request: AgentRunRequest) -> AgentRunResult:
            received.append(request)
            return super().run(request)

    def fake_factory(
        *,
        context: str,  # noqa: ARG001
        run_cwd: Path,  # noqa: ARG001
        model_by_kind: dict[AgentRuntimeKind, object],  # noqa: ARG001
    ) -> object:
        def factory(kind: AgentRuntimeKind) -> RecordingFake:
            return RecordingFake(kind, _approving_result())

        return factory

    monkeypatch.setattr(container, "_release_definition_runtime_factory", fake_factory)

    result = _define(
        [
            "--harness",
            "pi",
            "--model",
            "gpt-5.5:high",
            "--step-model",
            "release_scope=gpt-5.5:low",
            "--step-model",
            "spec_create=gpt-5.3-codex-spark:medium",
        ]
    )

    assert result.exit_code == 0, result.output
    by_label = {req.task_id.rsplit(":", 1)[-1]: req for req in received}
    release_scope = by_label["release_scope"].resolved_model
    spec_create = by_label["spec_create"].resolved_model
    assert release_scope is not None
    assert spec_create is not None
    assert (release_scope.model, release_scope.reasoning) == ("gpt-5.5", "low")
    assert (spec_create.model, spec_create.reasoning) == ("gpt-5.3-codex-spark", "medium")


def test_release_definition_persists_injected_context_before_worker_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    store = container.build_lifecycle_run_store(workspace)

    @dataclass
    class InspectingFake(_KindReportingFake):
        def run(self, request: AgentRunRequest) -> AgentRunResult:
            assert request.task_id is not None
            run_id, _, step_label = request.task_id.partition(":")
            persisted = store.load(run_id)
            assert persisted is not None
            assert any(entry.step == step_label for entry in persisted.injected_context)
            assert persisted.active_worker is not None
            assert persisted.active_worker.step == step_label
            assert persisted.active_worker.runtime_kind == self.kind.value
            return super().run(request)

    def fake_factory(
        *,
        context: str,  # noqa: ARG001
        run_cwd: Path,  # noqa: ARG001
        model_by_kind: dict[AgentRuntimeKind, object],  # noqa: ARG001
    ) -> object:
        def factory(kind: AgentRuntimeKind) -> InspectingFake:
            return InspectingFake(kind, _approving_result())

        return factory

    monkeypatch.setattr(container, "_release_definition_runtime_factory", fake_factory)

    result = _define(["--harness", "pi"])

    assert result.exit_code == 0, result.output
    completed = store.load("release-define")
    assert completed is not None
    assert completed.active_worker is None


# 3 -- rejected review blocks advancement -----------------------------------


def test_rejected_review_blocks_before_commit_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A REJECTED verdict at spec_arch_review stops the run before the commit gate."""
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    # Drive spec_arch_review on a distinct harness (codex) and make that kind reject;
    # every other step (on the default pi harness, also fake-backed) approves. Python —
    # not the model — decides the block.
    _install_fake_factory(monkeypatch, reject_kind=AgentRuntimeKind.CODEX_EXEC)

    result = _define(["--harness", "pi", "--step-harness", "spec_arch_review=codex"])

    assert result.exit_code == 3, result.output
    payload = _payload(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    # The release never advanced to IMPLEMENTATION.
    assert payload["final_phase"] != "implementation"
    steps = payload["steps"]
    assert isinstance(steps, list)
    labels = [step["label"] for step in steps]
    assert labels[-1] == "spec_arch_review"
    assert "definition_commit_gate" not in labels
    assert steps[-1]["accepted"] is False
    blocked = payload["blocked"]
    assert isinstance(blocked, dict)


def test_handoff_only_spec_create_blocks_at_spec_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch, write_create_artifacts=False)

    result = _define(["--harness", "fake"])

    assert result.exit_code == 3, result.output
    payload = _payload(result.output)
    assert payload["status"] == "BLOCKED"
    steps = payload["steps"]
    assert isinstance(steps, list)
    assert steps[-1]["label"] == "spec_create"
    blocked = payload["blocked"]
    assert isinstance(blocked, dict)
    assert blocked["blocked_at_step"] == "spec_create"
    assert "missing canonical release artifact" in blocked["reason"]


# 4 -- adjacent-harness seam (the key §8.5 assertion) -----------------------


def test_adjacent_steps_on_different_harnesses_same_bundle_same_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§8.5: adjacent steps run on different harnesses, same bundle, same gate, same result.

    Default ``--harness pi`` runs every step on PI_HEADLESS; ``--step-harness
    spec_create=codex`` overrides the single ``spec_create`` step onto CODEX_EXEC — so
    ``release_scope`` (PI) and its adjacent ``spec_create`` (Codex) genuinely run on two
    different harnesses. Both are FAKE-backed via the monkeypatched factory.

    Proves no lock-in:
      (a) the SAME step assembles a byte-identical fragment bundle regardless of harness;
      (b) both harnesses pass through the same Python gate logic (both accepted);
      (c) the mixed-harness run completes identically to the single-harness path.
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    _install_fake_factory(monkeypatch)

    # Single-harness baseline: everything on pi.
    baseline = _define(["--harness", "pi"])
    assert baseline.exit_code == 0, baseline.output
    baseline_payload = _payload(baseline.output)

    # Mixed: release_scope on pi, adjacent spec_create on codex — real --step-harness path.
    mixed = _define(["--harness", "pi", "--step-harness", "spec_create=codex"])
    assert mixed.exit_code == 0, mixed.output
    mixed_payload = _payload(mixed.output)

    baseline_steps = baseline_payload["steps"]
    mixed_steps = mixed_payload["steps"]
    assert isinstance(baseline_steps, list) and isinstance(mixed_steps, list)
    by_label_baseline = {s["label"]: s for s in baseline_steps}
    by_label_mixed = {s["label"]: s for s in mixed_steps}

    # The two adjacent steps genuinely ran on two DIFFERENT harnesses in the mixed run.
    # The JSON envelope reports the AgentRuntimeKind value (pi -> pi_headless,
    # codex -> codex_exec).
    assert by_label_mixed["release_scope"]["runtime"] == AgentRuntimeKind.PI_HEADLESS.value
    assert by_label_mixed["spec_create"]["runtime"] == AgentRuntimeKind.CODEX_EXEC.value
    assert by_label_mixed["release_scope"]["runtime"] != by_label_mixed["spec_create"]["runtime"]

    # (a) SAME fragment bundle for the role regardless of harness: the bundle is keyed by
    # the step, not the runtime. spec_create's fragment id is identical pi-vs-codex.
    assert (
        by_label_mixed["spec_create"]["fragment_id"]
        == by_label_baseline["spec_create"]["fragment_id"]
        == "release_definition.spec_create"
    )

    # (a, stronger) byte-identical assembled prompt for the same step across harnesses —
    # the fragment bundle (body + shared + output schema) does not depend on the harness.
    # Build both directly to compare the assembled prompt text.
    wf_pi = container.build_release_definition_workflow(
        workspace,
        context=_CONTEXT,
        release_id=_RELEASE,
        default_runtime_kind=AgentRuntimeKind.PI_HEADLESS,
    )
    wf_codex = container.build_release_definition_workflow(
        workspace,
        context=_CONTEXT,
        release_id=_RELEASE,
        default_runtime_kind=AgentRuntimeKind.CODEX_EXEC,
    )
    # Same run_id for both so the only thing that could differ is the harness — proving
    # the assembled bundle is harness-independent (task_id is part of the prompt payload).
    out_pi = wf_pi.run("seam-identity")
    out_codex = wf_codex.run("seam-identity")
    bundle_pi = next(s for s in out_pi.steps if s.label == "spec_create").prompt_text
    bundle_codex = next(s for s in out_codex.steps if s.label == "spec_create").prompt_text
    assert bundle_pi is not None and bundle_codex is not None
    assert bundle_pi == bundle_codex  # harness-independent fragment bundle.

    # (b) both harnesses passed through the same Python gate logic — both accepted.
    assert by_label_mixed["spec_create"]["accepted"] is True
    assert by_label_mixed["release_scope"]["accepted"] is True

    # (c) the mixed-harness run completes identically to the single-harness path: same
    # labels, same accepted flags, same terminal phase.
    assert [s["label"] for s in mixed_steps] == [s["label"] for s in baseline_steps]
    assert [s["accepted"] for s in mixed_steps] == [s["accepted"] for s in baseline_steps]
    assert mixed_payload["final_phase"] == baseline_payload["final_phase"] == "implementation"
    assert mixed_payload["completed"] is baseline_payload["completed"] is True
