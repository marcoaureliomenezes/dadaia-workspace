"""Headless OpenCode runtime adapter for lifecycle worker requests.

Structurally a twin of ``PiHeadlessAdapter`` (``pi_runtime.py``) and
``CodexExecAdapter`` (``codex_runtime.py``): an infrastructure-only,
subprocess-backed adapter behind ``AgentRuntimePort``. It drives the ``opencode``
CLI headless as::

    opencode run --format json --model <provider/model> [--print-logs] <prompt>

The prompt is passed as a single positional argument (``opencode run`` takes the
message on argv — verified via ``opencode run --help``), which avoids any shell
interpolation: the argv list is handed to the runner unparsed.

No OpenCode client is imported at module load — subprocess only — so
offline-first is preserved and the unit suite runs fully faked through an
injected runner.

Parsed output contract (ADR-23-2 — success-path verified-on-operator-live-run)
------------------------------------------------------------------------------
``opencode run --format json`` emits a **line-delimited JSON event stream**: one
JSON object per line, each discriminated by a ``"type"`` field.

VERIFIED (via the fast-fail invalid-model probe, no credits spent)::

    opencode run --format json --model invalid/invalid "ping"
    -> {"type":"error","timestamp":<int>,"sessionID":"ses_...",
        "error":{"name":"UnknownError","data":{"message":"Model not found: ..."}}}

So the ``error`` event shape — ``{"type":"error", "error":{"name", "data":
{"message"}}}`` — is verified, and is mapped to ``FAILED`` with the inner
``message`` as the error string. The process exit code is ``0`` even when the
stream reports an error, so completion is driven by the stream, not the return
code.

DEFENSIVE (success-path schema is upstream-owned; only fully verified on the
operator's live run, ADR-23-2): assistant text is harvested from whatever
message/part events carry it — any event whose payload contains a ``text`` field
(directly, under ``part``/``message``, or in a content-block list) contributes,
in stream order. The adapter NEVER raises on an unexpected event shape: non-JSON
lines are skipped, unknown ``type`` values are ignored, and if no usable text is
found the adapter degrades to a summary of the collected raw output (SUCCEEDED).
A trailing/last meaningful text wins for the summary; stream end is treated as
completion.

``changed_paths`` is sourced from ``git diff`` (the injected ``git`` client),
never from a model self-report — that is what gives OpenCode a real Ring-2 write
boundary, matching ``PiHeadlessAdapter``.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)

Runner = Callable[..., subprocess.CompletedProcess[str]]

_DEFAULT_ENV_ALLOWLIST = (
    "OPENCODE",
    "OPENCODE_CONFIG",
    "OPENCODE_SERVER_PASSWORD",
    "PATH",
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "TERM",
)
_SECRET_NAME_PARTS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")


class _GitDiffPort(Protocol):
    """Narrow git seam the adapter needs — satisfied by ``GitSubprocessClient``."""

    def diff_name_only(self, path: Path) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class OpenCodeConfig:
    """Explicit controls for one headless OpenCode adapter instance."""

    cwd: Path
    opencode_bin: str = "opencode"
    model: str | None = None
    timeout_seconds: int = 900
    env_allowlist: tuple[str, ...] = _DEFAULT_ENV_ALLOWLIST


class OpenCodeAdapter:
    """Run bounded lifecycle worker prompts through ``opencode run --format json``.

    The adapter is infrastructure-only: it never decides lifecycle transitions, it
    only returns a structured ``AgentRunResult`` for Python services to validate.
    ``changed_paths`` is sourced from ``git diff`` (the injected ``git`` client),
    never from a model self-report — that is what gives OpenCode a real Ring-2 write
    boundary.
    """

    def __init__(
        self,
        *,
        cwd: Path | None = None,
        config: OpenCodeConfig | None = None,
        runner: Runner = subprocess.run,
        environ: Mapping[str, str] | None = None,
        git: _GitDiffPort | None = None,
    ) -> None:
        if config is None:
            config = OpenCodeConfig(cwd=cwd or Path.cwd())
        self._config = config
        self._runner = runner
        self._environ = environ if environ is not None else os.environ
        self._git = git

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.OPENCODE_RUN

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if request.runtime is not AgentRuntimeKind.OPENCODE_RUN:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="request runtime does not match OpenCodeAdapter",
                error=f"unsupported runtime: {request.runtime.value}",
            )

        args = self._command(request)
        try:
            proc = self._runner(
                args,
                cwd=self._config.cwd,
                env=self._env(),
                text=True,
                capture_output=True,
                timeout=self._config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="opencode run timed out",
                error=self._redact(str(exc)),
            )
        except OSError as exc:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="opencode run failed to start",
                error=self._redact(str(exc)),
            )

        result = self._result_from_output(proc.stdout, proc.stderr, proc.returncode)
        if result.status is AgentRunStatus.FAILED:
            return result
        return self._with_changed_paths(result)

    def _command(self, request: AgentRunRequest) -> list[str]:
        args = [self._config.opencode_bin, "run", "--format", "json"]
        if self._config.model is not None:
            args += ["--model", self._config.model]
        # Prompt as a single positional argument (no shell interpolation).
        args.append(request.prompt)
        return args

    def _env(self) -> dict[str, str]:
        return {
            key: self._environ[key] for key in self._config.env_allowlist if key in self._environ
        }

    # -- result extraction (defensive line-delimited JSON, ADR-23-2) ------

    def _result_from_output(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
    ) -> AgentRunResult:
        error_message: str | None = None
        texts: list[str] = []

        for line in (stdout or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError:
                # Tolerate non-JSON lines (logs, banners) — never crash.
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "error":
                error_message = self._error_message(event) or error_message
                continue
            self._collect_text(event, texts)

        if error_message is not None:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="opencode run reported an error event",
                error=self._redact(error_message),
            )

        assistant_text = "".join(texts).strip()
        if assistant_text:
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(assistant_text),
            )

        # Degraded fallback: no usable text harvested. Never crash.
        raw = (stdout or "").strip()
        if returncode != 0 and not raw:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="opencode run returned non-zero exit",
                error=self._redact((stderr or "").strip()),
            )
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=self._redact(raw or "opencode run completed"),
        )

    @staticmethod
    def _error_message(event: dict[str, object]) -> str | None:
        error = event.get("error")
        if isinstance(error, dict):
            data = error.get("data")
            if isinstance(data, dict):
                message = data.get("message")
                if isinstance(message, str) and message:
                    return message
            name = error.get("name")
            if isinstance(name, str) and name:
                return name
        if isinstance(error, str) and error:
            return error
        return None

    @classmethod
    def _collect_text(cls, node: object, texts: list[str]) -> None:
        """Harvest assistant text from any event shape, defensively.

        The success-path event schema is upstream-owned (ADR-23-2). Rather than
        bind to one shape, walk message/part payloads and gather every ``text``
        string that belongs to a text-typed node, in stream order.
        """
        if isinstance(node, dict):
            node_type = node.get("type")
            text = node.get("text")
            if isinstance(text, str) and text and node_type in (None, "text", "text-delta"):
                texts.append(text)
            for key in ("part", "message", "content", "parts", "delta", "info"):
                if key in node:
                    cls._collect_text(node[key], texts)
        elif isinstance(node, list):
            for item in node:
                cls._collect_text(item, texts)

    # -- changed_paths via git diff (Ring-2 root-cause) -------------------

    def _with_changed_paths(self, result: AgentRunResult) -> AgentRunResult:
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
