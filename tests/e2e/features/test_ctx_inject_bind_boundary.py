"""Seed-3 e2e: bind-driven context injection across the REAL process boundary.

This is the acceptance test for FR-W2 (ADR-G5, release v0.1.14). It exercises the
genuine ``dadaia context bind`` CLI → ``ctx_inject`` hook chain across **two distinct
real subprocesses with distinct session ids** — the boundary the unit/contract suites
cannot reach.

Why a real bind subprocess (not CliRunner)
------------------------------------------
The mechanism under test (FR-W2-02) exists *because* the bind CLI mints its own session
id that the harness never reports to a hook: ``read_session(harness_sid)`` is structurally
``None`` in the default flow, so the bind-epoch marker file is the only harness-real
discovery path. A test that ran bind in-process (CliRunner) and the hook in another process
would not cross that sid boundary the way production does. Here ``context bind`` runs as
``python -m dadaia_workspace.cli.main`` (its own process, its own minted sid) writing
``.dadaia/states/bind_epoch/<ctx>``, and the hook runs via the sanctioned
:func:`run_hook_subprocess` with a *different* sid delivered through the stdin
``session_id`` field — exactly as a real harness delivers it.

Seed-3 acceptance (SPEC §FR-W2):

  fresh unbound session → injection contains NO context memory (generic preflight +
  ALIVE list); after ``dadaia context bind X`` → next prompt injects X's memory; re-bind
  Y → Y injected; a repeat prompt for the same already-injected context is silent.

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

from tests.fixtures.harness_env import claude_hook_env, codex_hook_env, run_hook_subprocess


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


def _real_bind(workspace: Path, ctx: str) -> subprocess.CompletedProcess[str]:
    """Run ``dadaia context bind <ctx>`` as a genuine separate process (own minted sid).

    Invoked as ``python -m dadaia_workspace.cli.main`` with ``cwd=workspace`` so the CLI's
    ``resolve_workspace_root`` (cwd walk-up) finds the tmp workspace. This is the CLI-side
    epoch write, end-to-end, across the real process boundary.
    """
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
        capture_output=True,
        text=True,
        timeout=60.0,
    )
    return proc


def _inject(workspace: Path, session_id: str) -> str:
    """Run ctx_inject as a real subprocess; return stdout. Distinct sid via stdin field."""
    env = claude_hook_env(workspace, session_id="harness-native-ignored")
    # Force resolution from the stdin session_id field (the harness-real channel) and make
    # sure no developer-shell DADAIA_CONTEXT leaks context resolution into this run.
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    result = run_hook_subprocess("ctx_inject", {"session_id": session_id}, env)
    assert result.returncode == 0, result.stderr
    return result.stdout


def _inject_codex_json(workspace: Path, session_id: str) -> dict[str, object] | None:
    """Run ctx_inject through the Codex JSON envelope; return parsed stdout or None."""
    env = codex_hook_env(
        workspace,
        session_id="harness-native-ignored",
        extra={"DADAIA_HOOK_OUTPUT": "codex-json", "DADAIA_HOOK_EVENT": "UserPromptSubmit"},
    )
    env.pop("CODEX_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    result = run_hook_subprocess("ctx_inject", {"session_id": session_id}, env)
    assert result.returncode == 0, result.stderr
    if result.stdout.strip() == "":
        return None
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


def test_seed3_bind_drives_injection_across_real_process_boundary(tmp_path: Path) -> None:
    """Seed-3 acceptance: unbound → no memory; bind X → X; re-bind Y → Y; repeat → silent.

    A SINGLE hook session id (``s-e2e``) is used across the whole scenario so the sentinel
    persists between prompts — this is what makes the re-injection state machine observable
    end-to-end (a re-bind to a newer epoch must re-inject for the SAME live session).
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

    # 2) Real `dadaia context bind alpha` (own process, own minted sid) → next prompt for
    #    the live hook session injects ALPHA's memory (the epoch marker is newer than the
    #    sentinel stamped in step 1).
    bind_alpha = _real_bind(tmp_path, "alpha")
    assert bind_alpha.returncode == 0, bind_alpha.stderr or bind_alpha.stdout
    assert (tmp_path / ".dadaia" / "states" / "bind_epoch" / "alpha").is_file()

    after_alpha = _inject(tmp_path, sid)
    assert "[alpha]" in after_alpha
    assert "end memory bootstrap" in after_alpha
    assert "ALPHA-MARKER" in after_alpha
    assert "BETA-MARKER" not in after_alpha

    # 3) Re-bind to beta (distinct real bind process) → next prompt re-injects BETA.
    bind_beta = _real_bind(tmp_path, "beta")
    assert bind_beta.returncode == 0, bind_beta.stderr or bind_beta.stdout
    assert (tmp_path / ".dadaia" / "states" / "bind_epoch" / "beta").is_file()

    after_beta = _inject(tmp_path, sid)
    assert "[beta]" in after_beta
    assert "BETA-MARKER" in after_beta
    assert "ALPHA-MARKER" not in after_beta

    # 4) Repeat prompt with no newer bind → silent (already-injected slug, no qualifying epoch).
    repeat = _inject(tmp_path, sid)
    assert repeat.strip() == ""


def test_seed3_distinct_bind_sid_is_not_the_hook_sid(tmp_path: Path) -> None:
    """The bind CLI mints its OWN sid — the marker (not a session record) drives injection.

    Proves the mechanism's reason for being: after a real bind, the hook session id has NO
    session record of its own, yet injection still fires off the bind-epoch marker. This is
    the genuine cross-sid boundary FR-W2-02 was designed for.
    """
    from dadaia_workspace.features.spec_context import session_identity

    _add_context(tmp_path, "alpha", tech="# tech alpha\nPython 3.12 ALPHA-MARKER\n")

    sid = "s-no-record"
    # Stamp the sentinel first (fresh session) so the subsequent bind epoch qualifies.
    _inject(tmp_path, sid)

    proc = _real_bind(tmp_path, "alpha")
    assert proc.returncode == 0, proc.stderr or proc.stdout

    # The hook session id has no session record of its own — injection rides the marker.
    assert session_identity.read_session(tmp_path, sid) is None

    out = _inject(tmp_path, sid)
    assert "[alpha]" in out
    assert "ALPHA-MARKER" in out


def test_codex_json_bind_injection_is_transcript_bounded_and_repeat_silent(
    tmp_path: Path,
) -> None:
    """Codex additionalContext is human-visible, so it must not carry catalog JSON noise."""
    _add_context(
        tmp_path,
        "alpha",
        tech="# tech alpha\nPython 3.12 ALPHA-MARKER\n",
    )
    catalog = tmp_path / "repos" / "alpha" / "specs" / "memory" / "product" / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "features": [
                    {
                        "rank": 1,
                        "slug": "alpha-feature",
                        "title": "Alpha Feature",
                        "tldr": "short",
                        "path": "specs/memory/product/alpha.md",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    sid = "s-codex-visible"
    first = _inject_codex_json(tmp_path, sid)
    assert first is not None
    generic = first["hookSpecificOutput"]["additionalContext"]  # type: ignore[index]
    assert "[no bound context]" in generic
    assert "features" not in generic
    assert "rank" not in generic

    bind_alpha = _real_bind(tmp_path, "alpha")
    assert bind_alpha.returncode == 0, bind_alpha.stderr or bind_alpha.stdout

    bound = _inject_codex_json(tmp_path, sid)
    assert bound is not None
    payload = bound["hookSpecificOutput"]["additionalContext"]  # type: ignore[index]
    assert "[alpha]" in payload
    assert "dadaia context loaded" in payload
    assert "specs/memory/product/catalog.json" in payload
    assert "ALPHA-MARKER" not in payload
    assert "features" not in payload
    assert "rank" not in payload
    assert "dispatcher preflight" not in payload

    repeat = _inject_codex_json(tmp_path, sid)
    assert repeat is None
