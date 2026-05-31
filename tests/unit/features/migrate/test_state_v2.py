"""Unit tests for state_v2 migration (spec_contexts.json v1 → v2).

Covers AC-T10c-1..6 and AC-T10a-5..6 migration path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.state_v2 import execute_migration, plan_migration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_v1(states_dir: Path, contexts: list[dict] | None = None) -> None:
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
# plan_migration
# ---------------------------------------------------------------------------


def test_plan_migration_detects_v1(tmp_path: Path) -> None:
    ws, states = _workspace(tmp_path)
    _write_v1(states)
    plan = plan_migration(states)
    assert plan.schema_version_before == "1"
    assert plan.already_v2 is False
    assert len(plan.contexts_to_migrate) == 1
    assert plan.contexts_to_migrate[0]["old_state"] == "ativo"
    assert plan.contexts_to_migrate[0]["new_state"] == "alive"


def test_plan_migration_detects_v2_as_noop(tmp_path: Path) -> None:
    ws, states = _workspace(tmp_path)
    _write_v2(states)
    plan = plan_migration(states)
    assert plan.already_v2 is True
    assert plan.contexts_to_migrate == []


def test_plan_migration_no_file_is_noop(tmp_path: Path) -> None:
    ws, states = _workspace(tmp_path)
    plan = plan_migration(states)
    assert plan.already_v2 is True


def test_plan_migration_unknown_version_raises(tmp_path: Path) -> None:
    ws, states = _workspace(tmp_path)
    bad = {"schema_version": "99", "contexts": []}
    (states / "spec_contexts.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="Unknown schema_version"):
        plan_migration(states)


# ---------------------------------------------------------------------------
# AC-T10c-1: dry-run on v1 file prints planned changes, exits 0, writes nothing
# ---------------------------------------------------------------------------


def test_dry_run_via_plan_migration_does_not_write(tmp_path: Path) -> None:
    """Verify plan_migration() never writes anything (used for dry-run display)."""
    ws, states = _workspace(tmp_path)
    _write_v1(states)
    before = (states / "spec_contexts.json").read_text()
    plan_migration(states)  # must not mutate
    after = (states / "spec_contexts.json").read_text()
    assert before == after


# ---------------------------------------------------------------------------
# AC-T10c-2: execute_migration on v1 performs all 12 actions, exits 0
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


def test_execute_migration_deletes_primary_context_json(tmp_path: Path) -> None:
    """AC-T10c-5: After migration, primary_context.json must not exist."""
    ws, states = _workspace(tmp_path)
    _write_v1(states)
    primary = states / "primary_context.json"
    primary.write_text(json.dumps({"name": "my-ctx", "repo_slug": "my-ctx", "specs_dir": "/x"}))
    assert primary.exists()

    execute_migration(states, ws)
    assert not primary.exists()


def test_execute_migration_creates_required_dirs(tmp_path: Path) -> None:
    """AC-T10c-6: sessions/, locks/implementation/, states/ctx_locks/ created."""
    ws, states = _workspace(tmp_path)
    _write_v1(states)
    execute_migration(states, ws)

    assert (ws / ".dadaia" / "sessions").is_dir()
    assert (ws / ".dadaia" / "locks" / "implementation").is_dir()
    assert (ws / ".dadaia" / "states" / "ctx_locks").is_dir()


def test_execute_migration_appends_audit_event(tmp_path: Path) -> None:
    """Migration appends an event to lock-events.jsonl."""
    ws, states = _workspace(tmp_path)
    _write_v1(states)
    execute_migration(states, ws)

    log_file = ws / ".dadaia" / "logs" / "lock-events.jsonl"
    assert log_file.exists()
    lines = [ln for ln in log_file.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 1
    event = json.loads(lines[0])
    assert event["event"] in ("MIGRATION_COMPLETE", "MIGRATION_SKIPPED")


# ---------------------------------------------------------------------------
# AC-T10c-3: execute_migration on v2 file is a no-op (idempotent)
# ---------------------------------------------------------------------------


def test_execute_migration_v2_is_noop(tmp_path: Path) -> None:
    """Migrating a v2 file must not change the JSON content."""
    ws, states = _workspace(tmp_path)
    _write_v2(states)
    before = (states / "spec_contexts.json").read_text()

    execute_migration(states, ws)

    after = (states / "spec_contexts.json").read_text()
    assert json.loads(before) == json.loads(after)


def test_execute_migration_twice_is_idempotent(tmp_path: Path) -> None:
    """Running execute_migration twice on the same workspace must not fail."""
    ws, states = _workspace(tmp_path)
    _write_v1(states)
    execute_migration(states, ws)
    # Second run: now a v2 file
    execute_migration(states, ws)
    data = json.loads((states / "spec_contexts.json").read_text())
    assert data["schema_version"] == "2"
