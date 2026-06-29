"""Contract tests for Layer-2 headless runtime security boundaries.

These are intentionally compact retained guards. They protect current security behavior
without restoring the deleted private adapter-unit matrices.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from dadaia_workspace.container import build_agent_runtime
from dadaia_workspace.core.harness_models import HarnessModelOption
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.infrastructure import claude_sdk_runtime, codex_runtime, pi_runtime
from dadaia_workspace.infrastructure.headless_adapter_base import (
    ChangedPathsMixin,
    RedactionMixin,
    extract_result_payload,
    normalize_artifact_refs,
)


class _FakeGit:
    def __init__(self, changed: tuple[str, ...]) -> None:
        self.changed = changed
        self.calls: list[Path] = []

    def diff_name_only(self, path: Path) -> tuple[str, ...]:
        self.calls.append(path)
        return self.changed


def _request(runtime: AgentRuntimeKind) -> AgentRunRequest:
    return AgentRunRequest(
        role="security-reviewer",
        prompt="Review the bounded change.",
        runtime=runtime,
        context="dadaia-workspace",
        release_id="v0.1.34",
        allowed_paths=("repos/dadaia-workspace/**",),
        forbidden_paths=("secrets/**",),
        expected_schema="agent-run-result-v1",
    )


def test_secret_redaction_is_shared_by_all_real_headless_adapters(tmp_path: Path) -> None:
    environ = {
        "PATH": "/bin",
        "OPENAI_API_KEY": "sk-openai-secret",
        "ANTHROPIC_API_KEY": "sk-anthropic-secret",
    }
    adapters = [
        pi_runtime.PiHeadlessAdapter(
            pi_runtime.PiHeadlessConfig(cwd=tmp_path),
            environ=environ,
        ),
        codex_runtime.CodexExecAdapter(
            codex_runtime.CodexExecConfig(cwd=tmp_path),
            environ=environ,
        ),
        claude_sdk_runtime.ClaudeSdkAdapter(environ=environ),
    ]

    for adapter in adapters:
        assert adapter._redact is not None
        redacted = adapter._redact("leaked sk-openai-secret and sk-anthropic-secret via /bin")
        assert "sk-openai-secret" not in redacted
        assert "sk-anthropic-secret" not in redacted
        assert redacted.count("[REDACTED]") == 2
        assert "/bin" in redacted

    assert pi_runtime.PiHeadlessAdapter._redact is RedactionMixin._redact
    assert codex_runtime.CodexExecAdapter._redact is RedactionMixin._redact
    assert claude_sdk_runtime.ClaudeSdkAdapter._redact is RedactionMixin._redact


def test_cli_runtime_env_is_allowlisted_before_subprocess_spawn(tmp_path: Path) -> None:
    pi_env = pi_runtime.PiHeadlessAdapter(
        pi_runtime.PiHeadlessConfig(cwd=tmp_path),
        environ={
            "PATH": "/bin",
            "ANTHROPIC_API_KEY": "sk-allowed-for-pi",
            "OPENAI_API_KEY": "sk-not-for-pi",
            "DADAIA_PRIVATE": "private",
        },
    )._env()
    codex_env = codex_runtime.CodexExecAdapter(
        codex_runtime.CodexExecConfig(cwd=tmp_path, isolate_home=False),
        environ={
            "PATH": "/bin",
            "HOME": "/home/operator",
            "CODEX_HOME": "/home/operator/.codex",
            "OPENAI_API_KEY": "sk-not-forwarded",
            "DADAIA_PRIVATE": "private",
        },
    )._env()

    assert pi_env == {"ANTHROPIC_API_KEY": "sk-allowed-for-pi", "PATH": "/bin"}
    assert codex_env == {
        "PATH": "/bin",
        "HOME": "/home/operator",
        "CODEX_HOME": "/home/operator/.codex",
    }


def test_git_diff_changed_paths_override_worker_self_report(tmp_path: Path) -> None:
    adapters = [
        pi_runtime.PiHeadlessAdapter(pi_runtime.PiHeadlessConfig(cwd=tmp_path)),
        codex_runtime.CodexExecAdapter(codex_runtime.CodexExecConfig(cwd=tmp_path)),
    ]

    for adapter in adapters:
        adapter._git = _FakeGit(("actual.py", "tests/actual_test.py"))
        result = AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="worker self-reported a lie",
            structured_output={"changed_paths": "claimed.py"},
        )

        secured = adapter._with_changed_paths(result)

        assert secured.structured_output["changed_paths"] == "actual.py,tests/actual_test.py"
        assert adapter._with_changed_paths is not None

    assert pi_runtime.PiHeadlessAdapter._with_changed_paths is ChangedPathsMixin._with_changed_paths
    assert (
        codex_runtime.CodexExecAdapter._with_changed_paths is ChangedPathsMixin._with_changed_paths
    )


def test_result_payload_extraction_accepts_only_current_result_contract() -> None:
    accepted = extract_result_payload(
        json.dumps(
            {
                "schema": "agent-run-result-v1",
                "summary": "done",
                "artifact_refs": [
                    {
                        "type": "handoff",
                        "path": ".dadaia/handoff/dadaia-workspace/security.handoff.json",
                    }
                ],
                "structured_output": {"verdict": "APPROVED"},
            }
        ),
        "agent-run-result-v1",
    )
    rejected = extract_result_payload(
        json.dumps({"summary": "looks like JSON, but has no artifact evidence"}),
        "agent-run-result-v1",
    )
    handoff_payload = {
        "schema_version": "handoff-v1.1",
        "agent": "security-reviewer",
        "context": "dadaia-workspace",
        "release_id": "v0.1.34",
        "verdict": "APPROVED",
        "metrics": {
            "commit_sha": "abc123",
            "artifact_ref": ".dadaia/handoff/dadaia-workspace/security.handoff.json",
        },
        "artifact": {"type": "other"},
    }
    accepted_handoff = extract_result_payload(json.dumps(handoff_payload), "agent-run-result-v1")

    assert accepted is not None
    assert accepted["structured_output"] == {"verdict": "APPROVED"}
    assert accepted_handoff is not None
    assert normalize_artifact_refs(accepted_handoff) == (
        ".dadaia/handoff/dadaia-workspace/security.handoff.json",
    )
    assert rejected is None


def test_codex_error_output_is_redacted_and_has_no_artifact_refs(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="failed sk-secret")

    result = codex_runtime.CodexExecAdapter(
        codex_runtime.CodexExecConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin", "OPENAI_API_KEY": "sk-secret"},
    ).run(_request(AgentRuntimeKind.CODEX_EXEC))

    assert result.status is AgentRunStatus.FAILED
    assert result.error == "failed [REDACTED]"
    assert result.artifact_refs == ()


def test_codex_exec_command_uses_supported_lifecycle_startup_flags(tmp_path: Path) -> None:
    captured: list[str] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured.extend(str(part) for part in argv)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="stop before model")

    result = codex_runtime.CodexExecAdapter(
        codex_runtime.CodexExecConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin"},
    ).run(_request(AgentRuntimeKind.CODEX_EXEC))

    assert result.status is AgentRunStatus.FAILED
    assert "--ask-for-approval" not in captured
    assert "--sandbox" in captured
    assert captured[captured.index("--sandbox") + 1] == "workspace-write"
    assert "--skip-git-repo-check" in captured
    assert "--ignore-user-config" in captured


def test_container_built_codex_adapter_uses_writable_workflow_sandbox(tmp_path: Path) -> None:
    adapter = build_agent_runtime(AgentRuntimeKind.CODEX_EXEC, cwd=tmp_path)

    assert isinstance(adapter, codex_runtime.CodexExecAdapter)
    assert adapter._config.sandbox == "workspace-write"


def test_pi_nonzero_without_message_end_surfaces_runtime_failure(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        stdout = json.dumps({"type": "session", "id": "sess_live"}) + "\n"
        stderr = "No API key found for azure-openai-responses. Use /login."
        return subprocess.CompletedProcess(argv, 1, stdout=stdout, stderr=stderr)

    result = pi_runtime.PiHeadlessAdapter(
        pi_runtime.PiHeadlessConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin"},
    ).run(_request(AgentRuntimeKind.PI_HEADLESS))

    assert result.status is AgentRunStatus.FAILED
    assert result.summary == "pi headless returned non-zero exit"
    assert "No API key found" in (result.error or "")
    assert result.artifact_refs == ()


def test_pi_command_qualifies_model_and_threads_thinking(tmp_path: Path) -> None:
    captured: list[str] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured.extend(str(part) for part in argv)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="stop before worker")

    adapter = build_agent_runtime(
        AgentRuntimeKind.PI_HEADLESS,
        cwd=tmp_path,
        model=HarnessModelOption("gpt-5.3-codex-spark", "medium"),
    )
    assert isinstance(adapter, pi_runtime.PiHeadlessAdapter)
    adapter._runner = fake_runner

    result = adapter.run(_request(AgentRuntimeKind.PI_HEADLESS))

    assert result.status is AgentRunStatus.FAILED
    assert captured[captured.index("--model") + 1] == "openai-codex/gpt-5.3-codex-spark"
    assert captured[captured.index("--thinking") + 1] == "medium"


def test_pi_review_requests_do_not_get_bash_or_edit_tools(tmp_path: Path) -> None:
    captured: list[str] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured.extend(str(part) for part in argv)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="stop before worker")

    result = pi_runtime.PiHeadlessAdapter(
        pi_runtime.PiHeadlessConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin"},
    ).run(_request(AgentRuntimeKind.PI_HEADLESS))

    assert result.status is AgentRunStatus.FAILED
    tools = captured[captured.index("--tools") + 1].split(",")
    assert tools == ["read", "write"]
    assert "bash" not in tools
    assert "edit" not in tools


def test_pi_create_requests_keep_full_configured_tool_set(tmp_path: Path) -> None:
    captured: list[str] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured.extend(str(part) for part in argv)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="stop before worker")

    request = AgentRunRequest(
        role="product-engineer",
        prompt="Create the scoped release artifact.",
        runtime=AgentRuntimeKind.PI_HEADLESS,
        context="dadaia-workspace",
        release_id="v0.1.37",
        allowed_paths=("specs/releases/v0.1.37/alpha-1/SPEC.md",),
        expected_schema="agent-run-result-v1",
    )

    result = pi_runtime.PiHeadlessAdapter(
        pi_runtime.PiHeadlessConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin"},
    ).run(request)

    assert result.status is AgentRunStatus.FAILED
    assert captured[captured.index("--tools") + 1].split(",") == [
        "read",
        "write",
        "edit",
        "bash",
    ]


def test_codex_handoff_final_payload_surfaces_review_verdict(tmp_path: Path) -> None:
    handoff = {
        "schema_version": "handoff-v1.1",
        "agent": "security-reviewer",
        "context": "dadaia-workspace",
        "release_id": "v0.1.34",
        "verdict": "APPROVED",
        "verdict_reason": "No blockers.",
        "metrics": {
            "commit_sha": "abc123",
            "artifact_ref": ".dadaia/handoff/dadaia-workspace/security.handoff.json",
        },
        "artifact": {"type": "other"},
    }

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        output_path = Path(argv[argv.index("--output-last-message") + 1])
        output_path.write_text(json.dumps(handoff), encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    result = codex_runtime.CodexExecAdapter(
        codex_runtime.CodexExecConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin"},
    ).run(_request(AgentRuntimeKind.CODEX_EXEC))

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/security.handoff.json",)
    assert result.structured_output["verdict"] == "APPROVED"
    assert result.structured_output["verdict_reason"] == "No blockers."
    assert result.structured_output["commit_sha"] == "abc123"


def test_codex_recovers_written_handoff_when_final_message_is_prose(tmp_path: Path) -> None:
    handoff_dir = tmp_path / ".dadaia" / "handoff" / "dadaia-workspace"
    handoff_dir.mkdir(parents=True)
    handoff_path = handoff_dir / "security.handoff.json"
    handoff = {
        "schema_version": "handoff-v1.1",
        "agent": "security-reviewer",
        "context": "dadaia-workspace",
        "release_id": "v0.1.34",
        "verdict": "APPROVED",
        "metrics": {
            "commit_sha": "abc123",
            "artifact_ref": ".dadaia/handoff/dadaia-workspace/security.handoff.json",
        },
        "artifact": {"type": "other"},
    }

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        output_path = Path(argv[argv.index("--output-last-message") + 1])
        handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
        output_path.write_text("Wrote the security handoff.", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    result = codex_runtime.CodexExecAdapter(
        codex_runtime.CodexExecConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin"},
    ).run(_request(AgentRuntimeKind.CODEX_EXEC))

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/security.handoff.json",)
    assert result.structured_output["verdict"] == "APPROVED"
    assert result.structured_output["commit_sha"] == "abc123"
