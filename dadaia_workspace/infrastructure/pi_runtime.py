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
import re
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

_FENCED_JSON = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


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
        """Parse the step's structured result object from the assistant message.

        The result object is the in-band channel the Python gate reads (a review step's
        ``verdict``; every step's ``artifact_refs`` / schema evidence). A compliant worker
        emits it as a fenced ```json block, but real GPT/Codex workers — pi runs on the
        operator's OpenAI Codex subscription — frequently emit the JSON object **bare**:
        the whole final message *is* the object, no fence. Both shapes are accepted
        (proven by the v0.1.31 real-worker e2e, where gpt-5.5 emitted a schema-correct
        payload unfenced and the strict fenced-only parse silently dropped it →
        ``artifact evidence missing`` block). Candidates are tried fenced-first, then the
        whole stripped message, then the outermost ``{...}`` slice. The payload must be a
        dict whose ``schema`` equals ``expected_schema``; otherwise None (absent /
        unparseable / schema mismatch).
        """
        if expected_schema is None:
            return None
        for candidate in PiHeadlessAdapter._json_candidates(assistant_text):
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if PiHeadlessAdapter._is_result_payload(payload, expected_schema):
                return payload
        return None

    @staticmethod
    def _is_result_payload(payload: dict[str, object], expected_schema: str) -> bool:
        """Decide whether a parsed dict IS this step's structured result object.

        Two acceptance paths:

        1. **Exact** — the worker labelled the transport ``schema`` field with the
           requested ``expected_schema`` id. This is the documented happy path.
        2. **Structural (real-worker tolerance, v0.1.31 R3)** — a real GPT/Codex worker
           reliably emits the result *object* but labels the ``schema`` field
           inconsistently across runs: it omits it, or names the fragment's domain schema
           (e.g. ``release-scope-handoff-v1``) instead of the transport id
           (``agent-run-result-v1``) — both observed in the live e2e. Rather than BLOCK a
           correct result on a label mismatch, accept a payload that *structurally is* the
           result: a non-empty ``artifact_refs`` list plus a ``status`` / ``summary`` /
           nested ``structured_output``. This degrades safely — arbitrary JSON lacking the
           result shape is still rejected (the gate's downstream evidence/scope checks
           still apply).
        """
        if payload.get("schema") == expected_schema:
            return True
        refs = payload.get("artifact_refs")
        if isinstance(refs, list) and refs:
            return any(key in payload for key in ("status", "summary", "structured_output"))
        return False

    @staticmethod
    def _json_candidates(text: str) -> list[str]:
        """Ordered JSON-string candidates from an assistant message, most-precise first.

        1. each fenced ```json block (the documented contract);
        2. the whole stripped message (a bare JSON object — the common real-worker shape);
        3. the outermost ``{...}`` slice (a JSON object trailing some prose).
        """
        candidates: list[str] = [match.group(1) for match in _FENCED_JSON.finditer(text or "")]
        stripped = (text or "").strip()
        if stripped:
            candidates.append(stripped)
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start != -1 and end > start:
                candidates.append(stripped[start : end + 1])
        return candidates

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
