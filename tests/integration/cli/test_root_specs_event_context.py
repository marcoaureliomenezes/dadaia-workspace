"""A governance verb writing the SELF-HOSTING root ``specs/`` tree stamps its event with
that context's name — with nothing bound in the environment.

Intent: CONTRACT — 0.4.7 FR2/FR6 (code review c3 LOW-13: `context_name_for_specs_dir`
knew only the ``repos/<slug>/specs`` shape, so the root tree resolved to ``""`` and the
decider borrowed ``$DADAIA_CONTEXT``; an unbound shell then stamped ``""`` and `doctor`
was silent about every record that tree carried). Size: MEDIUM — the real CLI against a
tmp_path workspace and a tmp_path HOME, one SQLite file; no network, no git.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A self-hosting workspace: the library context ``lib-ws`` is registered ALIVE and
    its specs live at the workspace-root ``specs/`` — exactly the tree
    ``resolve_context_specs_dir``'s root fallback returns."""
    root = tmp_path / "ws"
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [{"name": "lib-ws", "repo_slug": "lib-ws", "state": "alive"}],
            }
        ),
        encoding="utf-8",
    )
    (root / "repos" / "lib-ws").mkdir(parents=True)
    (root / "specs" / "bugs").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    monkeypatch.chdir(root)
    return root


def _contexts(home: Path) -> list[str]:
    db = container.telemetry_state_dir() / "telemetry.sqlite"
    conn = sqlite3.connect(db)
    try:
        return [row[0] for row in conn.execute("SELECT context FROM governance_events")]
    finally:
        conn.close()


def test_a_bug_appended_to_the_root_tree_names_the_self_hosting_context(
    workspace: Path, tmp_path: Path
) -> None:
    result = _runner.invoke(
        app,
        [
            "bugs", "append", "--specs-dir", str(workspace / "specs"),
            "--bug-id", "root-tree-probe", "--title", "root tree probe",
            "--severity", "LOW", "--surface", "cli", "--component", "bugs",
            "--context", "lib-ws",
            "--symptom", "s", "--repro", "r", "--expected", "e",
        ],
    )  # fmt: skip

    assert result.exit_code == 0, result.output
    # The event's context is DERIVED from the tree the verb wrote; the record's own
    # ``--context`` label is never read by the writer (test_bugs_append_context_routing).
    assert _contexts(tmp_path / "home") == ["lib-ws"]
