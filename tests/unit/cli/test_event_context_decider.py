"""``resolve_event_context_for_cli`` — the ONE decider both the governance-event writer
and the doctor's baseline reader use, so an event can never be filtered out by the
context the verb itself resolved.

Intent: CONTRACT — 0.4.7 FR2/FR6 (code review c3 HIGH-2: an env-derived context beside
the resolved one made `doctor --context B` report B's own verb-written records as hand
edits). Size: SMALL — real ``tmp_path`` filesystem, no subprocess/network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.cli._specs_resolution import resolve_event_context_for_cli


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}', encoding="utf-8"
    )
    return root


def test_the_resolved_specs_tree_names_the_context_over_a_divergent_bind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _workspace(tmp_path)
    specs = root / "repos" / "ctx-b" / "specs"
    specs.mkdir(parents=True)
    monkeypatch.setenv("DADAIA_CONTEXT", "ctx-a")

    assert resolve_event_context_for_cli(specs) == "ctx-b"


def test_a_tree_belonging_to_no_context_never_borrows_the_bind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bind is not a rung at all: it names where the SESSION is bound, which every
    ``--context``/``--specs-dir`` overrides. A tree that names no context resolves to
    ``""`` rather than to whatever the shell happened to export."""
    monkeypatch.setenv("DADAIA_CONTEXT", "ctx-a")

    assert resolve_event_context_for_cli(None) == ""
    assert resolve_event_context_for_cli(tmp_path / "loose" / "specs") == ""


def test_the_self_hosting_root_specs_tree_names_its_own_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The inverse of ``resolve_context_specs_dir``'s root fallback: a context whose
    ``repos/<slug>/specs`` does not exist resolves to ``workspace_root/specs``, so that
    tree names THAT context — with no bind in the environment (c3 LOW-13: the root tree
    stamped ``""`` and the doctor was silent for it)."""
    root = tmp_path / "ws"
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {"name": "lib-ws", "repo_slug": "lib-ws", "state": "alive"},
                    {"name": "ctx-b", "repo_slug": "ctx-b", "state": "alive"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "repos" / "ctx-b" / "specs").mkdir(parents=True)
    (root / "specs").mkdir()
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)

    assert resolve_event_context_for_cli(root / "specs") == "lib-ws"
