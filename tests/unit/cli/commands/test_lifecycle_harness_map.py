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


def test_harness_map_includes_pi() -> None:
    assert _HARNESS_KINDS["pi"] is AgentRuntimeKind.PI_HEADLESS


def test_harness_map_covers_layer2_selectable_kinds() -> None:
    # Layer-2 workflow harnesses are pi/codex/fake only (LAW 1). CLAUDE_SDK is a
    # Layer-1 adapter, intentionally NOT selectable as a workflow harness, so the
    # map covers exactly the L2-selectable kinds — not every AgentRuntimeKind.
    assert set(_HARNESS_KINDS.values()) == {
        AgentRuntimeKind.FAKE,
        AgentRuntimeKind.CODEX_EXEC,
        AgentRuntimeKind.PI_HEADLESS,
    }
    assert AgentRuntimeKind.CLAUDE_SDK not in _HARNESS_KINDS.values()


def test_resolve_harness_pi() -> None:
    assert _resolve_harness("pi") is AgentRuntimeKind.PI_HEADLESS
    assert _resolve_harness("PI") is AgentRuntimeKind.PI_HEADLESS


def test_resolve_harness_unknown_raises_bad_parameter() -> None:
    with pytest.raises(typer.BadParameter):
        _resolve_harness("nope")


# ---------------------------------------------------------------------------
# v0.1.64 FR3 — the "auto" default sentinel shim (_resolve_default_harness).
# ---------------------------------------------------------------------------

_ECHO_PREFIX = "[harness] auto-default:"


@pytest.mark.parametrize("explicit", ["fake", "codex", "pi", "FAKE"])
def test_explicit_harness_passes_through_without_echo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], explicit: str
) -> None:
    # AC-3: explicit --harness always wins with NO auto-default echo — even when an
    # entry signal is present in the environment.
    monkeypatch.setenv("DADAIA_ENTRY_HARNESS", "pi")
    assert _resolve_default_harness(explicit) == explicit
    assert _ECHO_PREFIX not in capsys.readouterr().err


def test_auto_without_signal_resolves_fake_silently(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DADAIA_ENTRY_HARNESS", raising=False)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
    assert _resolve_default_harness("auto") == "fake"
    captured = capsys.readouterr()
    assert _ECHO_PREFIX not in captured.err
    assert _ECHO_PREFIX not in captured.out


@pytest.mark.parametrize(
    ("env_var", "value", "expected"),
    [
        ("DADAIA_ENTRY_HARNESS", "pi", "pi"),
        ("DADAIA_ENTRY_HARNESS", "codex", "codex"),
        ("CODEX_SESSION_ID", "codex-sess-1", "codex"),
    ],
)
def test_auto_with_signal_resolves_real_worker_with_loud_echo(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    env_var: str,
    value: str,
    expected: str,
) -> None:
    # AC-3 + AC-9 sabotage (d): auto-defaulting a REAL worker is never silent — the
    # loud echo names the harness and the override. Dropping the echo fails here.
    monkeypatch.setenv(env_var, value)
    assert _resolve_default_harness("auto") == expected
    err = capsys.readouterr().err
    assert (
        f"[harness] auto-default: {expected} (from entry session; pass --harness to override)"
        in err
    )


def test_auto_resolution_still_validates_via_resolve_harness() -> None:
    # The shim only authors the NAME; kind validation stays in _resolve_harness.
    assert _resolve_harness(_resolve_default_harness("fake")) is AgentRuntimeKind.FAKE
