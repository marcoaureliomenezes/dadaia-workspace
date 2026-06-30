"""Tests for session-bound specs directory resolution."""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.specs_resolver import resolve_specs_dir


def test_resolve_specs_dir_uses_persisted_incumbent_bind(tmp_path: Path, monkeypatch) -> None:
    """A persisted bind resolves without DADAIA_CONTEXT or DADAIA_SESSION_ID env."""
    workspace = tmp_path
    specs = workspace / "repos" / "ctxa" / "specs"
    specs.mkdir(parents=True)
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text("[]", encoding="utf-8")
    sessions = workspace / ".dadaia" / "sessions"
    runtime = sessions / "runtime"
    runtime.mkdir(parents=True)
    (sessions / "sess_bound.json").write_text(
        json.dumps({"session_id": "sess_bound", "context": "ctxa"}),
        encoding="utf-8",
    )
    (runtime / "ctxa.ptr").write_text("sess_bound", encoding="utf-8")
    monkeypatch.chdir(workspace)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)

    assert resolve_specs_dir(None) == specs.resolve()
