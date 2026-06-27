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

import json
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
