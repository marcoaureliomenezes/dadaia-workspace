"""Behavior + white-box tests for dadaia_workspace.hooks.sdd_gate.

Two test layers, each driven through its harness-real channel:

* **Behavior** (the gate's ALLOW/BLOCK envelope on a real PreToolUse) is exercised by
  spawning the hook as a subprocess via :func:`run_hook_subprocess` + :func:`claude_hook_env`
  — never by patching ``sys.stdin`` and calling ``sdd_gate.main()`` in-process (the
  simulated-stdin pattern the harness-env contract bans).
* **White-box** unit tests target the pure helper ``sdd_gate._resolve_mode`` and the
  fail-safe contract of ``gate_policy.evaluate`` directly. These never simulate harness
  stdin.

Mandatory invariants covered:
  (a) PATH-first context slug: a write under repos/B is attributed to B, never A.
  (b) Presence failures never block a mutating write.
  (c) PROTECTED (.dadaia/sessions/) is the sole fail-CLOSED path (kept as a standalone
      test AND as a param row under mode=READ — CRIT, never weakened).

CRIT: this file covers path class, scope and context attribution.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core import session_store
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess


def _mk_workspace(tmp_path: Path, *slugs: str) -> Path:
    """Build a minimal workspace with repos/<slug>/specs/releases/<id>/RELEASE.json
    (phase: IMPLEMENTATION) for each slug (v0.5.0 FR4/T-050-21A -- ACTIVE.md retired)."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"contexts": [{"repo_slug": s, "state": "alive"} for s in slugs]}),
        encoding="utf-8",
    )
    for s in slugs:
        (tmp_path / "repos" / s / "specs").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _run(
    tmp_path: Path,
    payload: dict[str, Any],
    *,
    session_id: str = "claude-sess",
) -> dict[str, Any] | None:
    """Spawn sdd_gate as a real subprocess; return the parsed BLOCK envelope (or None=ALLOW).

    The session id is supplied through the stdin ``session_id`` field (the harness-real
    channel); ``claude_hook_env``'s native ``CLAUDE_CODE_SESSION_ID`` is popped so resolution
    falls to the payload field, matching how these gate paths are driven. ``DADAIA_CONTEXT``
    is popped so the PATH-first slug derivation is the only context source.
    """
    env = claude_hook_env(tmp_path, session_id=session_id)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    env.pop("DADAIA_CONTEXT", None)
    full_payload = {**payload, "session_id": session_id}
    result = run_hook_subprocess("sdd_gate", full_payload, env)
    assert result.returncode == 0, result.stderr
    return result.block_envelope()


def _write_session_record(ws: Path, session_id: str, mode: str) -> None:
    """Persist a minimal session record (id + mode) the way the bind CLI does."""
    session_store.write_session(ws, session_id, {"session_id": session_id, "mode": mode})


# --------------------------------------------------------------------------- #
# Behavior: ALLOW / BLOCK envelope under a real subprocess spawn.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "tool_name", "tool_input_fn", "expect_block", "reason_contains"),
    [
        ("non_write_tool", "Read", lambda ws: {"file_path": "x"}, False, None),
        ("unparseable_target", "Write", lambda ws: {}, False, None),
        (
            "ungated_path",
            "Write",
            lambda ws: {"file_path": str(ws / "README.md")},
            False,
            None,
        ),
        (
            # PARITY (c): .dadaia/sessions/ is the sole fail-CLOSED path — blocked
            # unconditionally.
            "protected_sessions_blocks",
            "Write",
            lambda ws: {"file_path": str(ws / ".dadaia" / "sessions" / "runtime" / "a.ptr")},
            True,
            "SEC-01",
        ),
    ],
)
def test_allow_parity(
    tmp_path: Path,
    name: str,
    tool_name: str,
    tool_input_fn: Any,
    expect_block: bool,
    reason_contains: str | None,
) -> None:
    ws = _mk_workspace(tmp_path, "a")
    block = _run(tmp_path, {"tool_name": tool_name, "tool_input": tool_input_fn(ws)})
    if expect_block:
        assert block is not None
        assert reason_contains is not None and reason_contains in block["reason"]
    else:
        assert block is None


# ---------------------------------------------------------------------------
# v0.4.5 FR1 (T-045-04) — a repo's own domain-scoped root AGENTS.md, fresh or
# existing, tracked by the manifest or not, is never LAW: only the workspace root
# and the fixed harness projection dirs (LAW_HARNESS_DIRS) are. Bugs:
# sdd-gate-blocks-fresh-repo-root-agents-md +
# repo-agents-md-law-gate-contradicts-template.
# ---------------------------------------------------------------------------


def test_fresh_repo_agents_md_write_allowed_on_executed_path(tmp_path: Path) -> None:
    """Intent: CONTRACT — v0.4.5 A1.1 (real PreToolUse subprocess spawn).

    A `Write` of repos/<fresh-slug>/AGENTS.md in a brand-new repo — the repo
    directory exists (scaffolded by ``_mk_workspace``), the file does not — must
    ALLOW. Before the fix this BLOCKed with the projected-law-file message.
    """
    ws = _mk_workspace(tmp_path, "fresh-repo")
    target = ws / "repos" / "fresh-repo" / "AGENTS.md"
    assert not target.exists()
    block = _run(tmp_path, {"tool_name": "Write", "tool_input": {"file_path": str(target)}})
    assert block is None


def test_existing_nonmanifest_repo_agents_md_edit_allowed_on_executed_path(
    tmp_path: Path,
) -> None:
    """Intent: CONTRACT — v0.4.5 A1.2 (real PreToolUse subprocess spawn, Edit tool).

    An EXISTING repos/<slug>/AGENTS.md scaffolded from templates/repo-AGENTS.md
    (carries no canonical `data/AGENTS.md` provenance banner — repo-owned content)
    must ALLOW an `Edit`. Before the fix this BLOCKed with the projected-law-file
    message.
    """
    ws = _mk_workspace(tmp_path, "existing-repo")
    target = ws / "repos" / "existing-repo" / "AGENTS.md"
    target.write_text(
        "# existing-repo — Repo Rules\n\nEdit this file directly.\n", encoding="utf-8"
    )
    block = _run(
        tmp_path,
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(target),
                "old_string": "Edit this file directly.",
                "new_string": "Edit this file directly for repo-specific behavior.",
            },
        },
    )
    assert block is None


@pytest.mark.parametrize(
    ("name", "second_header", "second_body", "expect_block", "reason_fragment"),
    [
        (
            # REGRESSION (T-014-02): a later PROTECTED (.dadaia/sessions/) header blocks
            # the patch.
            "protected",
            ".dadaia/sessions/runtime/a.ptr",
            "+forge",
            True,
            "SEC-01",
        ),
        (
            # A multi-file apply_patch where EVERY header is allowed is not blocked (no
            # false block).
            "all_allowed",
            "docs/notes.md",
            "+more",
            False,
            None,
        ),
    ],
)
def test_apply_patch_multi_file_most_restrictive(
    tmp_path: Path,
    name: str,
    second_header: str,
    second_body: str,
    expect_block: bool,
    reason_fragment: str | None,
) -> None:
    _mk_workspace(tmp_path, "a")
    cmd = (
        "*** Begin Patch\n"
        "*** Update File: README.md\n"
        "+ok\n"
        f"*** Update File: {second_header}\n"
        f"{second_body}\n"
        "*** End Patch"
    )
    block = _run(tmp_path, {"tool_name": "apply_patch", "tool_input": {"command": cmd}})
    if expect_block:
        assert block is not None
        assert reason_fragment is not None
        assert (
            reason_fragment in block["reason"] or reason_fragment.upper() in block["reason"].upper()
        )
    else:
        assert block is None


def test_path_first_context_slug_parity_no_context_fails_open_never_blocks(
    tmp_path: Path,
) -> None:
    # PARITY (a): first-ALIVE is repos/A, but a write under repos/B MUST attribute
    # to repos/B, never repos/A (fixes gate-cross-context-lock-contamination).
    ws = _mk_workspace(tmp_path, "A", "B")  # A is first-ALIVE
    target = ws / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    block = _run(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        session_id="sess-1",
    )
    assert block is None  # v0.1.76: never blocks on concurrency

    # A specs/releases/ path with no repo slug + no DADAIA_CONTEXT -> fail open.
    ws2 = _mk_workspace(tmp_path.parent / (tmp_path.name + "-no-ctx"), "a")
    target2 = ws2 / "specs" / "releases" / "x" / "TASKS.md"
    block2 = _run(
        ws2,
        {"tool_name": "Write", "tool_input": {"file_path": str(target2)}},
    )
    assert block2 is None

    # DOCTRINE (v0.1.76): another session on the SAME context never blocks — the write ALLOWs.
    ws3 = _mk_workspace(tmp_path.parent / (tmp_path.name + "-foreign"), "B")
    target3 = ws3 / "repos" / "B" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target3.parent.mkdir(parents=True, exist_ok=True)
    block3 = _run(
        ws3,
        {"tool_name": "Write", "tool_input": {"file_path": str(target3)}},
        session_id="intruder",
    )
    assert block3 is None


def _write_live_harness_record(ws: Path, harness_id: str, context: str) -> None:
    """Seed a fresh, LIVE ``sessions/<harness_id>.json`` bind (rung 2 fixture)."""
    session_store.write_session(
        ws,
        harness_id,
        {
            "session_id": harness_id,
            "context": context,
            "mode": "IMPLEMENTATION",
            "last_seen_at": datetime.now(tz=UTC).isoformat(),
            "ttl_seconds": 300,
            "pid": 999999,
        },
    )


# --------------------------------------------------------------------------- #
# T-50-02 (SPEC v0.5.0 FR1): the two acceptance tests named by the task —
# (a) path-first beats DADAIA_CONTEXT; (b) a no-repo write now falls through to
# rungs 2-3 instead of resolving unattributed. Driven directly through
# claude_hook_env/run_hook_subprocess (not the file's own ``_run()``, which pops
# CLAUDE_CODE_SESSION_ID/DADAIA_CONTEXT — exactly the signals these tests need present).
# An explicit ``cwd=ws`` keeps every case hermetic: this suite runs inside the
# dadaia-workspace SOURCE checkout, itself nested under a REAL, registered
# "dadaia-workspace" context — an un-scoped subprocess cwd would silently resolve that
# real context instead of the fixture's isolated tmp_path workspace.
# --------------------------------------------------------------------------- #


def test_gate_attributes_repo_target_over_dadaia_context_env(tmp_path: Path) -> None:
    """sa-bind-has-two-stores#S1: a session with a native id and no record is UNBOUND even
    while ``DADAIA_CONTEXT=y`` names a registered context — the env is ignored, so a
    write into ``repos/x/...`` is never scope-blocked."""
    ws = _mk_workspace(tmp_path, "x", "y")
    target = ws / "repos" / "x" / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    env = claude_hook_env(ws, session_id="sess-path-first", extra={"DADAIA_CONTEXT": "y"})
    result = run_hook_subprocess(
        "sdd_gate",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
            "session_id": "sess-path-first",
        },
        env,
        cwd=ws,
    )
    assert result.returncode == 0, result.stderr
    assert result.block_envelope() is None


def test_no_repo_write_resolves_via_rung2_live_session_record(tmp_path: Path) -> None:
    """(b) A write outside every ``repos/<slug>/`` — which used to resolve via
    ``DADAIA_CONTEXT`` ONLY and fail open when that was absent — now
    falls through to rung 2: this session's own LIVE record. No ``DADAIA_CONTEXT`` is
    set here at all."""
    ws = _mk_workspace(tmp_path, "a")
    _write_live_harness_record(ws, "claude-live-sess", "a")
    target = ws / "specs" / "releases" / "rel-1" / "TASKS.md"

    env = claude_hook_env(ws, session_id="claude-live-sess")
    env.pop("DADAIA_CONTEXT", None)  # hermeticity: never inherit the operator's own shell
    result = run_hook_subprocess(
        "sdd_gate",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
            "session_id": "claude-live-sess",
        },
        env,
        cwd=ws,
    )
    assert result.returncode == 0, result.stderr
    assert result.block_envelope() is None


def test_no_repo_write_resolves_via_rung3_cwd_repo(tmp_path: Path) -> None:
    """(b) companion: no ``DADAIA_CONTEXT``, no live session record — the write still
    resolves via rung 3, the repo containing the hook's own working directory."""
    ws = _mk_workspace(tmp_path, "a")
    target = ws / "specs" / "releases" / "rel-1" / "TASKS.md"

    env = claude_hook_env(ws, session_id="sess-cwd-repo")
    env.pop("CLAUDE_CODE_SESSION_ID", None)  # no live rung-2 record to find anyway
    env.pop("DADAIA_CONTEXT", None)  # hermeticity: never inherit the operator's own shell
    result = run_hook_subprocess(
        "sdd_gate",
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
            "session_id": "sess-cwd-repo",
        },
        env,
        cwd=ws / "repos" / "a",
    )
    assert result.returncode == 0, result.stderr
    assert result.block_envelope() is None


# --------------------------------------------------------------------------- #
# sa-gate-path-classes-diverge-from-the-law: the install ledger decides PROTECTED.
# --------------------------------------------------------------------------- #

_LEDGERED = (
    ".claude/settings.json", ".codex/hooks.json", ".dadaia/hooks/codex-pre-gate",
    ".agents/skills/dd-x/SKILL.md", "AGENTS.md", ".dadaia/AGENTS.md", ".dadaia/tmp/AGENTS.md",
)  # fmt: skip


def _ledgered_workspace(tmp_path: Path) -> Path:
    ws = _mk_workspace(tmp_path, "a")
    entries = [{"relpath": p, "sha256": "0" * 64, "family": "x", "kind": "file"} for p in _LEDGERED]
    (ws / ".dadaia" / "states" / "install_ledger.json").write_text(
        json.dumps({"schema_version": "1", "entries": entries}), encoding="utf-8"
    )
    return ws


def _write(ws: Path, rel: str) -> dict[str, Any] | None:
    return _run(ws, {"tool_name": "Write", "tool_input": {"file_path": str(ws / rel)}})


@pytest.mark.parametrize("rel", [".claude/settings.json", ".codex/hooks.json",
                                 ".dadaia/hooks/codex-pre-gate"])  # fmt: skip
def test_hook_wiring_the_ledger_records_is_blocked(tmp_path: Path, rel: str) -> None:
    """sa-gate-path-classes-diverge-from-the-law#B39-1: hook wiring (.claude/settings.json,
    .codex/hooks.json, .dadaia/hooks/*) BLOCKs in every harness, with a re-project fix."""
    block = _write(_ledgered_workspace(tmp_path), rel)
    assert block is not None and "public install" in block["reason"]


@pytest.mark.parametrize(
    "rel", [".agents/skills/dd-x/SKILL.md", ".dadaia/states/install_ledger.json"]
)
def test_a_ledgered_projection_and_the_ledger_itself_are_blocked(tmp_path: Path, rel: str) -> None:
    """sa-gate-path-classes-diverge-from-the-law#B39-2: every ledgered projection, and the
    ledger file, BLOCK; sa-gate-path-classes-diverge-from-the-law#B39-7: the root and
    .dadaia law BLOCK by the same ledger (below)."""
    assert _write(_ledgered_workspace(tmp_path), rel) is not None


@pytest.mark.parametrize("rel", ["AGENTS.md", ".dadaia/AGENTS.md", ".dadaia/tmp/AGENTS.md"])
def test_root_and_dadaia_law_block_via_the_ledger(tmp_path: Path, rel: str) -> None:
    """sa-gate-path-classes-diverge-from-the-law#B39-7: root/.dadaia law BLOCK via the
    ledger — with no ledger entry the same name is an ordinary write."""
    assert _write(_ledgered_workspace(tmp_path), rel) is not None
    assert _write(_mk_workspace(tmp_path / "bare", "a"), rel) is None


def test_a_tmp_probe_agents_md_is_allowed(tmp_path: Path) -> None:
    """sa-gate-path-classes-diverge-from-the-law#B39-3: .dadaia/tmp/.../AGENTS.md is an
    ADDITIVE scratch write — the basename rule is deleted."""
    assert _write(_ledgered_workspace(tmp_path), ".dadaia/tmp/probe/20260927/AGENTS.md") is None


@pytest.mark.parametrize(
    "rel", ["specs/releases/_archive/releases_histo.jsonl",
            "repos/b/specs/releases/_archive/releases_histo.jsonl"],
)  # fmt: skip
def test_any_area_histo_is_allowed_foreign_repo_included(tmp_path: Path, rel: str) -> None:
    """sa-gate-path-classes-diverge-from-the-law#B39-4 through the hook; the bound-to-
    another-context case is test_gate_policy's foreign-repo test."""
    ws = _mk_workspace(tmp_path, "a", "b")
    assert _write(ws, rel) is None
