"""Unit tests for the exec-backed Codex runtime adapter."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
)
from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter, CodexExecConfig


def _request(*, model_profile: str | None = "dispatch") -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="Do bounded work and return JSON.",
        runtime=AgentRuntimeKind.CODEX_EXEC,
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-17",
        model_profile=model_profile,
        allowed_paths=("src/**",),
        forbidden_paths=("secrets/**",),
        expected_schema="agent-run-result-v1",
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def test_codex_exec_adapter_builds_controlled_command_and_env(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        calls.append({"args": args, "kwargs": kwargs})
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(
            json.dumps(
                {
                    "summary": "done",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/qa.handoff.json"],
                    "structured_output": {"verdict": "APPROVED"},
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    adapter = CodexExecAdapter(
        CodexExecConfig(
            cwd=tmp_path,
            codex_bin="/usr/bin/codex",
            model="gpt-test",
            reasoning_effort="medium",
            sandbox="workspace-write",
        ),
        runner=fake_runner,
        environ={
            "PATH": "/bin",
            "HOME": "/home/operator",
            "OPENAI_API_KEY": "secret-key",
            "DADAIA_PRIVATE": "private",
        },
    )

    result = adapter.run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "done"
    call = calls[0]
    argv = call["args"][0]
    assert isinstance(argv, list)
    assert argv[:2] == ["/usr/bin/codex", "exec"]
    assert "--ignore-user-config" in argv
    assert argv[argv.index("--sandbox") :][:2] == ["--sandbox", "workspace-write"]
    assert argv[argv.index("--ask-for-approval") :][:2] == [
        "--ask-for-approval",
        "never",
    ]
    assert ["--cd", str(tmp_path)] == argv[argv.index("--cd") :][:2]
    assert argv[argv.index("-m") :][:2] == ["-m", "gpt-test"]
    assert 'model_reasoning_effort="medium"' in argv
    assert argv[-1] == "-"
    assert call["kwargs"]["cwd"] == tmp_path
    assert call["kwargs"]["env"] == {"PATH": "/bin", "HOME": "/home/operator"}
    assert "secret-key" not in str(call["kwargs"])


def test_codex_exec_adapter_resolves_model_from_registry_tier(tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout='{"summary":"plain"}')

    result = CodexExecAdapter(
        CodexExecConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={},
    ).run(_request(model_profile="fast"))

    assert result.status is AgentRunStatus.SUCCEEDED
    assert captured["argv"][captured["argv"].index("-m") + 1] == "gpt-5.4-mini"
    assert 'model_reasoning_effort="medium"' in captured["argv"]


def test_codex_exec_adapter_rejects_wrong_runtime_without_calling_codex(tmp_path: Path) -> None:
    called = False

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess([], 0)

    request = AgentRunRequest(
        role="software-engineer",
        prompt="wrong runtime",
        runtime=AgentRuntimeKind.FAKE,
        context="dadaia-workspace",
        release_id="v0.1.15",
    )

    result = CodexExecAdapter(CodexExecConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        request
    )

    assert result.status is AgentRunStatus.FAILED
    assert called is False


def test_codex_exec_adapter_redacts_secret_values_from_errors(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(
            argv,
            1,
            stdout="",
            stderr="failed with sk-secret-token",
        )

    result = CodexExecAdapter(
        CodexExecConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin", "OPENAI_API_KEY": "sk-secret-token"},
    ).run(_request())

    assert result.status is AgentRunStatus.FAILED
    assert result.error == "failed with [REDACTED]"


def test_codex_exec_adapter_redacts_successful_json_output(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(
            json.dumps(
                {
                    "summary": "completed with sk-secret-token",
                    "artifact_refs": [".dadaia/handoff/sk-secret-token.handoff.json"],
                    "structured_output": {
                        "verdict": "APPROVED",
                        "token": "sk-secret-token",
                    },
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    result = CodexExecAdapter(
        CodexExecConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin", "OPENAI_API_KEY": "sk-secret-token"},
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "completed with [REDACTED]"
    assert result.artifact_refs == (".dadaia/handoff/[REDACTED].handoff.json",)
    assert result.structured_output["token"] == "[REDACTED]"
