"""Exec-backed Codex runtime adapter for lifecycle worker requests."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, get_args

from dadaia_workspace.core.model_registry import CodexEffort, codex_tier_views
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)

Runner = Callable[..., subprocess.CompletedProcess[str]]

_DEFAULT_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "CODEX_HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "TERM",
)
_SECRET_NAME_PARTS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")

_VALID_CODEX_EFFORTS: frozenset[str] = frozenset(get_args(CodexEffort))


def _as_codex_effort(effort: str) -> CodexEffort:
    """Narrow a resolved reasoning string to the ``CodexEffort`` literal.

    Raises:
        ValueError: if *effort* is not one of ``high``/``medium``/``low``.
    """
    if effort not in _VALID_CODEX_EFFORTS:
        raise ValueError(
            f"invalid Codex reasoning effort {effort!r}; "
            f"valid: {', '.join(sorted(_VALID_CODEX_EFFORTS))}"
        )
    return effort  # type: ignore[return-value]


class _GitDiffPort(Protocol):
    """Narrow git seam the adapter needs — satisfied by ``GitSubprocessClient``."""

    def diff_name_only(self, path: Path) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class CodexExecConfig:
    """Explicit controls for one Codex exec adapter instance."""

    cwd: Path
    codex_bin: str = "codex"
    model: str | None = None
    reasoning_effort: CodexEffort | None = None
    sandbox: str = "read-only"
    approval_policy: str = "never"
    env_allowlist: tuple[str, ...] = _DEFAULT_ENV_ALLOWLIST
    timeout_seconds: int = 900


class CodexExecAdapter:
    """Run bounded lifecycle worker prompts through `codex exec`.

    The adapter is intentionally infrastructure-only. It never decides lifecycle
    transitions; it only returns structured `AgentRunResult` for Python services to
    validate. Live execution is opt-in through callers that instantiate this adapter.

    When an injected ``git`` client is present, ``changed_paths`` is sourced from
    ``git diff`` (the real working-tree+staged+untracked-non-ignored union), never
    from a model self-report — that is what gives Codex a real Ring-2 write boundary,
    matching ``PiHeadlessAdapter``. When ``git`` is ``None`` the prior behaviour is
    preserved (no ``changed_paths`` injection).
    """

    def __init__(
        self,
        config: CodexExecConfig,
        *,
        runner: Runner = subprocess.run,
        environ: Mapping[str, str] | None = None,
        git: _GitDiffPort | None = None,
    ) -> None:
        self._config = config
        self._runner = runner
        self._environ = environ if environ is not None else os.environ
        self._git = git

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.CODEX_EXEC

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if request.runtime is not AgentRuntimeKind.CODEX_EXEC:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="request runtime does not match CodexExecAdapter",
                error=f"unsupported runtime: {request.runtime.value}",
            )

        with tempfile.TemporaryDirectory(prefix="dadaia-codex-exec-") as tmp:
            output_path = Path(tmp) / "last-message.json"
            args = self._command(request, output_path)
            try:
                proc = self._runner(
                    args,
                    cwd=self._config.cwd,
                    env=self._env(),
                    input=self._prompt(request),
                    text=True,
                    capture_output=True,
                    timeout=self._config.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                return AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary="codex exec timed out",
                    error=self._redact(str(exc)),
                )
            except OSError as exc:
                return AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary="codex exec failed to start",
                    error=self._redact(str(exc)),
                )

            if proc.returncode != 0:
                return AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary="codex exec returned non-zero exit",
                    error=self._redact((proc.stderr or proc.stdout or "").strip()),
                )
            result = self._result_from_output(output_path, proc)
            return self._with_changed_paths(result)

    def _command(self, request: AgentRunRequest, output_path: Path) -> list[str]:
        model, effort = self._model_and_effort(request)
        args = [
            self._config.codex_bin,
            "exec",
            "--ignore-user-config",
            "--sandbox",
            self._config.sandbox,
            "--ask-for-approval",
            self._config.approval_policy,
            "--cd",
            str(self._config.cwd),
            "--output-last-message",
            str(output_path),
            "-m",
            model,
            "-c",
            f'model_reasoning_effort="{effort}"',
            "-",
        ]
        return args

    def _model_and_effort(self, request: AgentRunRequest) -> tuple[str, CodexEffort]:
        """Resolve the ``(model, reasoning_effort)`` for one request — ONE ordered precedence.

        M2 (T-28-A-06): the governance-resolved per-request model config wins; the legacy
        tier-name match is a fallback only. The single precedence, highest → lowest:

        1. ``request.resolved_model`` — the policy-resolved concrete model (governance).
        2. construction-time ``config.model`` + ``config.reasoning_effort`` — the
           container's per-step ``--model`` selection (legacy LAW-2 path).
        3. ``request.model_profile`` interpreted as a Codex *tier name* (legacy
           observability fallback — predates the profile registry).
        4. the ``dispatch`` tier view (last-resort default).
        """
        if request.resolved_model is not None:
            return request.resolved_model.model, _as_codex_effort(request.resolved_model.reasoning)
        if self._config.model is not None and self._config.reasoning_effort is not None:
            return self._config.model, self._config.reasoning_effort
        if request.model_profile:
            for view in codex_tier_views():
                if view.tier == request.model_profile:
                    return view.codex_id, view.reasoning_effort
        for view in codex_tier_views():
            if view.tier == "dispatch":
                return view.codex_id, view.reasoning_effort
        raise ValueError("Codex dispatch tier is not configured")

    def _env(self) -> dict[str, str]:
        return {
            key: self._environ[key] for key in self._config.env_allowlist if key in self._environ
        }

    @staticmethod
    def _prompt(request: AgentRunRequest) -> str:
        return json.dumps(
            {
                "role": request.role,
                "prompt": request.prompt,
                "context": request.context,
                "release_id": request.release_id,
                "task_id": request.task_id,
                "allowed_paths": list(request.allowed_paths),
                "forbidden_paths": list(request.forbidden_paths),
                "expected_schema": request.expected_schema,
                "required_evidence": [kind.value for kind in request.required_evidence],
            },
            indent=2,
            sort_keys=True,
        )

    def _result_from_output(
        self,
        output_path: Path,
        proc: subprocess.CompletedProcess[str],
    ) -> AgentRunResult:
        try:
            raw = output_path.read_text(encoding="utf-8")
        except OSError:
            raw = proc.stdout
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(raw.strip() or "codex exec completed"),
            )
        if not isinstance(payload, dict):
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="codex exec completed",
                structured_output={"value": self._redact(str(payload))},
            )
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=self._redact(str(payload.get("summary", "codex exec completed"))),
            artifact_refs=tuple(
                self._redact(str(item))
                for item in payload.get("artifact_refs", [])
                if isinstance(item, str)
            ),
            structured_output={
                str(key): self._redact(str(value))
                for key, value in payload.get("structured_output", {}).items()
                if isinstance(payload.get("structured_output"), dict)
            },
        )

    # -- changed_paths via git diff (Ring-2 root-cause, GAP-B) ------------

    def _with_changed_paths(self, result: AgentRunResult) -> AgentRunResult:
        """Source ``changed_paths`` from ``git diff``, overriding any model claim.

        When no git client is injected the result is returned untouched (prior
        behaviour). When present, the real diff UNCONDITIONALLY overwrites any
        ``changed_paths`` a lying worker may have self-reported.
        """
        if self._git is None:
            return result
        changed = self._git.diff_name_only(self._config.cwd)
        structured = dict(result.structured_output)
        structured["changed_paths"] = ",".join(changed)
        return AgentRunResult(
            status=result.status,
            summary=result.summary,
            artifact_refs=result.artifact_refs,
            structured_output=structured,
            error=result.error,
        )

    def _redact(self, text: str) -> str:
        redacted = text
        for key, value in self._environ.items():
            if not value:
                continue
            if any(part in key.upper() for part in _SECRET_NAME_PARTS):
                redacted = redacted.replace(value, "[REDACTED]")
        return redacted
