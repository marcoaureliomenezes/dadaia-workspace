"""Headless PI runtime adapter for lifecycle worker requests.

Structurally a twin of ``CodexExecAdapter`` (``codex_runtime.py``): an
infrastructure-only, subprocess-backed adapter behind ``AgentRuntimePort``. It
drives the ``pi`` CLI headless as ``pi --mode json`` — a deterministic,
line-delimited JSON event stream whose LAST ``{"type":"message_end",...}`` event
carries the assistant ``AgentMessage``.

No ``pi`` client is imported at module load — subprocess only — so offline-first
is preserved and the unit suite runs fully faked through an injected runner.
"""

from __future__ import annotations

import json
import os
import re
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
    "ANTHROPIC_API_KEY",
    "PATH",
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "TERM",
)
_SECRET_NAME_PARTS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")

_FENCED_JSON = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


class _GitDiffPort(Protocol):
    """Narrow git seam the adapter needs — satisfied by ``GitSubprocessClient``."""

    def diff_name_only(self, path: Path) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class PiHeadlessConfig:
    """Explicit controls for one headless PI adapter instance."""

    cwd: Path
    pi_bin: str = "pi"
    model: str | None = None
    timeout_seconds: int = 900
    env_allowlist: tuple[str, ...] = _DEFAULT_ENV_ALLOWLIST
    tools: tuple[str, ...] = ("read", "write", "edit", "bash")


class PiHeadlessAdapter:
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

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.PI_HEADLESS

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if request.runtime is not AgentRuntimeKind.PI_HEADLESS:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="request runtime does not match PiHeadlessAdapter",
                error=f"unsupported runtime: {request.runtime.value}",
            )

        args = self._command()
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

    def _command(self) -> list[str]:
        args = [
            self._config.pi_bin,
            "--mode",
            "json",
            "--tools",
            ",".join(self._config.tools),
        ]
        if self._config.model is not None:
            args += ["--model", self._config.model]
        args += ["-p", "-"]
        return args

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
            if returncode != 0 and not text:
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
        verdict_payload = self._verdict_payload(assistant_text, request.expected_schema)

        if verdict_payload is not None:
            summary = str(verdict_payload.get("summary", assistant_text))
            refs_raw = verdict_payload.get("artifact_refs", [])
            refs = refs_raw if isinstance(refs_raw, list) else []
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(summary or "pi headless completed"),
                artifact_refs=tuple(self._redact(item) for item in refs if isinstance(item, str)),
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

    @staticmethod
    def _verdict_payload(
        assistant_text: str,
        expected_schema: str | None,
    ) -> dict[str, object] | None:
        """Parse a fenced ```json verdict block matching the requested schema.

        The fenced-JSON sentinel is the in-band channel for review verdicts ONLY,
        not the primary transport. Returns None when absent / unparseable / schema
        mismatch.
        """
        if expected_schema is None:
            return None
        match = _FENCED_JSON.search(assistant_text)
        if match is None:
            return None
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("schema") != expected_schema:
            return None
        return payload

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

    # -- changed_paths via git diff (Ring-2 root-cause, WS-PI-2) ----------

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
