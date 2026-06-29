"""Headless PI runtime adapter for lifecycle worker requests.

Structurally a twin of ``CodexExecAdapter`` (``codex_runtime.py``): an
infrastructure-only, subprocess-backed adapter behind ``AgentRuntimePort``. It
drives the ``pi`` CLI headless as ``pi --mode json`` — a deterministic,
line-delimited JSON event stream whose LAST ``{"type":"message_end",...}`` event
carries the assistant ``AgentMessage``.

No ``pi`` client is imported at module load — subprocess only — so offline-first
is preserved and the unit suite runs fully faked through an injected runner.

The security-relevant invariants shared with the other real adapters — secret
redaction, the env-allowlist filter, the git ``changed_paths`` override, the
``Runner`` seam, and the prompt envelope — live in
:mod:`dadaia_workspace.infrastructure.headless_adapter_base`. This module keeps
only the genuinely PI-CLI-specific logic (``_command``, the JSONL parse, and
result/stream extraction).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.infrastructure.headless_adapter_base import (
    Runner,
    SubprocessAdapterMixin,
    _GitDiffPort,
    normalize_artifact_refs,
)

_DEFAULT_ENV_ALLOWLIST = (
    "ANTHROPIC_API_KEY",
    "PATH",
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "TERM",
)


@dataclass(frozen=True)
class PiHeadlessConfig:
    """Explicit controls for one headless PI adapter instance.

    ``model`` is the discrete Layer-2 GPT id (LAW 2 / ADR-B) PI runs against its Codex
    subscription. PI's CLI resolves bare ids through its provider stack, so the adapter
    qualifies GPT ids as ``openai-codex/<id>`` before passing ``--model``. The selected
    reasoning effort is forwarded through PI's native ``--thinking`` flag.
    """

    cwd: Path
    pi_bin: str = "pi"
    model: str | None = None
    reasoning_effort: str | None = None
    timeout_seconds: int = 900
    env_allowlist: tuple[str, ...] = _DEFAULT_ENV_ALLOWLIST
    tools: tuple[str, ...] = ("read", "write", "edit", "bash")
    review_tools: tuple[str, ...] = ("read", "write")


class PiHeadlessAdapter(SubprocessAdapterMixin):
    """Run bounded lifecycle worker prompts through ``pi --mode json``.

    The adapter is infrastructure-only: it never decides lifecycle transitions,
    it only returns a structured ``AgentRunResult`` for Python services to
    validate. ``changed_paths`` is sourced from ``git diff`` (the injected
    ``git`` client), never from a model self-report — that is what gives PI a
    real Ring-2 write boundary.
    """

    def __init__(
        self,
        config: PiHeadlessConfig,
        *,
        runner: Runner | None = None,
        environ: Mapping[str, str] | None = None,
        git: _GitDiffPort | None = None,
    ) -> None:
        self._config = config
        self._runner = runner or subprocess.run
        self._environ = environ if environ is not None else os.environ
        self._git = git
        # Wire the mixin seams to this adapter's config.
        self._env_allowlist = config.env_allowlist
        self._cwd_for_diff = config.cwd

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.PI_HEADLESS

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if request.runtime is not AgentRuntimeKind.PI_HEADLESS:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="request runtime does not match PiHeadlessAdapter",
                error=f"unsupported runtime: {request.runtime.value}",
            )

        args = self._command(request)
        started_at = time.time()
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
                summary="pi headless timed out",
                error=self._redact(str(exc)),
            )
        except OSError as exc:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="pi headless failed to start",
                error=self._redact(str(exc)),
            )

        result = self._result_from_output(request, proc.stdout, proc.stderr, proc.returncode)
        if result.status is AgentRunStatus.FAILED:
            if not (result.error or "").strip():
                result = AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary=result.summary,
                    error=self._redact((proc.stderr or proc.stdout or "").strip()),
                )
            return result
        result = self._with_written_handoff_result(request, result, started_at=started_at)
        return self._with_changed_paths(result)

    def _command(self, request: AgentRunRequest) -> list[str]:
        """Build the ``pi --mode json`` argv, threading the resolved per-request model.

        M2 (T-28-A-06): ONE ordered precedence for the ``--model`` id, highest → lowest:

        1. ``request.resolved_model.model`` — the policy-resolved concrete model
           (governance); this is what makes per-step model selection reach the command.
        2. construction-time ``config.model`` — the container's per-step ``--model``
           selection (legacy LAW-2 path).
        3. neither ⇒ no ``--model`` flag (PI uses its own default).

        PI resolves bare ids provider-first, so the model is provider-qualified before it
        reaches ``--model``. Reasoning effort is forwarded with ``--thinking`` when
        present.
        """
        args = [
            self._config.pi_bin,
            "--mode",
            "json",
            "--tools",
            ",".join(self._tools_for_request(request)),
        ]
        model = self._resolve_model(request)
        if model is not None:
            args += ["--model", self._pi_model_pattern(model)]
        effort = self._resolve_thinking(request)
        if effort is not None:
            args += ["--thinking", effort]
        # ``--print``/-p is non-interactive; the prompt is piped via stdin
        # (``subprocess.run(..., input=self._prompt(request))``). PI reads the piped
        # stdin in print mode — do NOT append a ``-`` stdin marker: ``pi`` has no such
        # option and rejects it ("Unknown option: -"), which BLOCKs every PI Layer-2
        # step (bug pi-headless-command-trailing-dash-breaks-layer2).
        args += ["-p"]
        return args

    def _resolve_model(self, request: AgentRunRequest) -> str | None:
        if request.resolved_model is not None:
            return request.resolved_model.model
        return self._config.model

    def _tools_for_request(self, request: AgentRunRequest) -> tuple[str, ...]:
        if self._is_review_request(request):
            return self._config.review_tools
        return self._config.tools

    @staticmethod
    def _is_review_request(request: AgentRunRequest) -> bool:
        review_roles = {
            "code-reviewer",
            "project-auditor",
            "qa-engineer",
            "security-reviewer",
            "software-architect",
        }
        role = request.role.strip().lower()
        return role in review_roles or role.endswith("-reviewer")

    def _resolve_thinking(self, request: AgentRunRequest) -> str | None:
        if request.resolved_model is not None:
            return request.resolved_model.reasoning
        return self._config.reasoning_effort

    @staticmethod
    def _pi_model_pattern(model: str) -> str:
        if "/" in model:
            return model
        return f"openai-codex/{model}"

    # -- result extraction (WS-PI-2) -------------------------------------

    def _result_from_output(
        self,
        request: AgentRunRequest,
        stdout: str,
        stderr: str,
        returncode: int,
    ) -> AgentRunResult:
        message = self._last_message_end(stdout)
        if message is None:
            # Degraded fallback: no usable message_end. Never crash.
            text = (stdout or "").strip()
            if returncode != 0:
                return AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary="pi headless returned non-zero exit",
                    error=self._redact((stderr or stdout or "").strip()),
                )
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(text or "pi headless completed"),
            )

        assistant_text = self._extract_text(message.get("content"))
        verdict_payload = self._extract_result_payload(assistant_text, request.expected_schema)

        if verdict_payload is not None:
            summary = str(verdict_payload.get("summary", assistant_text))
            refs = normalize_artifact_refs(verdict_payload)
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(summary or "pi headless completed"),
                artifact_refs=tuple(self._redact(path) for path in refs),
                structured_output=self._structured_from_verdict(verdict_payload),
            )

        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=self._redact(assistant_text or "pi headless completed"),
        )

    @staticmethod
    def _last_message_end(stdout: str) -> dict[str, object] | None:
        last: dict[str, object] | None = None
        for line in (stdout or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") != "message_end":
                continue
            message = event.get("message")
            if isinstance(message, dict):
                last = message
        return last

    @staticmethod
    def _extract_text(content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts)
        return ""

    def _structured_from_verdict(self, payload: dict[str, object]) -> dict[str, str]:
        structured: dict[str, str] = {}
        for key in ("verdict", "verdict_reason", "commit_sha", "task_group"):
            value = payload.get(key)
            if value is not None:
                structured[key] = self._redact(str(value))
        extra = payload.get("structured_output")
        if isinstance(extra, dict):
            for key, value in extra.items():
                structured[str(key)] = self._redact(str(value))
        metrics = payload.get("metrics")
        if isinstance(metrics, dict):
            commit_sha = metrics.get("commit_sha")
            if commit_sha is not None and "commit_sha" not in structured:
                structured["commit_sha"] = self._redact(str(commit_sha))
        return structured

    def _with_written_handoff_result(
        self,
        request: AgentRunRequest,
        result: AgentRunResult,
        *,
        started_at: float,
    ) -> AgentRunResult:
        """Recover a valid handoff written to disk when PI's final message is prose."""
        if result.artifact_refs or result.structured_output.get("verdict"):
            return result
        handoff = self._latest_written_handoff(request, started_at=started_at)
        if handoff is None:
            return result
        ref, payload = handoff
        return AgentRunResult(
            status=result.status,
            summary=result.summary,
            artifact_refs=(ref,),
            structured_output=self._structured_from_verdict(payload),
            error=result.error,
        )

    def _latest_written_handoff(
        self,
        request: AgentRunRequest,
        *,
        started_at: float,
    ) -> tuple[str, dict[str, object]] | None:
        handoff_dir = self._config.cwd / ".dadaia" / "handoff" / request.context
        if not handoff_dir.is_dir():
            return None
        matches: list[tuple[float, str, dict[str, object]]] = []
        for path in handoff_dir.glob("*.handoff.json"):
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_mtime < started_at - 1:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            if payload.get("agent") != request.role:
                continue
            if payload.get("context") != request.context:
                continue
            if payload.get("release_id") != request.release_id:
                continue
            try:
                rel = path.resolve().relative_to(self._config.cwd.resolve()).as_posix()
            except ValueError:
                continue
            matches.append((stat.st_mtime, rel, payload))
        if not matches:
            return None
        _mtime, rel, payload = max(matches, key=lambda item: item[0])
        return rel, payload
