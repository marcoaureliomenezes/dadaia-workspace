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
    subscription; it is passed verbatim as ``pi --model <id>``. ``reasoning_effort``
    carries the chosen option's effort for observability/parity, but PI's CLI exposes
    **no verified separate reasoning-effort flag**, so the effort is *not* forwarded as
    a flag — only ``--model`` reaches the command. (Limitation noted per WS-2: a unit
    test asserts the discrete id reaches ``pi --model``; effort honoring is upstream-CLI
    dependent and is a follow-up if/when PI exposes the flag.)
    """

    cwd: Path
    pi_bin: str = "pi"
    model: str | None = None
    reasoning_effort: str | None = None
    timeout_seconds: int = 900
    env_allowlist: tuple[str, ...] = _DEFAULT_ENV_ALLOWLIST
    tools: tuple[str, ...] = ("read", "write", "edit", "bash")


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
        runner: Runner = subprocess.run,
        environ: Mapping[str, str] | None = None,
        git: _GitDiffPort | None = None,
    ) -> None:
        self._config = config
        self._runner = runner
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

        result = self._result_from_output(request, proc.stdout, proc.returncode)
        if result.status is AgentRunStatus.FAILED:
            if not (result.error or "").strip():
                result = AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary=result.summary,
                    error=self._redact((proc.stderr or proc.stdout or "").strip()),
                )
            return result
        return self._with_changed_paths(result)

    def _command(self, request: AgentRunRequest) -> list[str]:
        """Build the ``pi --mode json`` argv, threading the resolved per-request model.

        M2 (T-28-A-06): ONE ordered precedence for the ``--model`` id, highest → lowest:

        1. ``request.resolved_model.model`` — the policy-resolved concrete model
           (governance); this is what makes per-step model selection reach the command.
        2. construction-time ``config.model`` — the container's per-step ``--model``
           selection (legacy LAW-2 path).
        3. neither ⇒ no ``--model`` flag (PI uses its own default).

        PI exposes no verified separate reasoning-effort flag, so only ``--model`` is
        forwarded (see :class:`PiHeadlessConfig`).
        """
        args = [
            self._config.pi_bin,
            "--mode",
            "json",
            "--tools",
            ",".join(self._config.tools),
        ]
        model = self._resolve_model(request)
        if model is not None:
            args += ["--model", model]
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

    # -- result extraction (WS-PI-2) -------------------------------------

    def _result_from_output(
        self,
        request: AgentRunRequest,
        stdout: str,
        returncode: int,
    ) -> AgentRunResult:
        message = self._last_message_end(stdout)
        if message is None:
            # Degraded fallback: no usable message_end. Never crash.
            text = (stdout or "").strip()
            # FR1 (bug: pi-headless-nonzero-exit-misreported): ANY non-zero returncode is
            # a FAILED run, regardless of whether stdout carries text — a pi setup failure
            # (e.g. a missing API key) still emits a JSONL session/event preamble to stdout
            # before dying, and the old ``and not text`` conjunct let that non-empty
            # preamble mask the real failure as SUCCEEDED. ``error=""`` here is
            # deliberate: ``run()``'s existing stderr-backfill (lines 138-144) fires
            # whenever a FAILED result carries an empty ``error`` and threads the real
            # (redacted) ``proc.stderr``/``proc.stdout`` in — no additional plumbing
            # needed here. This mirrors ``CodexExecAdapter.run``'s returncode-first check
            # (``codex_runtime.py:150-157``).
            if returncode != 0:
                return AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary="pi headless returned non-zero exit",
                    error="",
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
        for key in ("verdict", "commit_sha", "task_group"):
            value = payload.get(key)
            if value is not None:
                structured[key] = self._redact(str(value))
        extra = payload.get("structured_output")
        if isinstance(extra, dict):
            for key, value in extra.items():
                structured[str(key)] = self._redact(str(value))
        return structured
