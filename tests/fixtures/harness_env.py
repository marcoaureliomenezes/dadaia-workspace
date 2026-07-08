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
A Claude Code / Codex hook is spawned by the harness as a child process. The
harness passes through the operator's shell environment plus its own native variables.
Crucially it does **not** invent ``DADAIA_*`` variables: the only ``DADAIA_*`` value a
hook can rely on is whatever the *operator's shell* exported (``DADAIA_CONTEXT`` is the
documented operator-shell convenience var). In particular the harness never sets:

- ``DADAIA_SESSION_ID`` — the dadaia hooks resolve session identity from the harness's
  *native* id var (``CLAUDE_CODE_SESSION_ID`` / ``CODEX_SESSION_ID``) or the stdin
  ``session_id`` field
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
test (``tests/contract/test_harness_env_contract.py``) HARD-FAILS (no baseline) any test
that ``setenv``s a non-allowlisted ``DADAIA_*`` outside this module, or imports a hook
behavior module AND patches ``sys.stdin`` in-process to drive its ``main()`` instead of
using :func:`run_hook_subprocess`. Pure-helper unit tests (e.g. ``sdd_gate._resolve_mode``)
and fault-injection tests that monkeypatch a production internal without simulating
``sys.stdin`` are legitimately in-process and are not flagged.
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
    "ENTRY_SIGNAL_ENV_VARS",
    "HARNESS_CONTROL_DADAIA_ENV",
    "HOOK_MODULES",
    "HookResult",
    "claude_hook_env",
    "codex_hook_env",
    "run_hook_subprocess",
    "scrub_entry_signal_env",
]

#: The native session-id env var Claude Code provides to a hook subprocess.
CLAUDE_SESSION_ENV_VAR: Final[str] = "CLAUDE_CODE_SESSION_ID"

#: The native session-id env var Codex provides to a hook subprocess.
CODEX_SESSION_ENV_VAR: Final[str] = "CODEX_SESSION_ID"

#: The entry-harness auto-default signal vars (v0.1.64 FR3/AC-4). A developer running
#: pytest inside a codex TUI (or a PI session with the Ring-1 pin) legitimately carries
#: these in the shell; the test envelope must scrub them so a lifecycle verb invoked
#: without ``--harness`` in a test always resolves ``fake`` — never a real,
#: credit-spending worker. ``CLAUDE_CODE_SESSION_ID`` is included for symmetry (it is
#: never an entry signal, but scrubbing it keeps the envelope deterministic).
ENTRY_SIGNAL_ENV_VARS: Final[tuple[str, ...]] = (
    "DADAIA_ENTRY_HARNESS",
    CODEX_SESSION_ENV_VAR,
    CLAUDE_SESSION_ENV_VAR,
)


def scrub_entry_signal_env(monkeypatch: Any) -> None:
    """Delete the three entry-signal vars from ``os.environ`` for the current test.

    The autouse fixture in the root ``tests/conftest.py`` applies this over the whole
    suite (the AC-4 hermeticity envelope); tests that exercise the auto-default set the
    vars explicitly AFTER the scrub via their own ``monkeypatch.setenv``.
    """
    for name in ENTRY_SIGNAL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


#: ``DADAIA_*`` env vars a test MAY ``setenv`` in-process without tripping the env-contract
#: ratchet, because each is a documented **operator-shell input or operator override that
#: production code reads from the environment BY DESIGN**. Setting one in a unit test
#: exercises a real production env-read path — it is not harness-fiction. Every other
#: ``DADAIA_*`` setenv outside this module is a violation. Per-var justification (the
#: production reader is named so the allowlist stays auditable):
#:
#:   - ``DADAIA_CONTEXT`` — operator-shell context override; read by
#:     ``hooks/ctx_inject._resolve_context`` and ``hooks/sdd_gate`` context resolution.
#:   - ``DADAIA_AGENTS_DIR`` — agents-dir override (resolution branch 1); read by
#:     ``features/agents/reader`` (``os.environ.get("DADAIA_AGENTS_DIR")``).
#:   - ``DADAIA_WORKFLOWS_DIR`` — workflows-dir override (resolution branch 1); read by
#:     ``features/workflows/service`` (``os.environ.get("DADAIA_WORKFLOWS_DIR")``).
#:   - ``DADAIA_AGENT_RUNTIME`` — runtime selector; read by the lifecycle runtime
#:     wiring and the ``context`` CLI command.
#:   - ``DADAIA_SESSION_ID`` — the operator **override** leg of ``resolve_session_id``
#:     (``hooks/_common`` reads it first, ahead of the harness-native id vars). The harness
#:     never sets it (so it stays in :data:`_FORBIDDEN_HOOK_ENV`, scrubbed from a real hook
#:     *subprocess*), but a unit test of the override leg legitimately ``setenv``s it.
#:   - ``DADAIA_MODE`` — the operator-shell mode escape, order (1) of
#:     ``hooks/sdd_gate._resolve_mode``. Harness-never-set (scrubbed from subprocess env)
#:     but read from the environment by design when an operator exports it.
#:   - ``DADAIA_TESTING`` — the test-fixture flag the ``lease._before_write`` TOCTOU seam
#:     guard reads at import time (``features/spec_context/lease.py:112`` —
#:     ``os.environ.get("DADAIA_TESTING") == "1"``): the only sanctioned way to install the
#:     test-only ``_before_write`` interleave hook. Production code reads it by design (the
#:     assert is the named production reader), so a unit test ``setenv``-ing it exercises a
#:     real env-read path, not harness-fiction.
ALLOWLISTED_DADAIA_ENV: Final[frozenset[str]] = frozenset(
    {
        "DADAIA_CONTEXT",
        "DADAIA_AGENTS_DIR",
        "DADAIA_WORKFLOWS_DIR",
        "DADAIA_AGENT_RUNTIME",
        "DADAIA_SESSION_ID",
        "DADAIA_MODE",
        "DADAIA_TESTING",
        # Operator/test path-override knob read by production in
        # features/telemetry/service.py (PI session-store ingest, WS-PI-6) — same
        # category as DADAIA_AGENTS_DIR/DADAIA_WORKFLOWS_DIR above.
        "DADAIA_PI_SESSIONS_DIR",
        # Entry-harness pin (v0.1.64 FR3/FR4) — an operator-shell / PI-Ring-1 input read
        # by production BY DESIGN in core/session_env.entry_harness (the --harness auto
        # sentinel). Setting it in a test exercises that real env-read path; the autouse
        # AC-4 envelope scrub (scrub_entry_signal_env) keeps the suite hermetic.
        "DADAIA_ENTRY_HARNESS",
        # Codex sandbox override (v0.1.66 FR5) — an operator-shell input read by
        # production BY DESIGN in infrastructure/codex_runtime.CodexExecConfig.__post_init__
        # (os.environ.get(_DADAIA_CODEX_SANDBOX_ENV)), used to widen the codex sandbox mode
        # in constrained containers where the read-only default fails under bwrap.
        "DADAIA_CODEX_SANDBOX",
    }
)

#: ``DADAIA_*`` vars the **harness wiring itself** sets on the hook command line (not the
#: operator shell): the output contract that selects the codex-json / json envelope. The
#: Codex hook command in ``infrastructure/runtime_config`` exports these when it spawns
#: the hook; ``ctx_inject``
#: reads them in ``_emit``. They are NOT operator-shell vars and must never be planted via
#: an in-process ``setenv`` — a behavior test passes them through the *subprocess* env
#: (:func:`run_hook_subprocess`), which is the harness-real channel. :func:`claude_hook_env`
#: / :func:`codex_hook_env` accept them in ``extra`` for exactly that purpose.
HARNESS_CONTROL_DADAIA_ENV: Final[frozenset[str]] = frozenset(
    {"DADAIA_HOOK_OUTPUT", "DADAIA_HOOK_EVENT"}
)

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
    CLAUDE_SESSION_ENV_VAR,
    CODEX_SESSION_ENV_VAR,
)

#: The dadaia hook modules invocable as ``python -m dadaia_workspace.hooks.<name>``.
#: ``_common`` is intentionally absent — it is a shared-primitives library (pure helpers
#: like ``sanitize_session_id``), not a hook entrypoint, so unit-testing it directly is
#: legitimate. The behavior-import contract test uses this same list.
HOOK_MODULES: Final[frozenset[str]] = frozenset(
    {"sdd_gate", "sdd_post_gate", "ctx_inject", "root_whitelist", "pre_gate"}
)

#: Policy modules whose standalone ``main()`` CLI entrypoint was removed in v0.1.53 (the
#: merged ``pre_gate`` is the sole harness entrypoint). They are still driven in ISOLATION
#: for behavior tests via their pure ``evaluate_payload`` surface (see :func:`run_hook_subprocess`).
_POLICY_ONLY_MODULES: Final[frozenset[str]] = frozenset({"sdd_gate", "root_whitelist"})

#: Subprocess driver that reproduces the removed ``main()``: read the stdin JSON envelope,
#: run the named policy's ``evaluate_payload``, and emit the block envelope on a reason.
_POLICY_DRIVER: Final[str] = (
    "from dadaia_workspace.hooks import _common, {module} as _h\n"
    "p = _common.read_stdin_json()\n"
    "r = _h.evaluate_payload(p)\n"
    "if r is not None:\n"
    "    _common.emit_block(r)\n"
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
            if (
                key.startswith("DADAIA_")
                and key not in ALLOWLISTED_DADAIA_ENV
                and key not in HARNESS_CONTROL_DADAIA_ENV
            ):
                raise ValueError(
                    f"{key!r} is not a harness-provided var; do not inject it into a "
                    "hook env (see tests/fixtures/harness_env.py for the contract). "
                    "Operator-shell vars go in ALLOWLISTED_DADAIA_ENV; the hook output "
                    "contract vars go in HARNESS_CONTROL_DADAIA_ENV."
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
    if hook_module in _POLICY_ONLY_MODULES:
        # v0.1.53: the standalone ``sdd_gate`` / ``root_whitelist`` CLI ``main()`` entrypoints
        # were removed — ``pre_gate`` is the single merged harness entrypoint. To keep
        # exercising each policy IN ISOLATION (a merged ``pre_gate`` run would also apply the
        # other policies and change ALLOW outcomes), drive the policy's ``evaluate_payload``
        # in a real subprocess exactly as the removed ``main()`` did: read stdin JSON →
        # ``evaluate_payload`` → emit the block envelope on a reason.
        cmd = [sys.executable, "-c", _POLICY_DRIVER.format(module=hook_module)]
    else:
        cmd = [sys.executable, "-m", f"dadaia_workspace.hooks.{hook_module}"]
    proc = subprocess.run(
        cmd,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    return HookResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
