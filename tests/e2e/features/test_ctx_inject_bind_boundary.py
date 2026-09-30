"""Intent: CONTRACT — v0.1.14 FR-W2 (T-50-03): the ONE real-process SENTINEL of bind ->
ctx_inject. `context bind` runs as its own process and the hook as another, both carrying
the same CLAUDE_CODE_SESSION_ID: unbound -> no memory; bind X -> X injected; re-bind Y ->
Y; a repeat prompt is silent; a same-context re-bind re-injects; the injection carries
constitution.md (AC1.2, ADR 0103). A bind under a distinct
session id never bridges (T-50-04): test_one_bind.py row native-id-no-record-unbound.
Hand-built workspace, never a real venv.
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
    (mem / "ARCHITECTURE.md").write_text(
        f"# Architecture\n\n## Tech Stack\n\n{tech}", encoding="utf-8"
    )
    (mem / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    (mem.parent / "constitution.md").write_text(f"# {slug} CONSTITUTION-MARKER\n", "utf-8")


def _real_bind(
    workspace: Path, ctx: str, *, session_id: str | None
) -> subprocess.CompletedProcess[str]:
    """Run ``dadaia context bind <ctx>`` as a genuine separate process.

    T-50-03: *session_id*, when given, exports ``CLAUDE_CODE_SESSION_ID`` in the bind
    process's own env — modeling a REAL harness, where the bind CLI (run through the
    harness's own shell tool) and the hook are both children of the SAME harness process
    and inherit the SAME native session-id env var. This is what lets the bind's session
    record resolve through the hook's self-keyed leg (rung 2 of the root `AGENTS.md` map §3 in
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

    # 1) Fresh unbound session → generic preflight: ALIVE list only, NO dispatcher
    #    preflight restatement (FR30/T-044-60 deleted it from every emission path) and NO
    #    context memory.
    first = _inject(tmp_path, sid)
    assert "[no bound context]" in first
    assert "dispatcher preflight" not in first
    assert "end memory bootstrap" not in first
    assert "ALPHA-MARKER" not in first
    assert "BETA-MARKER" not in first
    assert "ALIVE contexts" in first
    assert "- alpha" in first
    assert "- beta" in first

    # 2) Real `dadaia context bind alpha`, SAME session id → next prompt for the live hook
    #    session injects ALPHA's memory (self-keyed session record, T-50-03) — the memory
    #    prefix ONLY: no dispatcher preflight, no ALIVE-context list (FR30/T-044-60 — the
    #    list is useful only in the unbound case).
    bind_alpha = _real_bind(tmp_path, "alpha", session_id=sid)
    assert bind_alpha.returncode == 0, bind_alpha.stderr or bind_alpha.stdout

    after_alpha = _inject(tmp_path, sid)
    assert "[alpha]" in after_alpha
    assert "alpha CONSTITUTION-MARKER" in after_alpha  # AC1.2 (0103): every harness, one hook
    assert "end memory bootstrap" in after_alpha
    assert "ALPHA-MARKER" in after_alpha
    assert "BETA-MARKER" not in after_alpha
    assert "dispatcher preflight" not in after_alpha
    assert "ALIVE contexts" not in after_alpha

    # 3) Re-bind to beta (distinct real bind process, same session id) → next prompt
    #    re-injects BETA (the resolved context name changed) — same bound-boundary shape:
    #    memory prefix only.
    bind_beta = _real_bind(tmp_path, "beta", session_id=sid)
    assert bind_beta.returncode == 0, bind_beta.stderr or bind_beta.stdout

    after_beta = _inject(tmp_path, sid)
    assert "[beta]" in after_beta
    assert "BETA-MARKER" in after_beta
    assert "ALPHA-MARKER" not in after_beta
    assert "dispatcher preflight" not in after_beta
    assert "ALIVE contexts" not in after_beta

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
    assert "dispatcher preflight" not in after_rebind
    assert "ALIVE contexts" not in after_rebind

    # 6) Repeat prompt again, no new bind → silent.
    assert _inject(tmp_path, sid).strip() == ""
