"""Unit tests for state_v2 migration (spec_contexts.json v1 → v2).

Covers AC-T10c-1..6 and AC-T10a-5..6 migration path. CRITICAL v1→v2 state migration:
transform correctness and idempotent double-run are kept as named tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.migrate.state_v2 import execute_migration, plan_migration


def _write_v1(states_dir: Path, contexts: list[dict[str, Any]] | None = None) -> None:
    """Write a v1 spec_contexts.json file."""
    data = {
        "schema_version": "1",
        "contexts": contexts
        or [
            {
                "name": "my-ctx",
                "state": "ativo",
                "repo_slug": "my-ctx",
                "repo_url": "https://github.com/org/my-ctx",
                "is_primary": True,
                "created_at": "2026-01-01T00:00:00Z",
                "activated_at": "2026-05-01T00:00:00Z",
                "current_branch": "main",
            }
        ],
    }
    (states_dir / "spec_contexts.json").write_text(json.dumps(data))


def _write_v2(states_dir: Path) -> None:
    """Write a v2 spec_contexts.json file."""
    data = {
        "schema_version": "2",
        "contexts": [
            {
                "name": "my-ctx",
                "state": "alive",
                "repo_slug": "my-ctx",
                "repo_url": "https://github.com/org/my-ctx",
                "created_at": "2026-01-01T00:00:00Z",
                "alive_since": "2026-05-01T00:00:00Z",
                "dead_since": None,
                "current_branch": "main",
            }
        ],
    }
    (states_dir / "spec_contexts.json").write_text(json.dumps(data))


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    """Return (workspace_root, states_dir) with .dadaia/states/ created."""
    ws = tmp_path / "ws"
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    return ws, states


# ---------------------------------------------------------------------------
# plan_migration: detection matrix (v1 / v2-noop / no-file / unknown-version)
# ---------------------------------------------------------------------------


def test_plan_migration_detection_matrix(tmp_path: Path) -> None:
    ws, states = _workspace(tmp_path / "v1")
    _write_v1(states)
    plan = plan_migration(states)
    assert plan.schema_version_before == "1"
    assert plan.already_v2 is False
    assert len(plan.contexts_to_migrate) == 1
    assert plan.contexts_to_migrate[0]["old_state"] == "ativo"
    assert plan.contexts_to_migrate[0]["new_state"] == "alive"
    # Never mutates on plan (dry-run display path).
    before = (states / "spec_contexts.json").read_text()
    plan_migration(states)
    assert (states / "spec_contexts.json").read_text() == before

    _, states_v2 = _workspace(tmp_path / "v2")
    _write_v2(states_v2)
    plan_v2 = plan_migration(states_v2)
    assert plan_v2.already_v2 is True
    assert plan_v2.contexts_to_migrate == []

    _, states_none = _workspace(tmp_path / "none")
    plan_none = plan_migration(states_none)
    assert plan_none.already_v2 is True

    _, states_bad = _workspace(tmp_path / "bad")
    bad = {"schema_version": "99", "contexts": []}
    (states_bad / "spec_contexts.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="Unknown schema_version"):
        plan_migration(states_bad)


# ---------------------------------------------------------------------------
# execute_migration: transform correctness (CRITICAL, named)
# ---------------------------------------------------------------------------


def test_execute_migration_transforms_contexts(tmp_path: Path) -> None:
    """ativo → alive, inativo → dead; is_primary removed; activated_at → alive_since."""
    ws, states = _workspace(tmp_path)
    _write_v1(
        states,
        contexts=[
            {
                "name": "ctx-a",
                "state": "ativo",
                "repo_slug": "ctx-a",
                "repo_url": "",
                "is_primary": True,
                "created_at": "2026-01-01T00:00:00Z",
                "activated_at": "2026-05-01T00:00:00Z",
            },
            {
                "name": "ctx-b",
                "state": "inativo",
                "repo_slug": "ctx-b",
                "repo_url": "",
                "is_primary": False,
                "created_at": "2026-01-01T00:00:00Z",
                "activated_at": None,
            },
        ],
    )
    execute_migration(states, ws)

    data = json.loads((states / "spec_contexts.json").read_text())
    assert data["schema_version"] == "2"
    rows = {c["name"]: c for c in data["contexts"]}

    ctx_a = rows["ctx-a"]
    assert ctx_a["state"] == "alive"
    assert ctx_a["alive_since"] == "2026-05-01T00:00:00Z"
    assert ctx_a["dead_since"] is None
    assert "is_primary" not in ctx_a
    assert "activated_at" not in ctx_a

    ctx_b = rows["ctx-b"]
    assert ctx_b["state"] == "dead"
    assert ctx_b["alive_since"] is None
    assert ctx_b["dead_since"] is None


# ---------------------------------------------------------------------------
# execute_migration: side effects (primary_context.json removal, dirs, audit event)
# ---------------------------------------------------------------------------


def test_execute_migration_side_effects_and_v2_noop(tmp_path: Path) -> None:
    ws, states = _workspace(tmp_path)
    _write_v1(states)
    primary = states / "primary_context.json"
    primary.write_text(json.dumps({"name": "my-ctx", "repo_slug": "my-ctx", "specs_dir": "/x"}))
    assert primary.exists()

    execute_migration(states, ws)

    # AC-T10c-5: primary_context.json removed.
    assert not primary.exists()
    # Session identity remains; retired lock namespaces and audit logs are not recreated.
    assert (ws / ".dadaia" / "sessions").is_dir()
    assert not (ws / ".dadaia" / "locks").exists()
    assert not (ws / ".dadaia" / "states" / "ctx_locks").exists()
    assert not (ws / ".dadaia" / "logs" / "lock-events.jsonl").exists()

    # Migrating an already-v2 file is a no-op (content unchanged).
    ws2, states2 = _workspace(tmp_path / "v2-noop")
    _write_v2(states2)
    before = (states2 / "spec_contexts.json").read_text()
    execute_migration(states2, ws2)
    after = (states2 / "spec_contexts.json").read_text()
    assert json.loads(before) == json.loads(after)


def test_execute_migration_twice_is_idempotent(tmp_path: Path) -> None:
    ws, states = _workspace(tmp_path)
    _write_v1(states)
    execute_migration(states, ws)
    # Second run: now a v2 file
    execute_migration(states, ws)
    data = json.loads((states / "spec_contexts.json").read_text())
    assert data["schema_version"] == "2"
