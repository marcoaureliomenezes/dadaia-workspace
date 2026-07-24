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
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

from dadaia_workspace.core.exceptions import CodexConfigError
from dadaia_workspace.core.model_registry import CodexEffort, codex_tier_views
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
    "PYTHONDONTWRITEBYTECODE",
    "PATH",
    "HOME",
    "CODEX_HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "TERM",
)

_VALID_CODEX_EFFORTS: frozenset[str] = frozenset(get_args(CodexEffort))

#: FR5 (v0.1.66) — the finite set of `codex exec --sandbox` values this adapter accepts,
#: identical to codex-cli's own accepted set. The compiled-in default is "read-only"; the
#: env override MUST resolve to one of these or construction fails loudly (AC5.3).
_VALID_CODEX_SANDBOX_MODES: frozenset[str] = frozenset(
    {"read-only", "workspace-write", "danger-full-access"}
)

#: An opt-in dadaia-level directive (NOT a codex `--sandbox` value): run codex with
#: `--dangerously-bypass-approvals-and-sandbox` — no sandbox at all — instead of
#: `--sandbox <mode>`. Codex's `--sandbox` modes (even danger-full-access) still set up a
#: sandbox namespace via bwrap, which CANNOT be created in a nested/unprivileged container
#: (bug codex-adapter-cannot-run-in-nested-container: "No permissions to create a new
#: namespace"). The bypass skips that entirely. Safe ONLY where the OUTER container is the
#: trust boundary (e.g. the Hermes worker, which already runs its own agent this way) — so
#: it is opt-in via DADAIA_CODEX_SANDBOX and never the default; the outer `dadaia lifecycle`
#: allowed-paths/review gates remain the real security boundary (same reasoning as FR5).
_SANDBOX_BYPASS = "danger-bypass"
_ACCEPTED_SANDBOX_VALUES: frozenset[str] = _VALID_CODEX_SANDBOX_MODES | {_SANDBOX_BYPASS}

#: FR5 (v0.1.66) — the environment-variable override read at ``CodexExecConfig``
#: construction (the single choke point — architect finding MEDIUM-1). Overrides the
#: compiled-in "read-only" default ONLY when the caller did not pass an explicit
#: ``sandbox=`` value; an explicit caller value always wins over the env var.
_DADAIA_CODEX_SANDBOX_ENV = "DADAIA_CODEX_SANDBOX"
_DEFAULT_CODEX_SANDBOX = "read-only"
_MAX_DIAGNOSTIC_TAIL = 4_000


#: Sandbox-failure stderr signatures (exit-0 deception guards). Matched against STDERR
#: ONLY: codex-cli/bwrap write namespace errors to stderr, while the worker event
#: stream (stdout) legitimately echoes source files that merely MENTION these strings
#: (e.g. this repo's own tests) — scanning stdout would false-positive every
#: self-hosting audit. Each tuple's parts must ALL appear (lowercased).
_SANDBOX_FAILURE_SIGNATURES: tuple[tuple[str, ...], ...] = (
    ("rtm_newaddr",),  # bwrap loopback setup failure (nested/unprivileged container)
    ("no permissions to create a new namespace",),  # codex-adapter-cannot-run-in-nested-container
    ("bwrap:", "permission denied"),
    ("landlock", "operation not permitted"),
)


def _sandbox_failure_signature(stderr_text: str) -> str | None:
    """Return an actionable error when *stderr_text* carries a sandbox-failure signature.

    Bug lifecycle-audit-worker-sandbox-cannot-read-bound-repo +
    codex-exec-sandbox-unusable-in-container: codex exec can exit 0 while its sandbox
    (bwrap namespace / landlock) made every tool call fail — the signature means the
    worker could not have inspected or written anything, so its result is fake
    evidence. ``None`` means no signature (the zero-exit happy path is untouched).
    """
    lowered = stderr_text.lower()
    for parts in _SANDBOX_FAILURE_SIGNATURES:
        if all(part in lowered for part in parts):
            return (
                "codex exec exited 0 but its stderr carries a sandbox-failure "
                f"signature ({' + '.join(parts)!r}): the sandbox namespace (bwrap/"
                "landlock) could not be created or denied workspace writes, so the "
                "worker inspected/wrote nothing. Remedies: set "
                "DADAIA_CODEX_SANDBOX=danger-bypass (nested container — runs codex "
                "without a sandbox; the outer container is the trust boundary) or "
                "DADAIA_CODEX_SANDBOX=danger-full-access (landlock write-denial), then "
                "re-run the workflow."
            )
    return None


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


@dataclass(frozen=True)
class CodexExecConfig:
    """Explicit controls for one Codex exec adapter instance.

    FR5 (v0.1.66): ``sandbox`` defaults to ``None`` (a sentinel, not the concrete
    value) so :meth:`__post_init__` — the single choke point every ``CodexExecConfig``
    construction passes through, regardless of call site — can tell "caller passed
    nothing" apart from "caller explicitly chose a value". When ``sandbox is None`` the
    resolved value is ``DADAIA_CODEX_SANDBOX`` if set, else the compiled-in default
    ``"read-only"``; an explicit caller-supplied ``sandbox`` always wins over the env
    var. The resolved value is ALWAYS validated against
    :data:`_VALID_CODEX_SANDBOX_MODES` before the instance is usable — an unrecognized
    value (from either the caller or the env var) raises ``ValueError`` at construction,
    never silently reaching `codex exec` unvalidated.
    """

    cwd: Path
    codex_bin: str = "codex"
    model: str | None = None
    reasoning_effort: CodexEffort | None = None
    sandbox: str | None = None
    # Retained for back-compat only (W1-1): `codex exec` never prompts — approval is
    # structurally "never" in the exec subcommand — so this policy is no longer emitted
    # into the argv. Passing the interactive-only `--ask-for-approval` flag to exec is
    # rejected by codex-cli 0.142.4 ("unexpected argument"). The field stays so existing
    # constructors keep working; it is intentionally not wired into `_command`.
    approval_policy: str = "never"
    env_allowlist: tuple[str, ...] = _DEFAULT_ENV_ALLOWLIST
    timeout_seconds: int = 900

    def __post_init__(self) -> None:
        resolved = self.sandbox
        if resolved is None:
            resolved = os.environ.get(_DADAIA_CODEX_SANDBOX_ENV) or _DEFAULT_CODEX_SANDBOX
        if resolved not in _ACCEPTED_SANDBOX_VALUES:
            valid = ", ".join(sorted(_ACCEPTED_SANDBOX_VALUES))
            raise CodexConfigError(
                f"invalid Codex sandbox mode {resolved!r}; valid: {valid} "
                f"(set via CodexExecConfig(sandbox=...) or the {_DADAIA_CODEX_SANDBOX_ENV} "
                "environment variable)"
            )
        # frozen dataclass: __setattr__ is disabled outside __init__/__post_init__, so
        # the resolved concrete value is stored back via object.__setattr__ (the
        # documented escape hatch for frozen dataclasses) — every reader of
        # `self.sandbox` from here on sees the final, validated string, never the
        # sentinel or an unvalidated env value.
        object.__setattr__(self, "sandbox", resolved)

    @property
    def resolved_sandbox(self) -> str:
        """The final, validated ``str`` sandbox mode — never ``None``.

        ``__post_init__`` always replaces the ``sandbox`` field with a concrete,
        validated string before construction returns, so this is a type-narrowing
        accessor (not a second resolution path) for readers like ``_command``.
        """
        assert self.sandbox is not None, "CodexExecConfig.__post_init__ always resolves sandbox"
        return self.sandbox

    @property
    def bypass_sandbox(self) -> bool:
        """True iff the resolved directive is the opt-in no-sandbox bypass.

        When True, ``_command`` emits ``--dangerously-bypass-approvals-and-sandbox`` INSTEAD
        of ``--sandbox <mode>`` (the two are mutually exclusive) so codex runs without a
        sandbox namespace — the only way it executes inside a nested/unprivileged container.
        """
        return self.sandbox == _SANDBOX_BYPASS


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
        self._runner = runner
        self._environ = environ if environ is not None else os.environ
        self._git = git
        # Wire the mixin seams to this adapter's config.
        self._env_allowlist = config.env_allowlist
        self._cwd_for_diff = config.cwd

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.CODEX_EXEC

    def _resolve_runner(self) -> Runner:
        """Resolve the subprocess runner at CALL time, not construction time.

        When no ``runner=`` was injected at construction, ``self._runner`` is
        ``None`` and this performs a live, module-qualified lookup of
        ``subprocess.run`` — evaluated fresh on every call, mirroring
        ``git_subprocess.py``'s pattern and ``PiHeadlessAdapter._resolve_runner``.
        This is what makes
        ``monkeypatch.setattr("dadaia_workspace.infrastructure.codex_runtime.subprocess.run", fake)``
        genuinely interceptable: the old ``runner: Runner = subprocess.run``
        default-argument snapshot bound the real function object once, at
        class-definition (import) time, so a later monkeypatch of the module
        attribute never reached an already-constructed adapter.
        """
        return self._runner if self._runner is not None else subprocess.run

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
            before_snapshot = self._snapshot_changed_paths()
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
                stderr_text = (proc.stderr or proc.stdout or "").strip()
                summary, error = self._classify_failure(stderr_text)
                return AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary=summary,
                    error=self._redact(error),
                )
            # Bug lifecycle-audit-worker-sandbox-cannot-read-bound-repo +
            # codex-exec-sandbox-unusable-in-container: codex exec can EXIT 0 while every
            # tool call died inside the sandbox (bwrap namespace creation fails in a
            # nested/unprivileged container; landlock denies workspace writes). A zero
            # exit carrying the failure signature must NOT read as SUCCEEDED — otherwise
            # a read-nothing worker's vacuous report is accepted as real evidence.
            # Bug real-codex-resume-output-not-committed-to-ledger-042: under
            # `danger-bypass` codex runs with NO sandbox, so a signature on stderr can
            # never be a true positive — codex mirrors the agent event stream (which
            # echoes the prompt) to stderr, and a resumed run's prompt quotes the prior
            # sandbox block reason verbatim. Scanning it would fail every resume of a
            # sandbox-blocked run forever, even when the worker verifiably delivered.
            sandbox_error = (
                None
                if self._config.bypass_sandbox
                else _sandbox_failure_signature(proc.stderr or "")
            )
            if sandbox_error is not None:
                return AgentRunResult(
                    status=AgentRunStatus.FAILED,
                    summary="codex sandbox unusable in this environment",
                    error=self._redact(sandbox_error),
                )
            result = self._result_from_output(request, output_path, proc)
            return self._with_changed_paths(result, before_snapshot)

    @staticmethod
    def _classify_failure(stderr_text: str) -> tuple[str, str]:
        """Map a non-zero codex exec failure to ``(summary, error)``.

        An "unexpected argument" / "unrecognized" stderr means the argv carried a flag the
        installed codex-cli's ``exec`` subcommand does not accept (e.g. the interactive-only
        ``--ask-for-approval``, dropped in W1-1). That class is surfaced with an actionable
        message naming the incompatible-flag contract instead of the raw CLI complaint, so a
        future argv drift fails loudly at the adapter boundary rather than as an opaque
        non-zero exit. All other failures keep the raw (redacted) stderr.
        """
        lowered = stderr_text.lower()
        if "unexpected argument" in lowered or "unrecognized" in lowered:
            return (
                "codex exec rejected an argument (incompatible codex-cli flag contract)",
                (
                    "codex exec rejected an argument passed by the adapter — the installed "
                    "codex-cli's `exec` subcommand does not accept it. Interactive-only flags "
                    "(e.g. `--ask-for-approval`) must not be passed to `codex exec`; express "
                    "approval policy via `-c approval_policy=...` config override instead. "
                    f"Underlying codex-cli error: {stderr_text}"
                ),
            )
        return ("codex exec returned non-zero exit", stderr_text)

    def _command(self, request: AgentRunRequest, output_path: Path) -> list[str]:
        model, effort = self._model_and_effort(request)
        # W1-1: NO `--ask-for-approval` — that flag is interactive-only and is rejected by
        # `codex exec` on codex-cli 0.142.4 ("unexpected argument"). exec never prompts, so
        # approval policy needs no expression here (`CodexExecConfig.approval_policy` is kept
        # only for constructor back-compat).
        args = [
            self._config.codex_bin,
            "exec",
            "--ignore-user-config",
            # FR4 (v0.1.66): --ignore-user-config discards ~/.codex trust, so a governed
            # worker running in a directory codex does not auto-trust fails codex's own
            # "Not inside a trusted directory" check unless this flag is also present.
            # The outer `dadaia lifecycle` gate (allowed_paths/review gates) remains the
            # real security boundary regardless of codex's own trust posture (same
            # reasoning as the sandbox override in FR5) — this flag governs only whether
            # codex itself refuses to run, not what it is permitted to write.
            "--skip-git-repo-check",
            # Sandbox posture: normally `--sandbox <mode>` (secure default read-only). The
            # opt-in `danger-bypass` directive instead runs codex WITHOUT a sandbox
            # (`--dangerously-bypass-approvals-and-sandbox`) — mutually exclusive with
            # `--sandbox` — the only way codex executes inside a nested/unprivileged
            # container where its sandbox namespace (bwrap) cannot be created (bug
            # codex-adapter-cannot-run-in-nested-container).
            *(
                ["--dangerously-bypass-approvals-and-sandbox"]
                if self._config.bypass_sandbox
                else ["--sandbox", self._config.resolved_sandbox]
            ),
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
            # Substantive summary + findings survive into the flat structured map (bug
            # step-payload-drops-worker-findings): real workers emit findings with no
            # top-level summary, and the old generic default erased their content.
            structured = self._structured_from_payload(payload)
            findings = findings_json(payload)
            if findings is not None and "findings" not in structured:
                structured["findings"] = self._redact(findings)
            changed = changed_paths_csv(payload)
            if changed is not None and "changed_paths" not in structured:
                structured["changed_paths"] = self._redact(changed)
            missing_refs = missing_artifact_refs(refs, self._config.cwd)
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=self._redact(derive_result_summary(payload) or "codex exec completed"),
                artifact_refs=tuple(self._redact(path) for path in refs),
                structured_output=structured,
                domain_payload=self._redact_json(payload),  # type: ignore[arg-type]
                diagnostic=(
                    None
                    if refs and not missing_refs
                    else self._diagnostic(
                        request,
                        raw,
                        "referenced-artifact-missing"
                        if missing_refs
                        else "result-without-artifact-refs",
                    )
                ),
            )

        # SALVAGE (bug prose-worker-with-valid-handoff-loses-verdict): a prose message
        # that names an existing on-disk handoff yields a result grounded in that file.
        salvaged = salvage_result_from_handoff(raw, self._config.cwd)
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
                summary=self._redact(derive_result_summary(salvaged) or "codex exec completed"),
                artifact_refs=tuple(
                    self._redact(path) for path in normalize_artifact_refs(salvaged)
                ),
                structured_output=structured,
                domain_payload=self._redact_json(salvaged),  # type: ignore[arg-type]
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
                diagnostic=self._diagnostic(request, raw, "unparseable-output"),
            )
        if not isinstance(parsed, dict):
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="codex exec completed",
                structured_output={"value": self._redact(str(parsed))},
                diagnostic=self._diagnostic(request, raw, "non-object-output"),
            )
        # A parsed dict that is NOT this step's result object: keep a redacted summary if
        # present, but emit NO artifact_refs / verdict (reject-guard parity with pi).
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=self._redact(str(parsed.get("summary", "codex exec completed"))),
            diagnostic=self._diagnostic(request, raw, "no-artifact-refs"),
        )

    def _diagnostic(
        self, request: AgentRunRequest, output: str, classification: str
    ) -> WorkerDiagnostic:
        """Describe a successful subprocess response that violated the result contract."""
        model, effort = self._model_and_effort(request)
        tail = self._redact((output or "").strip())[-_MAX_DIAGNOSTIC_TAIL:]
        return WorkerDiagnostic(
            runtime=AgentRuntimeKind.CODEX_EXEC.value,
            model=model,
            requested_reasoning=effort,
            actual_reasoning=None,
            exit_code=0,
            parser_classification=classification,
            output_tail=tail,
        )

    def _structured_from_payload(self, payload: dict[str, object]) -> dict[str, str]:
        """Flatten a result payload into the redacted string map — PI-parity lifting.

        Bug codex-adapter-drops-top-level-verdict: like PI's ``_structured_from_verdict``,
        top-level ``verdict``/``verdict_reason``/``commit_sha``/``task_group`` are lifted
        (real review workers emit them top-level), then the nested ``structured_output``
        dict merges over them.
        """
        structured: dict[str, str] = {}
        for key in ("verdict", "verdict_reason", "commit_sha", "task_group"):
            value = payload.get(key)
            if value is not None:
                structured[key] = self._redact(str(value))
        extra = payload.get("structured_output")
        if isinstance(extra, dict):
            for key, value in extra.items():
                structured[str(key)] = self._redact(str(value))
        return structured
