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
    WorkerDiagnostic,
)
from dadaia_workspace.infrastructure.headless_adapter_base import (
    Runner,
    SubprocessAdapterMixin,
    _GitDiffPort,
    changed_paths_csv,
    derive_result_summary,
    findings_json,
    missing_artifact_refs,
    normalize_artifact_refs,
    salvage_result_from_handoff,
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

#: v0.1.78 T-D / FR-D: bound on the redacted diagnostic ``output_tail`` — never an
#: unbounded raw stdout dump.
_MAX_DIAGNOSTIC_TAIL = 4096


@dataclass(frozen=True)
class PiHeadlessConfig:
    """Explicit controls for one headless PI adapter instance.

    ``model`` is the provider-qualified Layer-2 model id (LAW 2 / ADR-B). GPT ids must
    use the ``openai-codex/`` provider backed by the operator's Codex subscription; the
    adapter rejects ambiguous or other-provider GPT ids before spawning PI. The id is
    passed verbatim as ``pi --model <id>``. ``reasoning_effort``
    carries the chosen option's effort — ``low``/``medium``/``high`` — and is forwarded
    verbatim as ``pi --thinking <level>`` (v0.1.78 T-D / FR-D: installed PI >= 0.80.3
    supports ``--thinking``; the prior "no verified flag" limitation is resolved).
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
        runner: Runner | None = None,
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

    def _resolve_runner(self) -> Runner:
        """Resolve the subprocess runner at CALL time, not construction time.

        When no ``runner=`` was injected at construction, ``self._runner`` is
        ``None`` and this performs a live, module-qualified lookup of
        ``subprocess.run`` — evaluated fresh on every call, mirroring
        ``git_subprocess.py``'s pattern. This is what makes
        ``monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake)``
        genuinely interceptable: the old ``runner: Runner = subprocess.run``
        default-argument snapshot bound the real function object once, at
        class-definition (import) time, so a later monkeypatch of the module
        attribute never reached an already-constructed adapter.
        """
        return self._runner if self._runner is not None else subprocess.run

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if request.runtime is not AgentRuntimeKind.PI_HEADLESS:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="request runtime does not match PiHeadlessAdapter",
                error=f"unsupported runtime: {request.runtime.value}",
            )

        try:
            args = self._command(request)
        except ValueError as exc:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="pi headless rejected unsafe model provider",
                error=self._redact(str(exc)),
            )
        try:
            proc = self._resolve_runner()(
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
                    diagnostic=result.diagnostic,
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

        v0.1.78 T-D / FR-D: the reasoning effort follows the SAME ordered precedence and
        is forwarded as ``pi --thinking <level>`` (installed PI >= 0.80.3).
        """
        args = [
            self._config.pi_bin,
            "--mode",
            "json",
            # Lifecycle prompts already carry their complete persona, fragments, bounded
            # context, and execution root. Loading parent/global AGENTS.md files here can
            # redirect a nested disposable worker into another workspace, including writes
            # outside the adapter's Ring-2 boundary.
            "--no-context-files",
            "--tools",
            ",".join(self._config.tools),
        ]
        model = self._resolve_model(request)
        if model is not None:
            self._validate_model_provider(model)
            args += ["--model", model]
        reasoning = self._resolve_reasoning(request)
        if reasoning is not None:
            args += ["--thinking", reasoning]
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

    @staticmethod
    def _validate_model_provider(model: str) -> None:
        """Prevent GPT calls from escaping the operator's Codex subscription."""
        if "gpt" in model.lower() and not model.startswith("openai-codex/"):
            raise ValueError(
                "PI GPT models must use the explicit openai-codex/ provider; "
                f"refusing ambiguous or non-subscription model {model!r}"
            )

    def _resolve_reasoning(self, request: AgentRunRequest) -> str | None:
        """Resolve the requested reasoning effort — mirrors :meth:`_resolve_model`'s
        ordered precedence (resolved_model wins over construction-time config)."""
        if request.resolved_model is not None:
            return request.resolved_model.reasoning
        return self._config.reasoning_effort

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
            diagnostic = self._diagnostic(
                request,
                exit_code=returncode,
                parser_classification="no-result",
                output_tail=text or stdout or "",
            )
            if returncode != 0:
                return AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary="pi headless returned non-zero exit",
                    error="",
                    diagnostic=diagnostic,
                )
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(text or "pi headless completed"),
                diagnostic=diagnostic,
            )

        assistant_text = self._extract_text(message.get("content"))
        verdict_payload = self._extract_result_payload(assistant_text, request.expected_schema)

        if verdict_payload is not None:
            summary = derive_result_summary(verdict_payload) or assistant_text
            refs = normalize_artifact_refs(verdict_payload)
            # Findings survive into the flat structured map (bug
            # step-payload-drops-worker-findings) — codex parity.
            structured = self._structured_from_verdict(verdict_payload)
            findings = findings_json(verdict_payload)
            if findings is not None and "findings" not in structured:
                structured["findings"] = self._redact(findings)
            changed = changed_paths_csv(verdict_payload)
            if changed is not None and "changed_paths" not in structured:
                structured["changed_paths"] = self._redact(changed)
            missing_refs = missing_artifact_refs(refs, self._config.cwd)
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(summary or "pi headless completed"),
                artifact_refs=tuple(self._redact(path) for path in refs),
                structured_output=structured,
                domain_payload=self._redact_json(verdict_payload),  # type: ignore[arg-type]
                diagnostic=(
                    None
                    if refs and not missing_refs
                    else self._diagnostic(
                        request,
                        exit_code=returncode,
                        parser_classification=(
                            "referenced-artifact-missing"
                            if missing_refs
                            else "result-without-artifact-refs"
                        ),
                        output_tail=assistant_text or stdout or "",
                    )
                ),
            )

        # SALVAGE (bug prose-worker-with-valid-handoff-loses-verdict): a prose message
        # naming an existing on-disk handoff yields a result grounded in that file.
        salvaged = salvage_result_from_handoff(assistant_text, self._config.cwd)
        if salvaged is not None:
            structured = {}
            verdict = salvaged.get("verdict")
            if isinstance(verdict, str):
                structured["verdict"] = self._redact(verdict)
                reason = salvaged.get("verdict_reason")
                if isinstance(reason, str):
                    structured["verdict_reason"] = self._redact(reason)
            findings = findings_json(salvaged)
            if findings is not None:
                structured["findings"] = self._redact(findings)
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(derive_result_summary(salvaged) or "pi headless completed"),
                artifact_refs=tuple(
                    self._redact(path) for path in normalize_artifact_refs(salvaged)
                ),
                structured_output=structured,
                domain_payload=self._redact_json(salvaged),  # type: ignore[arg-type]
            )

        # Noncompliant: a real message_end arrived but carried no recognizable result
        # payload (no-op prose / shapeless JSON) — the gate BLOCKs on empty artifact_refs
        # (agent_runner.py), and this diagnostic is the evidence for WHY (bug
        # worker-noncompliance-block-carries-no-diagnostic-evidence).
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=self._redact(assistant_text or "pi headless completed"),
            diagnostic=self._diagnostic(
                request,
                exit_code=returncode,
                parser_classification="no-artifact-refs",
                output_tail=assistant_text or stdout or "",
            ),
        )

    def _diagnostic(
        self,
        request: AgentRunRequest,
        *,
        exit_code: int | None,
        parser_classification: str,
        output_tail: str,
    ) -> WorkerDiagnostic:
        """Build the redacted, bounded :class:`WorkerDiagnostic` for a degraded/noncompliant
        result (v0.1.78 T-D / FR-D)."""
        tail = self._redact((output_tail or "").strip())
        if len(tail) > _MAX_DIAGNOSTIC_TAIL:
            tail = tail[-_MAX_DIAGNOSTIC_TAIL:]
        return WorkerDiagnostic(
            runtime=AgentRuntimeKind.PI_HEADLESS.value,
            model=self._resolve_model(request),
            requested_reasoning=self._resolve_reasoning(request),
            # No verified in-band signal for the ACTUAL thinking level PI ran at (that
            # metadata lives only in PI's own on-disk session store, a separate data
            # source from this subprocess's `--mode json` stdout stream) — left unset
            # rather than fabricated. See PiHeadlessConfig / _resolve_reasoning.
            actual_reasoning=None,
            exit_code=exit_code,
            parser_classification=parser_classification,
            output_tail=tail,
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
