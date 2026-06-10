"""Harness-env fixture contract — the *only* sanctioned source of hook subprocess env.

WS-R5 / FR-R5-01 / AC-R5-01 (release v0.1.10). The 2026-06-10 test-architecture audit
(``specs/audits/2026-06-10T010550Z/qa-engineer.md`` §2, §6.1) named the single most
expensive blind spot in this suite: **a simulated harness environment**. Hook and
heartbeat tests ``setenv`` ``DADAIA_SESSION_ID`` / persona / mode variables that *no real
harness ever delivers to a hook subprocess*, so the suite certified mechanisms that are
physically dead in every runtime (bugs 2, 5, 17-D3, 28). This module is the corrective:
it pins, in one place, exactly what each harness actually provides to a hook process, and
exposes a subprocess runner so behavior tests invoke hooks the way the harness does.

Why these env vars and *only* these
-----------------------------------
A Claude Code / Codex / OpenCode hook is spawned by the harness as a child process. The
harness passes through the operator's shell environment plus its own native variables.
Crucially it does **not** invent ``DADAIA_*`` variables: the only ``DADAIA_*`` value a
hook can rely on is whatever the *operator's shell* exported (``DADAIA_CONTEXT`` is the
documented operator-shell convenience var). In particular the harness never sets:

- ``DADAIA_SESSION_ID`` — the dadaia hooks resolve session identity from the harness's
  *native* id var (``CLAUDE_CODE_SESSION_ID`` / ``CODEX_SESSION_ID`` /
  ``OPENCODE_SESSION_ID``) or the stdin ``session_id`` field
  (``dadaia_workspace/hooks/_common.py:resolve_session_id``). ``DADAIA_SESSION_ID`` is an
  *operator override only*, never a harness-supplied value.
- ``DADAIA_PERSONA`` / ``*_AGENT_PERSONA`` — no harness exposes the dispatched persona to
  a hook subprocess (this is why the rc-3 persona write-allowlist was a "lock with no
  key" and was removed). Tests must never plant it.
- ``DADAIA_MODE`` — bind mode is read from the on-disk session record, not a hook env var
  (WS-R4). A hook env never carries it from the harness.

Verification source: ``dadaia_workspace/hooks/{sdd_gate,sdd_post_gate,ctx_inject}.py`` +
``hooks/_common.resolve_session_id`` (which env vars the hooks actually read), and the
existing real-harness subprocess test ``tests/integration/gate/test_path_scope.py`` (which
already strips ``DADAIA_SESSION_ID`` / ``*_AGENT_PERSONA`` before invoking the gate). The
env returned here is **pinned-minimal**: a clean base (operator shell *without* any leaked
``DADAIA_*``/persona/mode vars) plus ``WORKSPACE_ROOT`` and the one native session-id var
the named harness provides.

Usage
-----
::

    from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

    env = claude_hook_env(workspace, session_id="sess-1")
    result = run_hook_subprocess("sdd_gate", payload, env)
    assert result.returncode == 0

The behavior of every hook/gate/lease test must flow through these helpers: a contract
test (``tests/contract/test_harness_env_contract.py``) fails any test that ``setenv``s a
non-allowlisted ``DADAIA_*`` outside this module, or imports+calls a hook module directly
in ``tests/**/hooks|gate/**`` instead of using :func:`run_hook_subprocess`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

__all__ = [
    "ALLOWLISTED_DADAIA_ENV",
    "CLAUDE_SESSION_ENV_VAR",
    "CODEX_SESSION_ENV_VAR",
    "HOOK_MODULES",
    "HookResult",
    "claude_hook_env",
    "codex_hook_env",
    "run_hook_subprocess",
]

#: The native session-id env var Claude Code provides to a hook subprocess.
CLAUDE_SESSION_ENV_VAR: Final[str] = "CLAUDE_CODE_SESSION_ID"

#: The native session-id env var Codex provides to a hook subprocess.
CODEX_SESSION_ENV_VAR: Final[str] = "CODEX_SESSION_ID"

#: ``DADAIA_*`` env vars that MAY legitimately reach a hook subprocess because the
#: *operator's shell* (not the harness) exports them. The env-contract test allows these
#: to be set by tests; every other ``DADAIA_*`` setenv outside this module is a violation.
#: ``DADAIA_CONTEXT`` is the documented operator-shell context override
#: (``hooks/ctx_inject._resolve_context``, ``hooks/sdd_gate._context_slug``).
ALLOWLISTED_DADAIA_ENV: Final[frozenset[str]] = frozenset({"DADAIA_CONTEXT"})

#: ``DADAIA_*`` / persona / mode vars that the harness NEVER provides to a hook and that
#: therefore must be scrubbed from any inherited environment before a hook runs. Tests
#: must never re-plant these (the contract test enforces it for the ``DADAIA_*`` half).
_FORBIDDEN_HOOK_ENV: Final[tuple[str, ...]] = (
    "DADAIA_SESSION_ID",
    "DADAIA_PERSONA",
    "DADAIA_MODE",
    "DADAIA_AGENT_PERSONA",
    "CLAUDE_AGENT_PERSONA",
    "CODEX_AGENT_PERSONA",
    "OPENCODE_AGENT_PERSONA",
    CLAUDE_SESSION_ENV_VAR,
    CODEX_SESSION_ENV_VAR,
    "OPENCODE_SESSION_ID",
)

#: The dadaia hook modules invocable as ``python -m dadaia_workspace.hooks.<name>``.
#: ``_common`` is intentionally absent — it is a shared-primitives library (pure helpers
#: like ``sanitize_session_id``), not a hook entrypoint, so unit-testing it directly is
#: legitimate. The behavior-import contract test uses this same list.
HOOK_MODULES: Final[frozenset[str]] = frozenset(
    {"sdd_gate", "sdd_post_gate", "ctx_inject", "root_whitelist"}
)


def _base_env() -> dict[str, str]:
    """A copy of the operator shell env with every harness-never-set var scrubbed.

    This models the real spawn: the operator shell is inherited, but the variables the
    harness does not actually deliver (and that a stray prior test might have leaked into
    ``os.environ``) are removed so a hook can never accidentally observe them.
    """
    env = dict(os.environ)
    for key in _FORBIDDEN_HOOK_ENV:
        env.pop(key, None)
    return env


def _harness_env(
    workspace: Path,
    *,
    session_env_var: str,
    session_id: str,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    env = _base_env()
    env["WORKSPACE_ROOT"] = str(workspace)
    env[session_env_var] = session_id
    if extra:
        for key, value in extra.items():
            if key.startswith("DADAIA_") and key not in ALLOWLISTED_DADAIA_ENV:
                raise ValueError(
                    f"{key!r} is not a harness-provided var; do not inject it into a "
                    "hook env (see tests/fixtures/harness_env.py for the contract)."
                )
            env[key] = value
    return env


def claude_hook_env(
    workspace: Path,
    *,
    session_id: str = "claude-sess-1",
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Pinned-minimal env a real Claude Code hook subprocess receives.

    Contains the operator shell (scrubbed of harness-never-set vars), ``WORKSPACE_ROOT``,
    and ``CLAUDE_CODE_SESSION_ID``. ``extra`` may add operator-shell vars (e.g.
    ``DADAIA_CONTEXT``); a non-allowlisted ``DADAIA_*`` in ``extra`` raises ``ValueError``.
    """
    return _harness_env(
        workspace,
        session_env_var=CLAUDE_SESSION_ENV_VAR,
        session_id=session_id,
        extra=extra,
    )


def codex_hook_env(
    workspace: Path,
    *,
    session_id: str = "codex-sess-1",
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Pinned-minimal env a real Codex hook subprocess receives.

    Contains the operator shell (scrubbed of harness-never-set vars), ``WORKSPACE_ROOT``,
    and ``CODEX_SESSION_ID``. ``extra`` may add operator-shell vars (e.g.
    ``DADAIA_CONTEXT``); a non-allowlisted ``DADAIA_*`` in ``extra`` raises ``ValueError``.
    """
    return _harness_env(
        workspace,
        session_env_var=CODEX_SESSION_ENV_VAR,
        session_id=session_id,
        extra=extra,
    )


@dataclass(frozen=True)
class HookResult:
    """Outcome of a hook subprocess invocation."""

    returncode: int
    stdout: str
    stderr: str

    def block_envelope(self) -> dict[str, Any] | None:
        """Parse the ``{"decision":"block",...}`` envelope from stdout, else ``None``.

        A gate ALLOW emits no envelope (empty/whitespace stdout); a BLOCK emits the JSON
        block object. ``ctx_inject`` raw output that is not a block dict also yields
        ``None``.
        """
        raw = self.stdout.strip()
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
        if isinstance(data, dict) and data.get("decision") == "block":
            return data
        return None


def run_hook_subprocess(
    hook_module: str,
    payload: dict[str, Any],
    env: dict[str, str],
    *,
    timeout: float = 30.0,
) -> HookResult:
    """Invoke a dadaia hook as a real subprocess, the way the harness does.

    Runs ``python -m dadaia_workspace.hooks.<hook_module>`` with ``payload`` serialized to
    stdin as the hook JSON envelope and ``env`` as the *complete* process environment
    (use :func:`claude_hook_env` / :func:`codex_hook_env` to build it). Captures exit code,
    stdout, and stderr.

    This is the single sanctioned channel for hook *behavior* tests in
    ``tests/**/hooks|gate/**``; importing a hook module and calling ``main()`` in-process
    re-creates the simulated-env blind spot this fixture exists to kill.
    """
    if hook_module not in HOOK_MODULES:
        raise ValueError(
            f"{hook_module!r} is not a known hook entrypoint; expected one of "
            f"{sorted(HOOK_MODULES)}."
        )
    proc = subprocess.run(
        [sys.executable, "-m", f"dadaia_workspace.hooks.{hook_module}"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    return HookResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
