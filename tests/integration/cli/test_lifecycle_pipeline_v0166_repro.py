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
            "--skip-preflight",
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


def test_pi_pipeline_fr2_tolerant_schema_accept_and_noop_negative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC2(repro) + AC2(repro-negative), merged: two invocations sharing
    ``_patch_pi_runner``.

    (1) bug lifecycle-agent-run-result-extraction-too-strict: a faked pi worker emits a
    result object keyed ``schema_version`` (not ``schema``) with a singular
    ``artifact.path`` (not an ``artifact_refs`` list) — both real, tolerable shapes per
    FR2. On current (buggy) code ``classify_result_payload`` only recognizes ``schema``
    and ``normalize_artifact_refs`` only reads ``artifact_refs``, so the payload is
    rejected entirely and the pipeline blocks at ``implement`` with "agent result
    missing artifact evidence". After the fix the step must ACCEPT (the verdict gate
    does not apply — ``implement`` is a create step, not review).

    (2) the no-op-worker invariant survives the FR2 widening: a faked pi worker emits
    ONLY prose — no JSON result object at all. ``extract_result_payload`` still returns
    ``None``, so ``artifact_refs`` stays empty and the pipeline still BLOCKs at
    ``implement`` with the EXACT generic "agent result missing artifact evidence"
    reason.
    """
    accept_calls: list[object] = []
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

    def fake_pi_run_accept(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        accept_calls.append(args)
        return _subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_message_end_stdout(worker_payload),
            stderr="",
        )

    _patch_pi_runner(monkeypatch, fake_pi_run_accept)
    _stub_git_diff(monkeypatch)

    accept_workspace = _init_workspace(tmp_path / "accept-case")
    monkeypatch.chdir(accept_workspace)
    # A REAL worker writes its artifact; the faked subprocess can't, so materialize it —
    # the gate now verifies declared refs EXIST (bug gate-accepts-phantom-artifact-evidence).
    impl_ref = accept_workspace / ".dadaia" / "handoff" / "dadaia-workspace" / "impl.handoff.json"
    impl_ref.parent.mkdir(parents=True, exist_ok=True)
    impl_ref.write_text('{"fake": true}\n', encoding="utf-8")

    accept_result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--skip-preflight",
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
    # negative case below does not apply here.
    assert len(accept_calls) >= 1, "the faked pi subprocess seam must have been invoked"
    accept_payload = json.loads(accept_result.output)
    assert accept_payload["steps"][0]["label"] == "implement"
    assert accept_payload["steps"][0]["runtime"] == "pi_headless"
    assert accept_payload["steps"][0]["accepted"] is True, accept_payload

    negative_calls: list[object] = []

    def fake_pi_run_negative(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        negative_calls.append(args)
        return _subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=_message_end_stdout("I had nothing structured to emit."),
            stderr="",
        )

    _patch_pi_runner(monkeypatch, fake_pi_run_negative)
    _stub_git_diff(monkeypatch)

    negative_workspace = _init_workspace(tmp_path / "negative-case")
    monkeypatch.chdir(negative_workspace)

    negative_result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--skip-preflight",
            "--release-id",
            "v0166-fr2-repro-negative",
            "--run-id",
            "pipe-fr2-repro-negative",
            "--harness",
            "pi",
            "--json",
        ],
    )

    assert len(negative_calls) == 1, "the faked pi subprocess seam must be invoked exactly once"
    assert negative_result.exit_code == 3, negative_result.output
    negative_payload = json.loads(negative_result.output)
    assert negative_payload["status"] == "BLOCKED"
    assert negative_payload["completed"] is False
    assert negative_payload["steps"][0]["label"] == "implement"
    assert negative_payload["steps"][0]["accepted"] is False
    assert negative_payload["blocked"]["reason"] == "agent result missing artifact evidence"


# ---------------------------------------------------------------------------
# FR8 (T-66-06) — precise upstream failure detail enrichment.
# ---------------------------------------------------------------------------


def test_pipeline_block_detail_carries_validated_handoff_path_when_refs_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC8(repro) — bug: (observability NFR, cross-cutting; DEC-A(iii)).

    **INVERTED for v0.1.68 FR1 (SPEC FR1.5 / architect F2).** The v0.1.66 FR8
    enrichment this test originally pinned — surfacing a role-keyed disk-glob match
    as ``detail["validated_handoff_path"]`` — is exactly the
    ``lifecycle-pipeline-selects-stale-unrelated-handoff`` defect: the glob is keyed
    ONLY on ``(context, role)``, carries no run_id/step, and so returns an ARBITRARY
    historical handoff by that role rather than anything produced by the current
    run's current step. It can never be made run-scoped (handoff files carry no
    run/step identity; the step-payload ledger is a different data plane), so v0.1.68
    REMOVES the enrichment rather than repairing it. This test now asserts the
    corrected invariant: even with a genuinely valid, independently-validating
    handoff file pre-existing on disk at the exact path the OLD enrichment would have
    matched, the block detail carries NO ``validated_handoff_path`` referencing it —
    only the honest ``no_current_artifact`` marker. The run is still BLOCKED, exactly
    as before (FR2's no-op invariant is untouched by this correction).
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
    # path the RETIRED FR8 enrichment used to match: <workspace>/.dadaia/handoff/<context>/
    # named per the emitter convention <UTC>-<agent>-<slug>.handoff.json,
    # agent=software-engineer (the `implement` step's role, per implementation_ladder()).
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
            "--skip-preflight",
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
    # The run is STILL blocked — the FR1 correction only removes the (mis)enrichment.
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    assert payload["blocked"]["reason"] == "agent result missing artifact evidence"
    stale_rel_path = ".dadaia/handoff/dadaia-workspace/2026-07-08T150000Z-software-engineer-pipe-fr8-repro.handoff.json"
    detail = payload["blocked"]["detail"]
    assert "validated_handoff_path" not in detail, (
        f"the retired FR8 disk-glob must never surface a handoff path again; got {detail!r}"
    )
    assert detail.get("no_current_artifact") == "pipe-fr8-repro:implement"
    # Never any reference to the pre-existing stale file's path anywhere in detail.
    assert stale_rel_path not in detail.values()
