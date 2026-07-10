"""Unit tests for the lifecycle CLI harness map and resolution.

`_HARNESS_KINDS` + `_resolve_harness` are the single seam that turns a
`--harness <name>` / `--step-harness <label>=<name>` token into an
`AgentRuntimeKind`. Adding a harness must require only a map entry — no change to
`phase_workflow.py` / `pipeline.py`.
"""

from __future__ import annotations

import pytest
import typer

from dadaia_workspace.cli.commands.lifecycle import (
    _HARNESS_KINDS,
    _resolve_default_harness,
    _resolve_harness,
)
from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind


def test_harness_map_covers_exactly_l2_selectable_kinds_including_pi() -> None:
    # Layer-2 workflow harnesses are pi/codex/fake only (LAW 1). CLAUDE_SDK is a
    # Layer-1 adapter, intentionally NOT selectable as a workflow harness, so the
    # map covers exactly the L2-selectable kinds — not every AgentRuntimeKind.
    assert _HARNESS_KINDS["pi"] is AgentRuntimeKind.PI_HEADLESS
    assert set(_HARNESS_KINDS.values()) == {
        AgentRuntimeKind.FAKE,
        AgentRuntimeKind.CODEX_EXEC,
        AgentRuntimeKind.PI_HEADLESS,
    }
    assert AgentRuntimeKind.CLAUDE_SDK not in _HARNESS_KINDS.values()


def test_resolve_harness_pi_case_insensitive_unknown_raises_and_auto_still_validates() -> None:
    assert _resolve_harness("pi") is AgentRuntimeKind.PI_HEADLESS
    assert _resolve_harness("PI") is AgentRuntimeKind.PI_HEADLESS
    with pytest.raises(typer.BadParameter):
        _resolve_harness("nope")
    # The auto-default shim only authors the NAME; kind validation stays in
    # _resolve_harness.
    assert _resolve_harness(_resolve_default_harness("fake")) is AgentRuntimeKind.FAKE


# ---------------------------------------------------------------------------
# v0.1.64 FR3 — the "auto" default sentinel shim (_resolve_default_harness).
# ---------------------------------------------------------------------------

_ECHO_PREFIX = "[harness] auto-default:"


@pytest.mark.parametrize(
    ("name", "env", "explicit_or_auto", "expected", "expect_echo"),
    [
        # AC-3: explicit --harness always wins with NO auto-default echo — even when
        # an entry signal is present in the environment.
        ("explicit_fake", {"DADAIA_ENTRY_HARNESS": "pi"}, "fake", "fake", False),
        ("explicit_codex", {"DADAIA_ENTRY_HARNESS": "pi"}, "codex", "codex", False),
        ("explicit_pi", {"DADAIA_ENTRY_HARNESS": "pi"}, "pi", "pi", False),
        ("explicit_fake_uppercase", {"DADAIA_ENTRY_HARNESS": "pi"}, "FAKE", "FAKE", False),
        # auto without signal resolves fake silently.
        ("auto_no_signal", {}, "auto", "fake", False),
        # AC-3 + AC-9 sabotage (d): auto-defaulting a REAL worker is never silent — the
        # loud echo names the harness and the override. Dropping the echo fails here.
        ("auto_dadaia_entry_pi", {"DADAIA_ENTRY_HARNESS": "pi"}, "auto", "pi", True),
        ("auto_dadaia_entry_codex", {"DADAIA_ENTRY_HARNESS": "codex"}, "auto", "codex", True),
        ("auto_codex_session_id", {"CODEX_SESSION_ID": "codex-sess-1"}, "auto", "codex", True),
    ],
)
def test_resolve_default_harness_table(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    name: str,
    env: dict[str, str],
    explicit_or_auto: str,
    expected: str,
    expect_echo: bool,
) -> None:
    monkeypatch.delenv("DADAIA_ENTRY_HARNESS", raising=False)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    result = _resolve_default_harness(explicit_or_auto)
    assert result == expected

    captured = capsys.readouterr()
    if expect_echo:
        assert (
            f"[harness] auto-default: {expected} (from entry session; pass --harness to override)"
            in captured.err
        )
    else:
        assert _ECHO_PREFIX not in captured.err
        assert _ECHO_PREFIX not in captured.out
