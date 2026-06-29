"""Exec-backed Codex runtime adapter for lifecycle worker requests.

The security-relevant invariants shared with the other real adapters — secret
redaction, the env-allowlist filter, the git ``changed_paths`` override, the
``Runner`` seam, and the prompt envelope — live in
:mod:`dadaia_workspace.infrastructure.headless_adapter_base`. This module keeps
only the genuinely Codex-CLI-specific logic (``_command``, ``_model_and_effort``,
effort narrowing, the ``--output-last-message`` read, and result extraction).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

from dadaia_workspace.core.model_registry import CodexEffort, codex_tier_views
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
    "PATH",
    "HOME",
    "CODEX_HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "TERM",
)

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


def _workspace_state_root(cwd: Path) -> Path:
    """Return the workspace root whose `.dadaia/tmp` may hold runtime state.

    Lifecycle callers usually pass the dadaia workspace root as cwd. Tests and direct
    adapter probes may pass a throwaway fixture. Walk upward so a repo cwd resolves to the
    containing workspace instead of creating a forbidden repo-local `.dadaia/` directory.
    """
    current = cwd.resolve()
    for candidate in (current, *current.parents):
        marker = candidate / ".dadaia"
        if marker.is_dir() and (candidate / "repos").is_dir():
            return candidate
    return current


def _copy_codex_runtime_file(src: Path, dest: Path) -> None:
    """Copy a non-secret-path runtime file into isolated CODEX_HOME when available."""
    if not src.is_file():
        return
    try:
        shutil.copy2(src, dest)
        dest.chmod(0o600)
    except OSError:
        # The adapter can still start without optional config/auth; Codex will surface any
        # real authentication failure in its own stderr, which we redact before returning.
        return


@dataclass(frozen=True)
class CodexExecConfig:
    """Explicit controls for one Codex exec adapter instance."""

    cwd: Path
    codex_bin: str = "codex"
    model: str | None = None
    reasoning_effort: CodexEffort | None = None
    # Lifecycle workers must be able to write scoped artifacts (handoffs, specs, reports).
    # Codex CLI also initializes local client state before answering. A read-only Codex
    # sandbox fails before the Python workflow gates can evaluate the worker result.
    sandbox: str = "workspace-write"
    # Codex CLI 0.142.x no longer accepts the historical
    # ``--ask-for-approval <policy>`` flag. Approval policy is owned by Codex config /
    # command approval rules; the workflow adapter controls sandbox, cwd, model, and
    # output capture only.
    approval_policy: str = "never"
    env_allowlist: tuple[str, ...] = _DEFAULT_ENV_ALLOWLIST
    timeout_seconds: int = 900
    isolate_home: bool = True


class CodexExecAdapter(SubprocessAdapterMixin):
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

    def _env(self) -> dict[str, str]:
        env = super()._env()
        if not self._config.isolate_home:
            return env

        root = _workspace_state_root(self._config.cwd)
        runtime_root = root / ".dadaia" / "tmp" / "codex-runtime"
        home = runtime_root / "home"
        codex_home = runtime_root / "codex-home"
        xdg_root = runtime_root / "xdg"
        for path in (
            home,
            codex_home,
            xdg_root / "config",
            xdg_root / "cache",
            xdg_root / "data",
        ):
            path.mkdir(parents=True, exist_ok=True)

        source_codex_home = Path(
            self._environ.get("CODEX_HOME")
            or Path(self._environ.get("HOME", str(Path.home()))) / ".codex"
        )
        _copy_codex_runtime_file(source_codex_home / "auth.json", codex_home / "auth.json")
        _copy_codex_runtime_file(source_codex_home / "config.toml", codex_home / "config.toml")

        env["HOME"] = str(home)
        env["CODEX_HOME"] = str(codex_home)
        env["XDG_CONFIG_HOME"] = str(xdg_root / "config")
        env["XDG_CACHE_HOME"] = str(xdg_root / "cache")
        env["XDG_DATA_HOME"] = str(xdg_root / "data")
        return env

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
            result = self._result_from_output(request, output_path, proc)
            result = self._with_written_handoff_result(request, result, started_at=started_at)
            return self._with_changed_paths(result)

    def _command(self, request: AgentRunRequest, output_path: Path) -> list[str]:
        model, effort = self._model_and_effort(request)
        args = [
            self._config.codex_bin,
            "exec",
            "--ignore-user-config",
            "--sandbox",
            self._config.sandbox,
            "--cd",
            str(self._config.cwd),
            "--skip-git-repo-check",
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

    def _result_from_output(
        self,
        request: AgentRunRequest,
        output_path: Path,
        proc: subprocess.CompletedProcess[str],
    ) -> AgentRunResult:
        """Parse the codex ``--output-last-message`` text into an ``AgentRunResult``.

        v0.1.32 (D-5 / OQ-3) brings codex to pi parity: the result object is extracted
        through the SHARED :meth:`_extract_result_payload`, so codex gains the same
        fenced-or-bare candidate scan and the same strict-primary + structural-fallback
        acceptance — and the same **reject-guard** (a parsed dict lacking the result shape
        no longer maps to a result; C4). The previous degraded fallbacks are preserved:
        unparseable text → a redacted prose-summary ``SUCCEEDED``; a non-dict JSON value →
        a ``structured_output`` value; a dict that is NOT the result object → a redacted
        prose summary with EMPTY ``artifact_refs`` (which BLOCKs a create step, matching
        pi). Every surfaced field is ``_redact``-scrubbed (CWE-209).
        """
        try:
            raw = output_path.read_text(encoding="utf-8")
        except OSError:
            raw = proc.stdout

        # PRIMARY: shared strict-primary / structural-fallback result extraction.
        payload = self._extract_result_payload(raw, request.expected_schema)
        if payload is not None:
            refs = normalize_artifact_refs(payload)
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(str(payload.get("summary", "codex exec completed"))),
                artifact_refs=tuple(self._redact(path) for path in refs),
                structured_output=self._structured_from_payload(payload),
            )

        # FALLBACK: no result object was accepted — degrade safely (never crash, no
        # synthesized artifact_refs — the reject-guard C4 keeps a shapeless dict from
        # mapping to a result).
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(raw.strip() or "codex exec completed"),
            )
        if not isinstance(parsed, dict):
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="codex exec completed",
                structured_output={"value": self._redact(str(parsed))},
            )
        # A parsed dict that is NOT this step's result object: keep a redacted summary if
        # present, but emit NO artifact_refs / verdict (reject-guard parity with pi).
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=self._redact(str(parsed.get("summary", "codex exec completed"))),
        )

    def _structured_from_payload(self, payload: dict[str, object]) -> dict[str, str]:
        """Flatten a result payload's ``structured_output`` into the redacted string map."""
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
        """Recover a valid handoff written to disk when Codex's final message is prose.

        Real Codex workers sometimes write the required handoff file but do not echo the
        result wrapper/handoff JSON as their last message. The lifecycle contract is the
        handoff artifact, so recover the newest matching handoff written during this run and
        surface its verdict/artifact to the Python gate.
        """
        if result.artifact_refs or result.structured_output.get("verdict"):
            return result
        handoff = self._latest_written_handoff(request, started_at=started_at)
        if handoff is None:
            return result
        ref, payload = handoff
        structured = self._structured_from_payload(payload)
        return AgentRunResult(
            status=result.status,
            summary=result.summary,
            artifact_refs=(ref,),
            structured_output=structured,
            error=result.error,
        )

    def _latest_written_handoff(
        self,
        request: AgentRunRequest,
        *,
        started_at: float,
    ) -> tuple[str, dict[str, object]] | None:
        workspace = _workspace_state_root(self._config.cwd)
        handoff_dir = workspace / ".dadaia" / "handoff" / request.context
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
            rel = path.resolve().relative_to(workspace.resolve()).as_posix()
            matches.append((stat.st_mtime, rel, payload))
        if not matches:
            return None
        _mtime, rel, payload = max(matches, key=lambda item: item[0])
        return rel, payload
