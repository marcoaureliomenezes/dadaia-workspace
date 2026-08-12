"""Seed-3 e2e: bind-driven context injection across the REAL process boundary.

This is the acceptance test for FR-W2 (ADR-G5, release v0.1.14; bound_at trigger,
T-50-03, SPEC v0.5.0 FR1 coupling 1). It exercises the genuine ``dadaia context bind``
CLI → ``ctx_inject`` hook chain across **two distinct real subprocesses** — the boundary
the unit/contract suites cannot reach.

Why a real bind subprocess (not CliRunner)
------------------------------------------
The bind CLI and the hook are separate processes; a test that ran bind in-process
(CliRunner) and the hook in another process would not cross that process boundary the way
production does. Here ``context bind`` runs as ``python -m dadaia_workspace.cli.main`` (its
own process) and the hook runs via the sanctioned :func:`run_hook_subprocess` — exactly as
a real harness delivers both.

T-50-03: the SAME session id is exported as ``CLAUDE_CODE_SESSION_ID`` to BOTH the bind CLI
and the hook, modeling the real harness shape (the bind CLI, run through the harness's own
Bash tool, inherits the harness's native session-id env var; a real harness also delivers
that same id to a hook subprocess). This is what lets the bind's session record resolve
through the hook's own self-keyed leg (``_session_bound_context``) and drives the
``bound_at`` injection trigger (``_session_bound_at``). The bind-epoch marker subsystem —
the pre-T-50-03 cross-sid bridge for a bind with NO matching session-id env — is no longer
consulted by the injection path (the accepted FR1 coupling), and T-50-04 deletes the
subsystem outright.

Seed-3 acceptance (SPEC §FR-W2, T-50-03 additions):

  fresh unbound session → injection contains NO context memory (generic preflight +
  ALIVE list); after ``dadaia context bind X`` → next prompt injects X's memory; re-bind
  Y → Y injected; a repeat prompt for the same already-injected context is silent; a
  SAME-CONTEXT re-bind (new pin) re-injects; a repeat prompt after THAT is silent again.

NEVER builds a real venv: the workspace is a minimal hand-built tree (the
``.dadaia/states/spec_contexts.json`` sentinel + per-context ``specs/memory`` only), the
same shape the ctx_inject unit fixtures use. ``WorkspaceService.init`` is deliberately
avoided.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


def _add_context(workspace: Path, slug: str, *, tech: str) -> None:
    """Register an ALIVE context in the registry and build its minimal memory tree."""
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    registry = states / "spec_contexts.json"
    if registry.is_file():
        data = json.loads(registry.read_text(encoding="utf-8"))
    else:
        data = {"schema_version": "2", "contexts": []}
    data["contexts"].append(
        {
            "name": slug,
            "state": "alive",
            "repo_slug": slug,
            "repo_url": f"https://example.com/{slug}.git",
            "created_at": "2026-01-01T00:00:00Z",
            "alive_since": "2026-01-01T00:00:00Z",
            "dead_since": None,
            "current_branch": "main",
        }
    )
    registry.write_text(json.dumps(data), encoding="utf-8")

    mem = workspace / "repos" / slug / "specs" / "memory"
    (mem / "product").mkdir(parents=True, exist_ok=True)
    (mem / "tech-stack.md").write_text(tech, encoding="utf-8")
    (mem / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")


def _real_bind(
    workspace: Path, ctx: str, *, session_id: str | None
) -> subprocess.CompletedProcess[str]:
    """Run ``dadaia context bind <ctx>`` as a genuine separate process.

    T-50-03: *session_id*, when given, exports ``CLAUDE_CODE_SESSION_ID`` in the bind
    process's own env — modeling a REAL harness, where the bind CLI (run through the
    harness's own shell tool) and the hook are both children of the SAME harness process
    and inherit the SAME native session-id env var. This is what lets the bind's session
    record resolve through the hook's self-keyed leg (rung 2 of ``DADAIA.md`` §3 in
    spirit; the exact mechanism is ``_session_bound_context``, resolved via THIS hook's
    own ``session_id``). ``session_id=None`` inherits the ambient (pytest) env untouched —
    a bind with no matching harness env, minting its own sid.
    """
    env = claude_hook_env(workspace, session_id=session_id) if session_id else None
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "dadaia_workspace.cli.main",
            "context",
            "bind",
            ctx,
            "--mode",
            "read",
        ],
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
        timeout=60.0,
    )
    return proc


def _inject(workspace: Path, session_id: str) -> str:
    """Run ctx_inject as a real subprocess; return stdout.

    T-50-03: ``CLAUDE_CODE_SESSION_ID`` carries *session_id* (not popped) — matching how a
    real harness delivers BOTH the env var and the stdin payload field for the SAME live
    session, which is what lets this hook's own self-keyed leg
    (``_session_bound_context``) and its injection trigger (``_session_bound_at``) resolve
    the record a same-harness bind just wrote. ``DADAIA_CONTEXT`` stays popped so no
    developer-shell override leaks context resolution into this run.
    """
    env = claude_hook_env(workspace, session_id=session_id)
    env.pop("DADAIA_CONTEXT", None)
    result = run_hook_subprocess("ctx_inject", {"session_id": session_id}, env)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_seed3_bind_drives_injection_across_real_process_boundary(tmp_path: Path) -> None:
    """Seed-3 acceptance: unbound → no memory; bind alpha → alpha; re-bind beta → beta;
    repeat → silent; SAME-CONTEXT re-bind (new pin, T-50-03) → re-injects; repeat → silent
    again.

    A SINGLE hook session id (``s-e2e``) is used across the whole scenario, exported as
    the SAME ``CLAUDE_CODE_SESSION_ID`` to both the bind CLI and the hook — the real
    harness shape — so the sentinel persists between prompts and the bind's session
    record resolves through the hook's own self-keyed leg.
    """
    _add_context(tmp_path, "alpha", tech="# tech alpha\nPython 3.12 ALPHA-MARKER\n")
    _add_context(tmp_path, "beta", tech="# tech beta\nNode 20 BETA-MARKER\n")

    sid = "s-e2e"

    # 1) Fresh unbound session → generic preflight, NO context memory, ALIVE list present.
    first = _inject(tmp_path, sid)
    assert "[no bound context]" in first
    assert "dispatcher preflight" in first
    assert "end memory bootstrap" not in first
    assert "ALPHA-MARKER" not in first
    assert "BETA-MARKER" not in first
    assert "ALIVE contexts" in first
    assert "- alpha" in first
    assert "- beta" in first

    # 2) Real `dadaia context bind alpha`, SAME session id → next prompt for the live hook
    #    session injects ALPHA's memory (self-keyed session record, T-50-03).
    bind_alpha = _real_bind(tmp_path, "alpha", session_id=sid)
    assert bind_alpha.returncode == 0, bind_alpha.stderr or bind_alpha.stdout

    after_alpha = _inject(tmp_path, sid)
    assert "[alpha]" in after_alpha
    assert "end memory bootstrap" in after_alpha
    assert "ALPHA-MARKER" in after_alpha
    assert "BETA-MARKER" not in after_alpha

    # 3) Re-bind to beta (distinct real bind process, same session id) → next prompt
    #    re-injects BETA (the resolved context name changed).
    bind_beta = _real_bind(tmp_path, "beta", session_id=sid)
    assert bind_beta.returncode == 0, bind_beta.stderr or bind_beta.stdout

    after_beta = _inject(tmp_path, sid)
    assert "[beta]" in after_beta
    assert "BETA-MARKER" in after_beta
    assert "ALPHA-MARKER" not in after_beta

    # 4) Repeat prompt with no new bind → silent.
    repeat = _inject(tmp_path, sid)
    assert repeat.strip() == ""

    # 5) SAME-CONTEXT re-bind (new pin, T-50-03, SPEC v0.5.0 FR1 coupling 1): re-binding
    #    beta AGAIN refreshes bound_at and MUST re-inject even though the resolved name is
    #    unchanged — a re-bind is how a mode/release change reaches a live session.
    rebind_beta = _real_bind(tmp_path, "beta", session_id=sid)
    assert rebind_beta.returncode == 0, rebind_beta.stderr or rebind_beta.stdout

    after_rebind = _inject(tmp_path, sid)
    assert "[beta]" in after_rebind
    assert "end memory bootstrap" in after_rebind

    # 6) Repeat prompt again, no new bind → silent.
    assert _inject(tmp_path, sid).strip() == ""


def test_seed3_distinct_bind_sid_never_bridges_into_this_hook_session(tmp_path: Path) -> None:
    """T-50-04 (SPEC v0.5.0 FR1): the bind-epoch marker subsystem that used to bridge a
    bind performed under a DIFFERENT (unmatched) session id into this hook session's
    injection is deleted outright — there is no attribution mechanism left to bridge
    through. A bind with no matching harness env (its own minted sid) and no
    ``DADAIA_CONTEXT`` leaves the hook session's injection unbound, durably: the THIRD
    prompt proves this is not merely a one-shot omission.
    """
    from dadaia_workspace.features.spec_context import session_identity

    _add_context(tmp_path, "alpha", tech="# tech alpha\nPython 3.12 ALPHA-MARKER\n")

    sid = "s-no-record"
    # First prompt: unbound -> generic preflight, sentinel stamped.
    first = _inject(tmp_path, sid)
    assert "[no bound context]" in first

    proc = _real_bind(tmp_path, "alpha", session_id=None)
    assert proc.returncode == 0, proc.stderr or proc.stdout

    # The hook session id has no session record of its own, and DADAIA_CONTEXT is unset —
    # this session never resolves "alpha". The second prompt is therefore an ordinary
    # silent repeat (still unbound, no change for THIS session) — never "[ctx]"/"[alpha]"
    # and never re-emitted preflight.
    assert session_identity.read_session(tmp_path, sid) is None
    second = _inject(tmp_path, sid)
    assert second.strip() == ""
    assert "ALPHA-MARKER" not in second

    # A further prompt confirms this is durable, not a one-shot omission.
    third = _inject(tmp_path, sid)
    assert third.strip() == ""
    assert "ALPHA-MARKER" not in third
