"""Shared base for the headless Layer-2 runtime adapters.

This module is the single home for the security-relevant invariants that were
copy-pasted across the three real ``AgentRuntimePort`` adapters
(``pi_runtime``, ``codex_runtime``, ``claude_sdk_runtime``). A divergence
between those copies is a latent **security** bug, not style debt, so the logic
lives here once and the adapters import it.

The pieces are deliberately factored along two reuse boundaries:

* :class:`RedactionMixin` (with :data:`_SECRET_NAME_PARTS`) and the git seam
  (:class:`_GitDiffPort` + :class:`ChangedPathsMixin`) are **transport-neutral**.
  The non-CLI Claude SDK adapter reuses these and only these — it has no
  subprocess machinery.
* :class:`SubprocessAdapterMixin` (with the :data:`Runner` seam type, the
  env-allowlist filter, and the :func:`build_prompt_envelope` builder) is the
  subprocess-specific surface reused only by the CLI adapters (``pi``/``codex``).

This is a **pure de-duplication**: every method body is byte-for-byte the logic
that previously lived in the adapters. ``test_headless_adapter_base.py`` pins
single-source behaviour with a divergence test, and the per-adapter unit suites
stay green unchanged.
"""

from __future__ import annotations

import enum
import json
import re
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.models.lifecycle import AgentRunRequest, AgentRunResult

#: The subprocess-runner seam type shared by the CLI adapters. Injecting this is
#: what lets the unit suites run fully faked (no real ``pi``/``codex`` process).
Runner = Callable[..., subprocess.CompletedProcess[str]]

#: Env-var name fragments whose values must never appear in surfaced output
#: (CWE-209). The single source of truth for every adapter's secret scrub.
_SECRET_NAME_PARTS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")

#: Fenced ```json block matcher reused by both CLI adapters' result extraction.
_FENCED_JSON = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


class ResultMatch(enum.Enum):
    """Which acceptance path classified a parsed dict as the step's result object.

    The enum makes strict-vs-structural acceptance an observable BEHAVIOUR (v0.1.32
    Cluster 2 / C5): a behaviour test can assert that a both-valid payload matches
    :data:`STRICT` and a schema-mismatched-but-structurally-valid payload matches only
    :data:`STRUCTURAL` — so a future reorder that lets the structural check shadow the
    strict one fails the test rather than passing silently.
    """

    STRICT = "strict"
    STRUCTURAL = "structural"
    NONE = "none"


def json_candidates(text: str) -> list[str]:
    """Ordered JSON-string candidates from an assistant message, most-precise first.

    1. each fenced ```json block (the documented contract);
    2. the whole stripped message (a bare JSON object — the common real-worker shape);
    3. the outermost ``{...}`` slice (a JSON object trailing some prose).

    Shared by ``pi_runtime`` and ``codex_runtime`` (v0.1.32 A12) — both real Layer-2
    workers emit either a fenced or a bare object, so the candidate scan is single-sourced.
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


def classify_result_payload(payload: dict[str, object], expected_schema: str) -> ResultMatch:
    """Classify a parsed dict against the coherent worker-output contract (v0.1.32 L4).

    Strict primacy, structural defence-in-depth:

    1. **STRICT (primary)** — the worker labelled the transport ``schema`` field with the
       requested ``expected_schema`` id. This is the documented happy path now that the
       prompt contract is coherent (one field ``schema``, one value the transport id).
       It is checked FIRST so a both-valid payload always classifies as strict.
    2. **STRUCTURAL (documented fallback)** — a real GPT/Codex worker reliably emits the
       result *object* but labels the ``schema`` field inconsistently across runs (omits
       it, or names the fragment's domain schema instead of the transport id — both
       observed live). Rather than BLOCK a correct result on a label mismatch, accept a
       payload that *structurally is* the result: a non-empty ``artifact_refs`` list plus a
       ``status`` / ``summary`` / nested ``structured_output``. This is defence-in-depth,
       NOT the primary contract.
    3. **NONE** — arbitrary JSON lacking the result shape (no schema match AND no non-empty
       ``artifact_refs``) is rejected; a no-op worker (no payload) yields no result → BLOCK.
    """
    if payload.get("schema") == expected_schema:
        return ResultMatch.STRICT
    refs = payload.get("artifact_refs")
    if (
        isinstance(refs, list)
        and refs
        and any(key in payload for key in ("status", "summary", "structured_output"))
    ):
        return ResultMatch.STRUCTURAL
    return ResultMatch.NONE


def is_result_payload(payload: dict[str, object], expected_schema: str) -> bool:
    """Whether a parsed dict IS this step's structured result object (strict OR structural).

    Thin wrapper over :func:`classify_result_payload` — ``True`` for STRICT/STRUCTURAL,
    ``False`` for NONE. The classifier is the single source of the acceptance ordering.
    """
    return classify_result_payload(payload, expected_schema) is not ResultMatch.NONE


def extract_result_payload(text: str, expected_schema: str | None) -> dict[str, object] | None:
    """Parse the step's structured result object from an assistant message — single-sourced.

    The result object is the in-band channel the Python gate reads (a review step's
    ``verdict``; every step's ``artifact_refs`` / schema evidence). Candidates are scanned
    fenced-first, then the whole stripped message, then the outermost ``{...}`` slice (see
    :func:`json_candidates`). A candidate is accepted iff :func:`is_result_payload` holds:
    strict ``schema == expected_schema`` is the PRIMARY contract; a structurally-valid
    payload is accepted as documented defence-in-depth. A no-op worker (no usable payload)
    yields ``None`` → empty ``artifact_refs`` → the create-step gate BLOCKs (the extractor
    is never made permissive). Returns ``None`` when ``expected_schema`` is ``None`` or no
    candidate is accepted.

    Both ``pi_runtime`` and ``codex_runtime`` call THIS function (v0.1.32 A12/L5), proven
    by a patch-the-helper test — copy-paste divergence cannot silently reappear.
    """
    if expected_schema is None:
        return None
    for candidate in json_candidates(text):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if is_result_payload(payload, expected_schema):
            return payload
    return None


class _GitDiffPort(Protocol):
    """Narrow git seam the adapters need — satisfied by ``GitSubprocessClient``."""

    def diff_name_only(self, path: Path) -> tuple[str, ...]: ...


class RedactionMixin:
    """Secret-scrub surfaced output using the host environment.

    Reused by every real adapter — including the non-subprocess Claude SDK
    adapter — so the redaction discipline is single-sourced. Hosts must expose a
    ``self._environ`` mapping (the allowlist/full environment the adapter holds).
    """

    _environ: Mapping[str, str]

    def _redact(self, text: str) -> str:
        """Replace any secret-named env value occurrence with ``[REDACTED]``."""
        redacted = text
        for key, value in self._environ.items():
            if not value:
                continue
            if any(part in key.upper() for part in _SECRET_NAME_PARTS):
                redacted = redacted.replace(value, "[REDACTED]")
        return redacted


class ChangedPathsMixin:
    """Source ``changed_paths`` from ``git diff`` — the Ring-2 write boundary.

    When an injected ``git`` client is present, the real diff UNCONDITIONALLY
    overwrites any ``changed_paths`` a lying worker may have self-reported; when
    ``git`` is ``None`` the result is returned untouched (prior behaviour). Hosts
    must expose ``self._git`` (``_GitDiffPort | None``) and a ``self._cwd_for_diff``
    ``Path`` (the working tree to diff).
    """

    _git: _GitDiffPort | None
    _cwd_for_diff: Path

    def _with_changed_paths(self, result: AgentRunResult) -> AgentRunResult:
        if self._git is None:
            return result
        changed = self._git.diff_name_only(self._cwd_for_diff)
        structured = dict(result.structured_output)
        structured["changed_paths"] = ",".join(changed)
        return AgentRunResult(
            status=result.status,
            summary=result.summary,
            artifact_refs=result.artifact_refs,
            structured_output=structured,
            error=result.error,
        )


def build_prompt_envelope(request: AgentRunRequest) -> str:
    """Build the deterministic JSON prompt envelope handed to a headless worker.

    Fields: ``role``, ``prompt``, ``context``, ``release_id``, ``task_id``,
    ``allowed_paths``, ``forbidden_paths``, ``expected_schema``,
    ``required_evidence``. Emitted with ``indent=2, sort_keys=True`` so the
    on-the-wire payload is byte-stable (the prior per-adapter behaviour).
    """
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


def filter_env(environ: Mapping[str, str], allowlist: tuple[str, ...]) -> dict[str, str]:
    """Project ``environ`` down to the keys in ``allowlist`` that are present.

    The single source of the env-allowlist filtering each CLI adapter applies
    before spawning its subprocess. The *contents* of the allowlist stay
    per-adapter (PI allows ``ANTHROPIC_API_KEY``; Codex allows ``CODEX_HOME``);
    only the filtering algorithm is shared.
    """
    return {key: environ[key] for key in allowlist if key in environ}


class SubprocessAdapterMixin(RedactionMixin, ChangedPathsMixin):
    """Common subprocess surface for the CLI headless adapters (``pi``/``codex``).

    Bundles redaction (CWE-209) and the git ``changed_paths`` override (Ring-2)
    with the subprocess-specific env filter and prompt envelope. Hosts expose
    ``self._environ`` (full host environment), ``self._git`` / ``self._cwd_for_diff``
    (git seam), and a config carrying ``env_allowlist``.
    """

    _environ: Mapping[str, str]
    _env_allowlist: tuple[str, ...]

    def _env(self) -> dict[str, str]:
        return filter_env(self._environ, self._env_allowlist)

    @staticmethod
    def _prompt(request: AgentRunRequest) -> str:
        return build_prompt_envelope(request)

    def _extract_result_payload(
        self,
        text: str,
        expected_schema: str | None,
    ) -> dict[str, object] | None:
        """Single shared entry point for result extraction (v0.1.32 A12 / L5).

        Both CLI adapters resolve result extraction through THIS method, which delegates to
        the module-level :func:`extract_result_payload`. Because both adapters share this
        one body, a patch of :func:`extract_result_payload` is observed by both — the
        positive proof (C3) that ``pi_runtime`` and ``codex_runtime`` cannot diverge.
        """
        return extract_result_payload(text, expected_schema)
