"""Executed-path reproduction tests for release v0.1.66 (Layer-2 Worker Path Remediation).

Every test here is named exactly as SPEC.md's ``AC-N(repro)``/``AC-N(repro-negative)``
criteria specify (traceability by name, not inference). Each drives the REAL production
entrypoint the user actually hit — ``dadaia lifecycle`` via ``CliRunner`` +
``dadaia_workspace.cli.main.app``, invoking the real ``container.build_agent_runtime`` /
``LifecycleAgentRunner`` / ``LifecycleStateMachine`` chain — with only the outermost I/O
boundary faked (the ``subprocess.run`` seam for the pi/codex adapters, or an injected
``FakeAgentRuntime`` result for engine-logic-only FRs). This file is a SIBLING of
``test_lifecycle_pipeline_cli.py`` per PLAN.md's judgment call (avoids waves A/B/C
colliding on one growing file).

Faking the pi subprocess seam — IMPORTANT gotcha (bug:
pi-e2e-test-false-positive-loose-blocked-reason-assertion, registered during this task):
``PiHeadlessAdapter.__init__`` declares ``runner: Runner = subprocess.run`` as a
KEYWORD-ONLY default. Python binds that default ONCE, to whatever function object
``subprocess.run`` resolves to at the moment the class body executes (first import of
``pi_runtime``) — not a live per-call lookup. ``container.build_agent_runtime`` never
passes an explicit ``runner=`` override, so ``monkeypatch.setattr("...pi_runtime.
subprocess.run", fake)`` does NOT redirect the adapter's actual subprocess call once the
module has already been imported anywhere in the test session (it silently falls through
to the REAL local ``pi`` binary). The deterministic, import-order-independent fix used
here: patch the bound keyword-default itself via
``monkeypatch.setitem(PiHeadlessAdapter.__init__.__kwdefaults__, "runner", fake)``. Every
test below also asserts the fake was invoked EXACTLY once and asserts on the EXACT
fake-derived content (never a truthy-only check) — closing the false-positive gap the
registered bug describes.
"""

from __future__ import annotations

import json
import subprocess as _subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _stub_git_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the Ring-2 git seam hermetic (no real repo in the temp workspace)."""
    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )


def _patch_pi_runner(
    monkeypatch: pytest.MonkeyPatch,
    fake_pi_run: object,
) -> None:
    """Deterministically redirect PiHeadlessAdapter's subprocess seam.

    See the module docstring: this patches the bound keyword-default directly
    (``PiHeadlessAdapter.__init__.__kwdefaults__["runner"]``), which is honored
    regardless of whether ``pi_runtime`` was already imported earlier in the test
    session — unlike ``monkeypatch.setattr("...pi_runtime.subprocess.run", ...)``,
    which only works if this is the FIRST import of the module in the process.
    """
    monkeypatch.setitem(PiHeadlessAdapter.__init__.__kwdefaults__, "runner", fake_pi_run)


def _message_end_stdout(content: str) -> str:
    events = [
        {"type": "message_start"},
        {"type": "message_end", "message": {"role": "assistant", "content": content}},
    ]
    return "\n".join(json.dumps(event) for event in events) + "\n"


# ---------------------------------------------------------------------------
# FR1 (T-66-04) — pi non-zero exit reported as FAILED, not the generic block.
# ---------------------------------------------------------------------------


def test_pi_pipeline_surfaces_real_setup_failure_not_generic_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC1(repro) — bug: pi-headless-nonzero-exit-misreported.

    A faked pi subprocess exits ``returncode=1`` with a non-empty JSONL
    session/event preamble on stdout (no usable ``message_end``) and a real,
    actionable stderr. On current (buggy) code
    ``PiHeadlessAdapter._result_from_output`` treats the non-empty stdout as a
    signal the run "completed" (``returncode != 0 and not text``), so the
    engine reports SUCCEEDED with empty ``artifact_refs`` and the pipeline
    blocks with the generic "agent result missing artifact evidence" message —
    the real setup failure is lost. After the fix, ANY non-zero returncode is
    FAILED and the block reason must carry the EXACT real stderr text.
    """
    calls: list[object] = []
    preamble_stdout = (
        "\n".join(
            [
                json.dumps({"type": "session_start", "session_id": "abc123"}),
                json.dumps({"type": "message_start"}),
            ]
        )
        + "\n"
    )

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        calls.append(args)
        return _subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout=preamble_stdout,
            stderr="No API key found for azure-openai-responses.",
        )

    _patch_pi_runner(monkeypatch, fake_pi_run)
    _stub_git_diff(monkeypatch)

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0166-fr1-repro",
            "--run-id",
            "pipe-fr1-repro",
            "--harness",
            "pi",
            "--json",
        ],
    )

    assert len(calls) == 1, "the faked pi subprocess seam must be invoked exactly once"
    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    assert payload["steps"][0]["runtime"] == "pi_headless"
    assert payload["steps"][0]["accepted"] is False
    # Tight assertion: the EXACT real stderr text must reach the operator — NOT the
    # flattened generic "agent result missing artifact evidence" message.
    assert payload["blocked"]["reason"] == "No API key found for azure-openai-responses."


# ---------------------------------------------------------------------------
# FR2 (T-66-05) — tolerant worker-result contract, no-op invariant preserved.
# ---------------------------------------------------------------------------


def test_pi_pipeline_accepts_schema_version_and_singular_artifact_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC2(repro) — bug: lifecycle-agent-run-result-extraction-too-strict.

    A faked pi worker emits a result object keyed ``schema_version`` (not
    ``schema``) with a singular ``artifact.path`` (not an ``artifact_refs``
    list) — both real, tolerable shapes per FR2. On current (buggy) code
    ``classify_result_payload`` only recognizes ``schema`` and
    ``normalize_artifact_refs`` only reads ``artifact_refs``, so the payload is
    rejected entirely and the pipeline blocks at ``implement`` with "agent
    result missing artifact evidence". After the fix the step must ACCEPT (the
    verdict gate does not apply — ``implement`` is a create step, not review).
    """
    calls: list[object] = []
    worker_payload = json.dumps(
        {
            "schema_version": "agent-run-result-v1",
            "status": "succeeded",
            "summary": "implemented via schema_version + singular artifact",
            "artifact": {
                "type": "other",
                "path": ".dadaia/handoff/dadaia-workspace/impl.handoff.json",
            },
        }
    )

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        calls.append(args)
        return _subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_message_end_stdout(worker_payload),
            stderr="",
        )

    _patch_pi_runner(monkeypatch, fake_pi_run)
    _stub_git_diff(monkeypatch)

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0166-fr2-repro",
            "--run-id",
            "pipe-fr2-repro",
            "--harness",
            "pi",
            "--json",
        ],
    )

    # The implement step ACCEPTS on this fix, so the pipeline advances into review_qa
    # (also faked pi) before blocking there — at least one call proves the fake, not
    # the real binary, drove the implement step; the exact-once assertion used by the
    # other (blocking-at-first-step) tests in this file does not apply here.
    assert len(calls) >= 1, "the faked pi subprocess seam must have been invoked"
    payload = json.loads(result.output)
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["runtime"] == "pi_headless"
    assert payload["steps"][0]["accepted"] is True, payload


def test_pi_pipeline_still_blocks_on_genuine_noop_worker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC2(repro-negative) — the no-op-worker invariant survives the FR2 widening.

    A faked pi worker emits ONLY prose — no JSON result object at all. This must
    PASS on current code (baseline proof the invariant already holds) AND continue
    to PASS after the fix: `extract_result_payload` still returns ``None``, so
    `artifact_refs` stays empty and the pipeline still BLOCKs at `implement` with
    the EXACT generic "agent result missing artifact evidence" reason. Driven
    through the real CLI so the proof covers the actual executed path, not just
    the unit-level classifier.
    """
    calls: list[object] = []

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        calls.append(args)
        return _subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_message_end_stdout("I had nothing structured to emit."),
            stderr="",
        )

    _patch_pi_runner(monkeypatch, fake_pi_run)
    _stub_git_diff(monkeypatch)

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0166-fr2-repro-negative",
            "--run-id",
            "pipe-fr2-repro-negative",
            "--harness",
            "pi",
            "--json",
        ],
    )

    assert len(calls) == 1, "the faked pi subprocess seam must be invoked exactly once"
    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["accepted"] is False
    assert payload["blocked"]["reason"] == "agent result missing artifact evidence"


# ---------------------------------------------------------------------------
# FR8 (T-66-06) — precise upstream failure detail enrichment.
# ---------------------------------------------------------------------------


def test_pipeline_block_detail_carries_validated_handoff_path_when_refs_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC8(repro) — bug: (observability NFR, cross-cutting; DEC-A(iii)).

    A faked pi worker result has empty ``artifact_refs`` (a genuine no-op, blocking
    exactly as FR2's invariant requires) but a genuinely valid, independently
    validating handoff file already exists on disk at the expected
    ``.dadaia/handoff/<context>/`` path for the step's context/agent naming
    convention. On current (buggy) code the block's ``detail`` dict is always
    ``{}``. After the DEC-A(iii) fix, ``detail["validated_handoff_path"]`` must
    equal that path — and the run must STILL be BLOCKED (this never converts a
    block into a pass).
    """
    calls: list[object] = []

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        calls.append(args)
        return _subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_message_end_stdout("I had nothing structured to emit."),
            stderr="",
        )

    _patch_pi_runner(monkeypatch, fake_pi_run)
    _stub_git_diff(monkeypatch)

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    # Pre-write a genuinely valid, independently-validating handoff file at the exact
    # path the FR8 enrichment must find: <workspace>/.dadaia/handoff/<context>/ named
    # per the emitter convention <UTC>-<agent>-<slug>.handoff.json, agent=software-engineer
    # (the `implement` step's role, per implementation_ladder()).
    handoff_dir = workspace / ".dadaia" / "handoff" / "dadaia-workspace"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = handoff_dir / "2026-07-08T150000Z-software-engineer-pipe-fr8-repro.handoff.json"
    handoff_doc = {
        "schema_version": "handoff-v1.1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-07-08T15:00:00Z",
        "scope": "T-66-06 FR8 repro fixture",
        "metrics": {},
        "artifact": {"type": "other"},
    }
    handoff_path.write_text(json.dumps(handoff_doc, indent=2), encoding="utf-8")

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0166-fr8-repro",
            "--run-id",
            "pipe-fr8-repro",
            "--harness",
            "pi",
            "--json",
        ],
    )

    assert len(calls) == 1, "the faked pi subprocess seam must be invoked exactly once"
    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    # The run is STILL blocked — FR8 is detail enrichment only, never a pass conversion.
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    assert payload["blocked"]["reason"] == "agent result missing artifact evidence"
    expected_rel_path = ".dadaia/handoff/dadaia-workspace/2026-07-08T150000Z-software-engineer-pipe-fr8-repro.handoff.json"
    assert payload["blocked"]["detail"]["validated_handoff_path"] == expected_rel_path
