"""Unit tests for ``core/session_env`` — entry-harness resolution (v0.1.64 FR3, AC-3).

``entry_harness()`` is the single seam the lifecycle CLI's ``--harness auto`` sentinel
resolves through. Precedence (SPEC §9 ADR-3):

1. ``DADAIA_ENTRY_HARNESS`` when it holds ``codex``/``pi`` (operator / PI-seam pin);
2. ``CODEX_SESSION_ID`` present ⇒ ``"codex"``;
3. otherwise ``None`` (Claude entry — Layer-1-only, never a workflow harness — and
   plain shells/CI).

Also carries the AC-4 CI half (QA64-1): a CI-scoped assert — active only when
``GITHUB_ACTIONS`` is set — that the GHA quality jobs' RAW env carries none of the three
entry-signal vars, so no CI shell step can auto-default a real worker outside pytest
either. The raw-env snapshot is taken at module import (collection time), BEFORE any
autouse scrub fixture runs, so the assert observes the genuine job environment.
"""

from __future__ import annotations

import os

import pytest

from dadaia_workspace.core.session_env import entry_harness, harness_session_id
from tests.fixtures.harness_env import ENTRY_SIGNAL_ENV_VARS, scrub_entry_signal_env

# AC-4 CI half: raw env captured at import/collection time — before the per-test autouse
# scrub (which would make an in-test read vacuous).
_RAW_ENV_AT_COLLECTION: dict[str, str] = dict(os.environ)


@pytest.mark.parametrize(
    ("name", "env", "expected"),
    [
        ("no_signal_resolves_none", {}, None),
        ("pin_codex_wins", {"DADAIA_ENTRY_HARNESS": "codex"}, "codex"),
        ("pin_pi_wins", {"DADAIA_ENTRY_HARNESS": "pi"}, "pi"),
        ("pin_uppercase_normalized", {"DADAIA_ENTRY_HARNESS": "CODEX"}, "codex"),
        ("pin_mixed_case_normalized", {"DADAIA_ENTRY_HARNESS": "Pi"}, "pi"),
        ("pin_whitespace_stripped", {"DADAIA_ENTRY_HARNESS": "  pi  "}, "pi"),
        (
            # AC-3: DADAIA_ENTRY_HARNESS=pi beats a stale CODEX_SESSION_ID (AC-9
            # sabotage (c) — making the resolver ignore the pin — fails exactly here).
            "pin_beats_stale_codex_session_id",
            {"CODEX_SESSION_ID": "stale-codex-sess", "DADAIA_ENTRY_HARNESS": "pi"},
            "pi",
        ),
        ("codex_session_id_resolves_codex", {"CODEX_SESSION_ID": "codex-sess-1"}, "codex"),
        (
            # Claude Code is Layer-1-only (LAW 1): its native session id is NEVER an
            # entry signal, and "claude" is never returned.
            "claude_session_only_resolves_none",
            {"CLAUDE_CODE_SESSION_ID": "claude-sess-1"},
            None,
        ),
        # A garbage/unsupported DADAIA_ENTRY_HARNESS value is ignored — resolution
        # falls through to None (no CODEX_SESSION_ID present), never raises, never
        # returns the garbage token.
        ("garbage_claude", {"DADAIA_ENTRY_HARNESS": "claude"}, None),
        ("garbage_fake", {"DADAIA_ENTRY_HARNESS": "fake"}, None),
        ("garbage_auto", {"DADAIA_ENTRY_HARNESS": "auto"}, None),
        ("garbage_opencode", {"DADAIA_ENTRY_HARNESS": "opencode"}, None),
        ("garbage_digit", {"DADAIA_ENTRY_HARNESS": "1"}, None),
        ("garbage_space", {"DADAIA_ENTRY_HARNESS": " "}, None),
        ("garbage_empty", {"DADAIA_ENTRY_HARNESS": ""}, None),
    ],
)
def test_entry_harness_precedence_table(
    monkeypatch: pytest.MonkeyPatch, name: str, env: dict[str, str], expected: str | None
) -> None:
    for var in ("DADAIA_ENTRY_HARNESS", "CODEX_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert entry_harness() == expected


def test_garbage_pin_falls_through_to_codex_session_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DADAIA_ENTRY_HARNESS", "opencode")
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-sess-1")
    assert entry_harness() == "codex"


def test_envelope_scrub_neutralizes_developer_codex_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # AC-4 pytest half: a developer running pytest inside a codex TUI carries
    # CODEX_SESSION_ID; the shared envelope scrub must neutralize it so a defaulted
    # harness resolves fake (None here), never a real worker.
    monkeypatch.setenv("CODEX_SESSION_ID", "developer-codex-tui-sess")
    scrub_entry_signal_env(monkeypatch)
    assert entry_harness() is None


def test_codex_thread_id_resolves_session_and_entry_harness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # T-69-01 (FR1/FR1.2, bug codex-thread-id-bind-resolution-breaks-cli): a modern
    # Codex tool subprocess exposes CODEX_THREAD_ID instead of CODEX_SESSION_ID.
    # harness_session_id() must resolve it, and entry_harness() must recognize the
    # session as "codex" even without CODEX_SESSION_ID.
    monkeypatch.delenv("DADAIA_ENTRY_HARNESS", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-abc123")
    assert harness_session_id() == "thread-abc123"
    assert entry_harness() == "codex"

    # AC1.2: when both CODEX_SESSION_ID and CODEX_THREAD_ID are present,
    # harness_session_id() must prefer CODEX_SESSION_ID (CODEX_THREAD_ID is ordered
    # AFTER CODEX_SESSION_ID).
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-sess-1")
    assert harness_session_id() == "codex-sess-1"


@pytest.mark.skipif(
    not os.environ.get("GITHUB_ACTIONS"),
    reason="CI-only env-hygiene assert (QA64-1); a developer inside a codex TUI "
    "legitimately carries CODEX_SESSION_ID locally.",
)
def test_ci_job_env_carries_no_entry_signal_vars() -> None:
    # AC-4 CI half (QA64-1): the GHA quality jobs' raw environment must carry NONE of
    # the three entry-signal vars — no CI shell step can auto-default a real worker.
    present = [name for name in ENTRY_SIGNAL_ENV_VARS if _RAW_ENV_AT_COLLECTION.get(name)]
    assert not present, (
        f"CI job env carries entry-signal vars {present}; a CI shell step running a "
        "lifecycle verb without --harness would auto-default a real worker (FR3/AC-4)."
    )
