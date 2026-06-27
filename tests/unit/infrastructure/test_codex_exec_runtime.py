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
    """Runner whose codex output is a valid result object self-reporting a (lying) ``changed_paths``.

    The payload IS a result object (schema-labelled + non-empty ``artifact_refs``) so it
    passes the v0.1.32 extraction/reject-guard — the test then exercises whether the git
    diff OVERRIDES the model's self-reported ``changed_paths`` (Ring-2 boundary).
    """

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(
            json.dumps(
                {
                    "schema": "agent-run-result-v1",
                    "summary": "done",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/g.handoff.json"],
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


def test_codex_resolved_model_wins_over_config_and_tier(tmp_path: Path) -> None:
    """T-28-A-06 / M2: the per-request resolved_model wins over config.model and tier.

    The single ordered precedence is resolved_model > config.model > model_profile tier >
    dispatch default. Here both a construction-time config model AND a request tier exist;
    the resolved_model must still be the one that reaches ``-m`` / ``model_reasoning_effort``.
    """
    import dataclasses

    from dadaia_workspace.core.harness_models import validate
    from dadaia_workspace.core.models.workflow_execution import (
        PolicySource,
        ResolvedModelConfig,
    )
    from dadaia_workspace.infrastructure.codex_runtime import CodexExecConfig

    captured: dict[str, list[str]] = {}

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured["argv"] = argv
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text('{"summary":"done"}', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    # Construction-time config model is gpt-5.5:medium ...
    option = validate("codex", "gpt-5.5:medium")
    adapter = CodexExecAdapter(
        CodexExecConfig(cwd=tmp_path, model=option.model_id, reasoning_effort=option.effort),
        runner=fake_runner,
        environ={},
    )
    # ... but the resolved_model says gpt-5.5:high — which must win.
    request = dataclasses.replace(
        _request(model_profile="deep"),
        resolved_model=ResolvedModelConfig(
            profile_id="codex-review-deep",
            harness="codex",
            model="gpt-5.5",
            reasoning="high",
            source=PolicySource.CLI,
        ),
    )

    adapter.run(request)

    argv = captured["argv"]
    assert argv[argv.index("-m") + 1] == "gpt-5.5"
    assert 'model_reasoning_effort="high"' in argv


# ---------------------------------------------------------------------------
# T-32-B-01 — codex extractor parity: fenced+bare parse, strict-primary +
# structural-fallback acceptance, no-op→empty refs, reject-guard (A10/A11/C4).
# These FAIL against the pre-parity codex (single ``json.loads`` of the whole
# file, no fenced/bare/sliced candidates, no ``schema`` acceptance, ANY dict
# mapped to a result).
# ---------------------------------------------------------------------------


def _codex_run_with_message(tmp_path: Path, last_message_text: str) -> Any:
    """Run the codex adapter, writing *last_message_text* verbatim to the temp file.

    The text is whatever a real codex worker would leave in ``--output-last-message``:
    a bare JSON object, a fenced ```json block, JSON with trailing prose, or junk.
    """

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(last_message_text, encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    return CodexExecAdapter(CodexExecConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )


def test_codex_strict_primary_accepts_bare_payload(tmp_path: Path) -> None:
    """A10/A11 — a correctly-labelled BARE codex payload is accepted via the strict path."""
    bare = json.dumps(
        {
            "schema": "agent-run-result-v1",
            "summary": "bare codex strict",
            "artifact_refs": [".dadaia/handoff/dadaia-workspace/c1.handoff.json"],
            "structured_output": {"verdict": "APPROVED"},
        }
    )
    result = _codex_run_with_message(tmp_path, bare)
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "bare codex strict"
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/c1.handoff.json",)
    assert result.structured_output["verdict"] == "APPROVED"


def test_codex_strict_primary_accepts_fenced_payload(tmp_path: Path) -> None:
    """A10 — a fenced ```json codex payload (trailing prose) is accepted, not dropped.

    The pre-parity codex called ``json.loads`` on the whole fenced text once and FAILED,
    degrading to a prose-summary result with EMPTY ``artifact_refs`` (would BLOCK a step).
    """
    fenced = (
        "Here is my result.\n```json\n"
        + json.dumps(
            {
                "schema": "agent-run-result-v1",
                "summary": "fenced codex strict",
                "artifact_refs": [".dadaia/handoff/dadaia-workspace/c2.handoff.json"],
                "structured_output": {"verdict": "APPROVED"},
            }
        )
        + "\n```\nDone.\n"
    )
    result = _codex_run_with_message(tmp_path, fenced)
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "fenced codex strict"
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/c2.handoff.json",)
    assert result.structured_output["verdict"] == "APPROVED"


def test_codex_structural_fallback_accepts_mislabelled_payload(tmp_path: Path) -> None:
    """A11 — structural fallback parity: a schema-MISLABELLED but valid payload parses."""
    bare = json.dumps(
        {
            "schema": "release-scope-handoff-v1",  # wrong (domain) id
            "status": "succeeded",
            "summary": "codex mislabelled but valid",
            "artifact_refs": [".dadaia/handoff/dadaia-workspace/c3.handoff.json"],
            "structured_output": {"verdict": "APPROVED"},
        }
    )
    result = _codex_run_with_message(tmp_path, bare)
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "codex mislabelled but valid"
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/c3.handoff.json",)
    assert result.structured_output["verdict"] == "APPROVED"


def test_codex_noop_worker_yields_empty_artifact_refs(tmp_path: Path) -> None:
    """A11 — a no-op codex worker (no result payload) yields empty ``artifact_refs``."""
    result = _codex_run_with_message(tmp_path, "I had nothing structured to emit.")
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.artifact_refs == ()
    assert "verdict" not in result.structured_output


def test_codex_reject_guard_drops_shapeless_dict(tmp_path: Path) -> None:
    """C4 / A11 — codex reject-guard: arbitrary JSON lacking the result shape is dropped.

    A parsed dict with NO ``schema`` match AND no non-empty ``artifact_refs`` is not the
    result object; the rewired codex must yield empty ``artifact_refs`` (no longer mapping
    ANY dict to a result). Pins the regression away from the pre-parity unconditional
    dict acceptance.
    """
    shapeless = json.dumps(
        {"schema": "something-else", "note": "not a result", "verdict": "APPROVED"}
    )
    result = _codex_run_with_message(tmp_path, shapeless)
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.artifact_refs == ()
    assert "verdict" not in result.structured_output


# ---------------------------------------------------------------------------
# T-32-B-03 — A12 / C3: positively prove ONE shared extraction implementation.
# Patch the shared helper in headless_adapter_base and assert BOTH pi_runtime
# AND codex_runtime resolve result extraction through it (not a grep).
# ---------------------------------------------------------------------------


def test_pi_and_codex_share_one_extraction_helper(tmp_path: Path, monkeypatch: Any) -> None:
    """A12 / C3 — both adapters call the SAME ``extract_result_payload`` shared helper.

    A sentinel patch over ``headless_adapter_base.extract_result_payload`` records every
    call. Driving a real ``pi`` run and a real ``codex`` run (both fully faked at the
    subprocess seam) must each invoke the patched helper — proving pi and codex resolve
    result extraction through one implementation, so copy-paste divergence cannot reappear.
    """
    from dadaia_workspace.infrastructure import headless_adapter_base
    from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig

    calls: list[str] = []

    def _spy(text: str, expected_schema: str | None) -> dict[str, object] | None:
        calls.append("called")
        return {
            "schema": expected_schema,
            "summary": "spied",
            "artifact_refs": [".dadaia/handoff/dadaia-workspace/spy.handoff.json"],
            "structured_output": {"verdict": "APPROVED"},
        }

    monkeypatch.setattr(headless_adapter_base, "extract_result_payload", _spy)

    # --- pi run (faked subprocess) ---
    def _pi_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        message = json.dumps(
            {"type": "message_end", "message": {"role": "assistant", "content": "bare"}}
        )
        return subprocess.CompletedProcess(argv, 0, stdout=message)

    pi_request = AgentRunRequest(
        role="software-engineer",
        prompt="work",
        runtime=AgentRuntimeKind.PI_HEADLESS,
        context="dadaia-workspace",
        release_id="v0.1.32",
        expected_schema="agent-run-result-v1",
    )
    PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=_pi_runner, environ={}).run(pi_request)
    assert len(calls) == 1, "pi_runtime did not call the shared extract_result_payload helper"

    # --- codex run (faked subprocess) ---
    _codex_run_with_message(tmp_path, '{"summary":"ignored by spy"}')
    assert len(calls) == 2, "codex_runtime did not call the shared extract_result_payload helper"
