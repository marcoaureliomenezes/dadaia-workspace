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

import json
from dataclasses import dataclass, replace
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
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_RELEASE = "v0.1.16"
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

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        # The structural gate verifies declared refs EXIST and that a create step
        # delivers INSIDE its declared zone (bugs gate-accepts-phantom-artifact-evidence
        # / create-step-gate-accepts-refusal-handoff-as-success): be step-aware and
        # materialize like the production driving fake.
        label = (request.task_id or "").rsplit(":", 1)[-1]
        deliverable = {
            "spec_create": "SPEC.md",
            "plan_create": "PLAN.md",
            "tasks_create": "TASKS.md",
        }.get(label)
        refs = list(self.result.artifact_refs)
        if deliverable is not None:
            zone = Path.cwd() / "repos" / _CONTEXT / "specs"
            prefix = f"repos/{_CONTEXT}/specs" if zone.is_dir() else "specs"
            refs.append(f"{prefix}/releases/{_RELEASE}/{deliverable}")
        for ref in refs:
            target = Path.cwd() / ref
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                body = '{"fake": true}\n'
                if target.name == "PLAN.md":
                    body = (
                        "# PLAN\n\n"
                        "## Validation Dependency Table\n\n"
                        "| Workstream | Produces by end | Direct validation | "
                        "Validation dependencies | Deferred integration evidence |\n"
                        "|---|---|---|---|---|\n"
                        "| WS-1 | fake artifact | focused test | None | None |\n"
                    )
                target.write_text(body, encoding="utf-8")
        return replace(self.result, artifact_refs=tuple(refs))


def _approving_result() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake worker: APPROVED",
        artifact_refs=(
            f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/release-definition-step.step-output.json",
        ),
        structured_output={"verdict": "APPROVED"},
    )


def _rejecting_result() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake worker: REJECTED",
        artifact_refs=(
            f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/release-definition-step.step-output.json",
        ),
        structured_output={"verdict": "REJECTED"},
    )


def _install_fake_factory(
    monkeypatch: pytest.MonkeyPatch,
    *,
    reject_kind: AgentRuntimeKind | None = None,
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
        release_id: str | None = None,  # noqa: ARG001
    ) -> object:
        def factory(kind: AgentRuntimeKind) -> _KindReportingFake:
            if reject_kind is not None and kind is reject_kind:
                return _KindReportingFake(kind, _rejecting_result())
            return _KindReportingFake(kind, _approving_result())

        return factory

    monkeypatch.setattr(container, "_release_definition_runtime_factory", fake_factory)


def _define(args: list[str]) -> Result:
    return _runner.invoke(
        app,
        [
            "lifecycle",
            "release-definition",
            "--release-id",
            _RELEASE,
            "--json",
            *args,
        ],
    )


def test_release_scope_consumes_exact_backlog_author_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace.cli.commands.lifecycle import _authoritative_backlog_prefix
    from dadaia_workspace.core.models.lifecycle import (
        LifecyclePhase,
        LifecycleRun,
        LifecycleRunStatus,
    )

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv(
        "DADAIA_CONTEXT", "dadaia-workspace"
    )  # explicit rung (no first-ALIVE/terminal fallback)
    handoff_ref = f".dadaia/handoff/{_CONTEXT}/author.handoff.json"
    handoff = workspace / handoff_ref
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text(
        json.dumps(
            {
                "artifact": {
                    "type": "other",
                    "path": "specs/backlog/deterministic-tetris-engine.md",
                }
            }
        ),
        encoding="utf-8",
    )
    run = LifecycleRun(
        run_id="tetris-backlog-run",
        context=_CONTEXT,
        release_id=_RELEASE,
        command="backlog_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.COMPLETED,
        current_step="backlog_review_gate",
        idempotency_key="tetris-backlog-run",
    )
    store = container.build_lifecycle_run_store(workspace)
    store.save(run)
    resolver = container.build_workflow_handoff_resolver(workspace)
    resolver.produce(
        run,
        producer_step="backlog_author",
        attempt=0,
        output_schema="backlog-item-v1",
        payload={"summary": "authored tetris", "artifact_refs": [handoff_ref]},
    )

    prefix = _authoritative_backlog_prefix(
        workspace,
        context=_CONTEXT,
        release_id=_RELEASE,
        backlog_run_id="tetris-backlog-run",
    )

    assert prefix is not None
    assert "Exact producer run: `tetris-backlog-run`" in prefix.text
    assert "`specs/backlog/deterministic-tetris-engine.md`" in prefix.text
    assert "must not substitute a different candidate" in prefix.text


# 3 -- rejected review blocks advancement -----------------------------------


def test_rejected_review_blocks_before_commit_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A REJECTED verdict at spec_review stops the run before the commit gate
    (after the single bounded in-run revision of spec_create is spent)."""
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv(
        "DADAIA_CONTEXT", "dadaia-workspace"
    )  # explicit rung (no first-ALIVE/terminal fallback)

    # Drive spec_review on a distinct harness (codex) and make that kind reject;
    # every other step (on the default pi harness, also fake-backed) approves. Python —
    # not the model — decides the block.
    _install_fake_factory(monkeypatch, reject_kind=AgentRuntimeKind.CODEX_EXEC)

    result = _define(["--harness", "pi", "--step-harness", "spec_review=codex"])

    assert result.exit_code == 3, result.output
    payload = _payload(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    # The release never advanced to IMPLEMENTATION.
    assert payload["final_phase"] != "implementation"
    steps = payload["steps"]
    assert isinstance(steps, list)
    labels = [step["label"] for step in steps]
    assert labels[-1] == "spec_review"
    assert "definition_commit_gate" not in labels
    assert steps[-1]["accepted"] is False
    blocked = payload["blocked"]
    assert isinstance(blocked, dict)


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

    The single-harness baseline below IS the full happy-path proof (all 7 model steps +
    terminal Python commit gate, release advances to IMPLEMENTATION) — absorbing the
    former standalone happy-path test. Fragment-scoped (non-generic) prompt assertions
    are folded in as this fn already builds workflow objects directly.
    """
    from dadaia_workspace.features.lifecycle.workflows.release_definition import _SEQUENCE

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv(
        "DADAIA_CONTEXT", "dadaia-workspace"
    )  # explicit rung (no first-ALIVE/terminal fallback)
    _install_fake_factory(monkeypatch)

    # Single-harness baseline: everything on pi. This IS the full happy-path proof: all 7
    # model steps + the terminal Python commit gate ran, release advances to IMPLEMENTATION.
    baseline = _define(["--harness", "pi", "--run-id", "adjacent-baseline"])
    assert baseline.exit_code == 0, baseline.output
    baseline_payload = _payload(baseline.output)
    assert baseline_payload["status"] == "OK"
    assert baseline_payload["completed"] is True
    assert baseline_payload["final_phase"] == "implementation"
    baseline_labels = [step["label"] for step in baseline_payload["steps"]]
    assert baseline_labels == [
        "release_scope",
        "spec_create",
        "spec_review",
        "plan_create",
        "plan_review",
        "tasks_create",
        "tasks_implementability_review",
        "definition_commit_gate",
    ]
    baseline_commit_gate = baseline_payload["steps"][-1]
    assert baseline_commit_gate["label"] == "definition_commit_gate"
    assert baseline_commit_gate["is_gate"] is True
    assert baseline_commit_gate["accepted"] is True

    # Mixed: release_scope on pi, adjacent spec_create on codex — real --step-harness path.
    # Distinct run id: the completed-rerun guard refuses re-using the baseline's id.
    mixed = _define(
        ["--harness", "pi", "--step-harness", "spec_create=codex", "--run-id", "adjacent-mixed"]
    )
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
    # The completed-rerun guard (bug completed-workflow-rerun-not-refused) refuses a
    # fresh run over a COMPLETED id, so drop the first run's record before the second.
    out_pi = wf_pi.run("seam-identity")
    store = container.build_lifecycle_run_store(workspace)
    next(store.root.glob("*seam-identity*")).unlink()
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

    # Scoped (non-generic) fragment prompts: at least one step prompt carries
    # fragment-sourced content; no generic suffix. Reuses the wf_pi/out_pi run built above.
    scope_step = next(s for s in out_pi.steps if s.label == "release_scope")
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
    for step in out_pi.steps:
        if step.prompt_text is None:
            continue
        assert f"Run the {step.label} step for release" not in step.prompt_text
        assert "Run the release-define step" not in step.prompt_text
    # Sanity: every model step in the sequence emitted a fragment-scoped prompt.
    model_labels = {s.label for s in _SEQUENCE if s.fragment_id is not None}
    emitted_with_prompt = {s.label for s in out_pi.steps if s.prompt_text is not None}
    assert model_labels <= emitted_with_prompt
