"""``resolve_event_context_for_cli`` — the ONE decider both the governance-event writer
and the doctor's baseline reader use, so an event can never be filtered out by the
context the verb itself resolved.

Intent: CONTRACT — 0.4.7 FR2/FR6 (code review c3 HIGH-2: an env-derived context beside
the resolved one made `doctor --context B` report B's own verb-written records as hand
edits). Size: SMALL — real ``tmp_path`` filesystem, no subprocess/network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.cli._specs_resolution import resolve_event_context_for_cli


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text('{"version": 2, "contexts": []}', encoding="utf-8")
    return root


def test_the_resolved_specs_tree_names_the_context_over_a_divergent_bind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _workspace(tmp_path)
    specs = root / "repos" / "ctx-b" / "specs"
    specs.mkdir(parents=True)
    monkeypatch.setenv("DADAIA_CONTEXT", "ctx-a")

    assert resolve_event_context_for_cli(specs) == "ctx-b"


def test_the_bind_is_the_last_rung_when_no_tree_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DADAIA_CONTEXT", "ctx-a")

    assert resolve_event_context_for_cli(None) == "ctx-a"
    assert resolve_event_context_for_cli(tmp_path / "loose" / "specs") == "ctx-a"


def test_no_tree_and_no_bind_resolves_to_no_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)

    assert resolve_event_context_for_cli(None) == ""
