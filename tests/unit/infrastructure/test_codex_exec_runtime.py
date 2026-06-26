"""Unit tests for the exec-backed Codex runtime adapter."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
)
from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter, CodexExecConfig


class _FakeGit:
    """Fake GitSubprocessClient seam — returns a canned diff list per cwd snapshot."""

    def __init__(self, changed: tuple[str, ...] = ()) -> None:
        self._changed = changed
        self.calls: list[Path] = []

    def diff_name_only(self, path: Path) -> tuple[str, ...]:
        self.calls.append(path)
        return self._changed


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


def test_codex_discrete_model_and_effort_reach_command_verbatim(tmp_path: Path) -> None:
    """WS-2 (LAW 2): a supplied discrete ``(id, effort)`` is used verbatim, NOT the tier.

    Built via the container seam ``build_agent_runtime(CODEX_EXEC, model=...)`` to prove
    the discrete catalog option threads to ``-m <id> -c model_reasoning_effort=<effort>``.
    Even though the request still carries a ``model_profile`` tier, the discrete config
    wins (tier is fallback only).
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.harness_models import validate

    captured: dict[str, list[str]] = {}

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured["argv"] = argv
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text('{"summary":"done"}', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    option = validate("codex", "gpt-5.5:medium")
    adapter = container.build_agent_runtime(AgentRuntimeKind.CODEX_EXEC, cwd=tmp_path, model=option)
    assert isinstance(adapter, CodexExecAdapter)
    adapter._runner = fake_runner  # type: ignore[attr-defined]
    adapter._environ = {}  # type: ignore[attr-defined]
    adapter._git = None  # type: ignore[attr-defined]
    # Request carries a tier profile, which MUST be ignored in favour of the discrete model.
    adapter.run(_request(model_profile="deep"))

    argv = captured["argv"]
    assert argv[argv.index("-m") + 1] == "gpt-5.5"
    assert 'model_reasoning_effort="medium"' in argv


def test_codex_tier_fallback_used_when_no_discrete_model(tmp_path: Path) -> None:
    """When no discrete model is supplied, the registry tier view is the fallback."""
    from dadaia_workspace import container

    captured: dict[str, list[str]] = {}

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured["argv"] = argv
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text('{"summary":"done"}', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    adapter = container.build_agent_runtime(AgentRuntimeKind.CODEX_EXEC, cwd=tmp_path)
    assert isinstance(adapter, CodexExecAdapter)
    adapter._runner = fake_runner  # type: ignore[attr-defined]
    adapter._environ = {}  # type: ignore[attr-defined]
    adapter._git = None  # type: ignore[attr-defined]
    adapter.run(_request(model_profile="fast"))

    argv = captured["argv"]
    # 'fast' tier resolves to gpt-5.4-mini via codex_tier_views().
    assert argv[argv.index("-m") + 1] == "gpt-5.4-mini"


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


# ---------------------------------------------------------------------------
# GAP-B — changed_paths from a FAKED git diff (never a model self-report)
# ---------------------------------------------------------------------------


def _git_diff_runner(model_changed: str) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Runner whose codex output self-reports a (lying) ``changed_paths``."""

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(
            json.dumps(
                {
                    "summary": "done",
                    "structured_output": {"changed_paths": model_changed},
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    return fake_runner


def test_codex_exec_adapter_changed_paths_from_git_diff(tmp_path: Path) -> None:
    fake_git = _FakeGit(changed=("src/a.py", "src/b.py"))

    result = CodexExecAdapter(
        CodexExecConfig(cwd=tmp_path),
        runner=_git_diff_runner(model_changed="lies/fake.py"),
        environ={},
        git=fake_git,
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    # The real git diff WINS over the model's self-reported changed_paths.
    assert result.structured_output["changed_paths"] == "src/a.py,src/b.py"
    assert fake_git.calls == [tmp_path]


def test_codex_exec_adapter_changed_paths_empty_when_no_diff(tmp_path: Path) -> None:
    fake_git = _FakeGit(changed=())

    result = CodexExecAdapter(
        CodexExecConfig(cwd=tmp_path),
        runner=_git_diff_runner(model_changed="lies/fake.py"),
        environ={},
        git=fake_git,
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output["changed_paths"] == ""
    assert fake_git.calls == [tmp_path]


def test_codex_exec_adapter_no_git_client_preserves_prior_behavior(tmp_path: Path) -> None:
    result = CodexExecAdapter(
        CodexExecConfig(cwd=tmp_path),
        runner=_git_diff_runner(model_changed="lies/fake.py"),
        environ={},
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    # No git client: the adapter does not synthesize changed_paths; the model's own
    # value passes through untouched (no Ring-2 override).
    assert result.structured_output["changed_paths"] == "lies/fake.py"
