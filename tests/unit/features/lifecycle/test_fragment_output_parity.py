"""Dual-parser harness-universal PRIMARY guarantee (WS-3 / T-24-07).

The behavioral guarantee that a fragment is genuinely harness-universal is that its
declared ``output_schema`` extracts to the **same** structured verdict whether the
worker ran under PI or under Codex. The two adapters use different native transports:

* ``PiHeadlessAdapter`` reads a line-delimited JSON event stream and pulls the verdict
  from a fenced ```json block (carrying a ``schema`` field) inside the last
  ``message_end`` event's assistant content.
* ``CodexExecAdapter`` reads the ``--output-last-message`` file as a single JSON object.

This test takes a verdict-bearing fragment schema (``spec-review-verdict-v1``: an
APPROVED/REJECTED verdict + fields), produces the EQUIVALENT worker output in each
adapter's native shape via FAKE runners, drives both through their public ``run()``,
and asserts the extracted structured verdict is identical. It PROVES (not assumes)
cross-harness parity for the fragment's output schema.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.lifecycle.fragments.loader import load_fragment
from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter, CodexExecConfig
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig

# The single logical verdict both adapters must extract identically.
_SCHEMA = "spec-review-verdict-v1"
_VERDICT = "APPROVED"
_SUMMARY = "SPEC respects layer boundaries; acceptance is testable."
_ARTIFACT_REFS = (".dadaia/handoff/dadaia-workspace/spec-review.handoff.json",)
_STRUCTURED = {"verdict": _VERDICT, "task_group": "spec_review_architecture"}


def _request(runtime: AgentRuntimeKind) -> AgentRunRequest:
    return AgentRunRequest(
        role="software-architect",
        prompt="review the spec draft",
        runtime=runtime,
        context="dadaia-workspace",
        release_id="v0.1.24",
        expected_schema=_SCHEMA,
    )


# -- PI native transport: fenced json inside a message_end event ----------


def _pi_fake_runner(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
    fenced = (
        "Verdict below.\n\n```json\n"
        + json.dumps(
            {
                "schema": _SCHEMA,
                "verdict": _VERDICT,
                "summary": _SUMMARY,
                "artifact_refs": list(_ARTIFACT_REFS),
                "structured_output": {"task_group": _STRUCTURED["task_group"]},
            }
        )
        + "\n```\n"
    )
    stream = "\n".join(
        [
            json.dumps({"type": "message_start"}),
            json.dumps(
                {
                    "type": "message_end",
                    "message": {"role": "assistant", "content": fenced},
                }
            ),
        ]
    )
    return subprocess.CompletedProcess(args=["pi"], returncode=0, stdout=stream, stderr="")


# -- Codex native transport: the --output-last-message JSON file ----------


def _codex_fake_runner_factory() -> object:
    def runner(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        # Honor the adapter's --output-last-message contract: write the verdict file.
        out_path = Path(args[args.index("--output-last-message") + 1])
        out_path.write_text(
            json.dumps(
                {
                    "summary": _SUMMARY,
                    "artifact_refs": list(_ARTIFACT_REFS),
                    "structured_output": dict(_STRUCTURED),
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    return runner


def _run_pi() -> AgentRunResult:
    adapter = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=Path("/tmp")),
        runner=_pi_fake_runner,
        environ={},
    )
    return adapter.run(_request(AgentRuntimeKind.PI_HEADLESS))


def _run_codex() -> AgentRunResult:
    adapter = CodexExecAdapter(
        CodexExecConfig(cwd=Path("/tmp"), model="gpt-5.5", reasoning_effort="high"),
        runner=_codex_fake_runner_factory(),
        environ={},
    )
    return adapter.run(_request(AgentRuntimeKind.CODEX_EXEC))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_verdict_bearing_fragment_exists_with_expected_schema() -> None:
    fragment = load_fragment("release_definition.spec_review_architecture")
    assert fragment.output_schema == _SCHEMA


def test_both_adapters_succeed() -> None:
    assert _run_pi().status is AgentRunStatus.SUCCEEDED
    assert _run_codex().status is AgentRunStatus.SUCCEEDED


def test_dual_parser_extracts_identical_verdict() -> None:
    pi = _run_pi()
    codex = _run_codex()
    # The verdict — the load-bearing field of the schema — must be identical.
    assert pi.structured_output.get("verdict") == _VERDICT
    assert codex.structured_output.get("verdict") == _VERDICT
    assert pi.structured_output.get("verdict") == codex.structured_output.get("verdict")


def test_dual_parser_extracts_identical_structured_result() -> None:
    pi = _run_pi()
    codex = _run_codex()
    assert pi.summary == codex.summary == _SUMMARY
    assert pi.artifact_refs == codex.artifact_refs == _ARTIFACT_REFS
    assert pi.structured_output.get("task_group") == codex.structured_output.get("task_group")
    # Full structured-output parity for the schema's fields.
    assert pi.structured_output == codex.structured_output


@pytest.mark.parametrize("verdict", ["APPROVED", "REJECTED"])
def test_parity_holds_for_either_verdict_value(verdict: str) -> None:
    # Rebuild fakes parameterized on the verdict value to prove parity is not
    # specific to APPROVED.
    def pi_runner(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        fenced = (
            "```json\n"
            + json.dumps({"schema": _SCHEMA, "verdict": verdict, "summary": _SUMMARY})
            + "\n```\n"
        )
        stream = json.dumps(
            {"type": "message_end", "message": {"role": "assistant", "content": fenced}}
        )
        return subprocess.CompletedProcess(args=["pi"], returncode=0, stdout=stream, stderr="")

    def codex_runner(args: list[str], **_k: object) -> subprocess.CompletedProcess[str]:
        out_path = Path(args[args.index("--output-last-message") + 1])
        out_path.write_text(
            json.dumps({"summary": _SUMMARY, "structured_output": {"verdict": verdict}}),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    pi = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=Path("/tmp")), runner=pi_runner, environ={}
    ).run(_request(AgentRuntimeKind.PI_HEADLESS))
    codex = CodexExecAdapter(
        CodexExecConfig(cwd=Path("/tmp"), model="gpt-5.5", reasoning_effort="high"),
        runner=codex_runner,
        environ={},
    ).run(_request(AgentRuntimeKind.CODEX_EXEC))

    assert pi.structured_output.get("verdict") == verdict
    assert codex.structured_output.get("verdict") == verdict
    assert pi.structured_output.get("verdict") == codex.structured_output.get("verdict")
