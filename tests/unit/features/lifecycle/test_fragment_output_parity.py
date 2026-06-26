"""Dual-parser harness-universal PRIMARY guarantee (WS-3 / T-24-07).

The behavioral guarantee that a fragment is genuinely harness-universal is that its
declared ``output_schema`` extracts to the **same** structured verdict whether the
worker ran under PI or under Codex. The two adapters use different native transports:

* ``PiHeadlessAdapter`` reads a line-delimited JSON event stream and pulls the verdict
  from a fenced ```json block (carrying a ``schema`` field) inside the last
  ``message_end`` event's assistant content.
* ``CodexExecAdapter`` reads the ``--output-last-message`` file as a single JSON object.

This test takes EVERY structured-output schema shipped by the release_definition
fragments — the three review-verdict schemas and the four draft/handoff schemas —
produces the EQUIVALENT worker output in each adapter's native shape via FAKE runners,
drives both through their public ``run()``, and asserts the extracted structured
output is identical. It PROVES (not assumes) cross-harness parity for *each shipped
fragment's* output schema, so the WS-3 "each shipped fragment" claim is actually
backed rather than demonstrated on a single schema.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.lifecycle.fragments.loader import list_fragments, load_fragment
from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter, CodexExecConfig
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig

_SUMMARY = "SPEC respects layer boundaries; acceptance is testable."
_ARTIFACT_REFS = (".dadaia/handoff/dadaia-workspace/step.handoff.json",)

#: The structured output schemas shipped by the release_definition fragments, each paired
#: with a canonical structured payload a worker would emit for that schema. The payload
#: keys mirror the schema's load-bearing fields; values are kept as strings because both
#: adapters stringify structured_output values during extraction. Every value the
#: fragment workflow reads downstream lives in ``structured_output`` so the two native
#: transports extract a byte-identical dict.
_SCHEMA_PAYLOADS: dict[str, dict[str, str]] = {
    # review-verdict schemas
    "spec-review-verdict-v1": {"verdict": "APPROVED", "task_group": "spec_review_architecture"},
    "plan-review-verdict-v1": {"verdict": "REJECTED", "task_group": "plan_review"},
    "tasks-review-verdict-v1": {"verdict": "APPROVED", "task_group": "tasks_review"},
    # draft / handoff schemas
    "release-scope-handoff-v1": {"verdict": "APPROVED", "scope_id": "scope-1"},
    "release-spec-draft-v1": {"verdict": "APPROVED", "draft": "spec"},
    "release-plan-draft-v1": {"verdict": "APPROVED", "draft": "plan"},
    "release-tasks-draft-v1": {"verdict": "APPROVED", "draft": "tasks"},
}


def test_every_release_definition_schema_is_covered() -> None:
    """The parametrization must cover EVERY output schema the shipped fragments declare.

    Derives the set straight from the packaged release_definition fragments so the
    coverage claim cannot silently drift from the real library.
    """
    shipped = {f.output_schema for f in list_fragments(workflow="release_definition")}
    covered = set(_SCHEMA_PAYLOADS)
    missing = shipped - covered
    assert not missing, f"shipped release_definition schemas not covered by parity test: {missing}"


def test_each_shipped_schema_maps_to_a_loadable_fragment() -> None:
    # Sanity: every schema we parametrize over is genuinely declared by a shipped fragment.
    shipped = {f.output_schema for f in list_fragments(workflow="release_definition")}
    for schema in _SCHEMA_PAYLOADS:
        assert schema in shipped, f"{schema} is not declared by any release_definition fragment"


def _request(runtime: AgentRuntimeKind, schema: str) -> AgentRunRequest:
    return AgentRunRequest(
        role="software-architect",
        prompt="produce the structured output",
        runtime=runtime,
        context="dadaia-workspace",
        release_id="v0.1.24",
        expected_schema=schema,
    )


# -- PI native transport: fenced json inside a message_end event ----------


def _pi_runner(schema: str, payload: Mapping[str, str]) -> object:
    def runner(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        fenced = (
            "Verdict below.\n\n```json\n"
            + json.dumps(
                {
                    "schema": schema,
                    "summary": _SUMMARY,
                    "artifact_refs": list(_ARTIFACT_REFS),
                    "structured_output": dict(payload),
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

    return runner


# -- Codex native transport: the --output-last-message JSON file ----------


def _codex_runner(payload: Mapping[str, str]) -> object:
    def runner(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        out_path = Path(args[args.index("--output-last-message") + 1])
        out_path.write_text(
            json.dumps(
                {
                    "summary": _SUMMARY,
                    "artifact_refs": list(_ARTIFACT_REFS),
                    "structured_output": dict(payload),
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    return runner


def _run_pi(schema: str, payload: Mapping[str, str]) -> AgentRunResult:
    adapter = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=Path("/tmp")),
        runner=_pi_runner(schema, payload),
        environ={},
    )
    return adapter.run(_request(AgentRuntimeKind.PI_HEADLESS, schema))


def _run_codex(schema: str, payload: Mapping[str, str]) -> AgentRunResult:
    adapter = CodexExecAdapter(
        CodexExecConfig(cwd=Path("/tmp"), model="gpt-5.5", reasoning_effort="high"),
        runner=_codex_runner(payload),
        environ={},
    )
    return adapter.run(_request(AgentRuntimeKind.CODEX_EXEC, schema))


# ---------------------------------------------------------------------------
# Single-schema sanity (the historical spec-review fragment).
# ---------------------------------------------------------------------------


def test_verdict_bearing_fragment_exists_with_expected_schema() -> None:
    fragment = load_fragment("release_definition.spec_review_architecture")
    assert fragment.output_schema == "spec-review-verdict-v1"


# ---------------------------------------------------------------------------
# Dual-parser parity across EVERY shipped schema.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("schema", sorted(_SCHEMA_PAYLOADS))
def test_both_adapters_succeed(schema: str) -> None:
    payload = _SCHEMA_PAYLOADS[schema]
    assert _run_pi(schema, payload).status is AgentRunStatus.SUCCEEDED
    assert _run_codex(schema, payload).status is AgentRunStatus.SUCCEEDED


@pytest.mark.parametrize("schema", sorted(_SCHEMA_PAYLOADS))
def test_dual_parser_extracts_identical_structured_output(schema: str) -> None:
    payload = _SCHEMA_PAYLOADS[schema]
    pi = _run_pi(schema, payload)
    codex = _run_codex(schema, payload)
    # The summary and artifact refs are extracted identically...
    assert pi.summary == codex.summary == _SUMMARY
    assert pi.artifact_refs == codex.artifact_refs == _ARTIFACT_REFS
    # ...and the full structured output is byte-identical across the two native transports.
    assert pi.structured_output == codex.structured_output
    # Every declared field of the schema reached both extractions.
    for key, value in payload.items():
        assert pi.structured_output.get(key) == value
        assert codex.structured_output.get(key) == value


@pytest.mark.parametrize("verdict", ["APPROVED", "REJECTED"])
def test_parity_holds_for_either_verdict_value(verdict: str) -> None:
    # Parity is not specific to APPROVED: drive the spec-review schema on both verdicts.
    schema = "spec-review-verdict-v1"
    payload = {"verdict": verdict, "task_group": "spec_review_architecture"}
    pi = _run_pi(schema, payload)
    codex = _run_codex(schema, payload)
    assert pi.structured_output.get("verdict") == verdict
    assert codex.structured_output.get("verdict") == verdict
    assert pi.structured_output == codex.structured_output
