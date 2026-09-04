"""Unit tests for state_v3 migration (spec_contexts.json v2 -> v3, FR15).

Intent: CONTRACT — A15.1, A15.2, V8 (registry v2->v3 migration round-trip on a real v2
registry); bug migrate-v3-backup-lands-in-closed-states-canon (the hop writes nothing
outside ``STATES_CANON``).

Covers the schema-drop law's migration: canon-clean (the only file the hop touches is
``spec_contexts.json`` itself), idempotent (a second run makes zero writes), and
behaviourally-identical-with-zero-associated-repos (A15.2), proven through the real
JsonContextStore, not just by inspecting JSON keys.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.spec_context import AssociatedRepo
from dadaia_workspace.core.workspace_layout import STATES_CANON
from dadaia_workspace.features.migrate.state_v3 import execute_migration, plan_migration
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore


def _write_v2(states_dir: Path, contexts: list[dict] | None = None) -> None:  # type: ignore[type-arg]
    data = {
        "schema_version": "2",
        "contexts": contexts
        or [
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
    (states_dir / "spec_contexts.json").write_text(json.dumps(data), encoding="utf-8")


def _write_v3(states_dir: Path) -> None:
    data = {
        "schema_version": "3",
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
                "associated_repos": [],
            }
        ],
    }
    (states_dir / "spec_contexts.json").write_text(json.dumps(data), encoding="utf-8")


def _states(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    return states


# ---------------------------------------------------------------------------
# plan_migration: detection matrix
# ---------------------------------------------------------------------------


def test_plan_migration_detection_matrix(tmp_path: Path) -> None:
    states_v2 = _states(tmp_path / "v2")
    _write_v2(states_v2)
    plan = plan_migration(states_v2)
    assert plan.schema_version_before == "2"
    assert plan.already_v3 is False
    assert len(plan.contexts_to_migrate) == 1
    assert plan.contexts_to_migrate[0]["name"] == "my-ctx"
    assert plan.contexts_to_migrate[0]["had_associated_repos"] is False
    # Never mutates on plan (dry-run display path).
    before = (states_v2 / "spec_contexts.json").read_text()
    plan_migration(states_v2)
    assert (states_v2 / "spec_contexts.json").read_text() == before

    states_v3 = _states(tmp_path / "v3")
    _write_v3(states_v3)
    plan_v3 = plan_migration(states_v3)
    assert plan_v3.already_v3 is True
    assert plan_v3.contexts_to_migrate == []

    states_none = _states(tmp_path / "none")
    plan_none = plan_migration(states_none)
    assert plan_none.already_v3 is True

    states_bad = _states(tmp_path / "bad")
    bad = {"schema_version": "99", "contexts": []}
    (states_bad / "spec_contexts.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="Unknown schema_version"):
        plan_migration(states_bad)


# ---------------------------------------------------------------------------
# A15.1 + bug migrate-v3-backup-lands-in-closed-states-canon: the hop rewrites
# spec_contexts.json and leaves states/ holding canon entries only.
# ---------------------------------------------------------------------------


def test_execute_migration_writes_nothing_outside_the_states_canon(tmp_path: Path) -> None:
    states = _states(tmp_path)
    _write_v2(states)
    ctx_file = states / "spec_contexts.json"

    execute_migration(states)

    entries = {p.name for p in states.iterdir()}
    assert entries == {"spec_contexts.json"}
    assert entries <= STATES_CANON

    migrated = json.loads(ctx_file.read_text())
    assert migrated["schema_version"] == "3"
    assert migrated["contexts"][0]["associated_repos"] == []


def test_execute_migration_preserves_existing_fields(tmp_path: Path) -> None:
    states = _states(tmp_path)
    _write_v2(
        states,
        contexts=[
            {
                "name": "ctx-a",
                "state": "dead",
                "repo_slug": "ctx-a",
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00Z",
                "alive_since": None,
                "dead_since": "2026-02-01T00:00:00Z",
                "current_branch": None,
            }
        ],
    )
    execute_migration(states)
    row = json.loads((states / "spec_contexts.json").read_text())["contexts"][0]
    assert row["name"] == "ctx-a"
    assert row["state"] == "dead"
    assert row["dead_since"] == "2026-02-01T00:00:00Z"
    assert row["associated_repos"] == []


# ---------------------------------------------------------------------------
# A15.1: idempotent — re-running after success makes zero writes.
# ---------------------------------------------------------------------------


def test_execute_migration_rerun_is_a_noop(tmp_path: Path) -> None:
    states = _states(tmp_path)
    _write_v2(states)
    execute_migration(states)

    ctx_file = states / "spec_contexts.json"
    after_first = ctx_file.read_bytes()
    ctx_mtime = ctx_file.stat().st_mtime_ns

    execute_migration(states)

    assert ctx_file.read_bytes() == after_first
    assert ctx_file.stat().st_mtime_ns == ctx_mtime


def test_execute_migration_on_already_v3_is_a_noop(tmp_path: Path) -> None:
    states = _states(tmp_path)
    _write_v3(states)
    before = (states / "spec_contexts.json").read_text()

    execute_migration(states)

    assert (states / "spec_contexts.json").read_text() == before
    assert {p.name for p in states.iterdir()} == {"spec_contexts.json"}


def test_execute_migration_missing_file_is_a_noop(tmp_path: Path) -> None:
    states = _states(tmp_path)
    execute_migration(states)  # must not raise
    assert not (states / "spec_contexts.json").exists()


def test_execute_migration_unknown_version_raises(tmp_path: Path) -> None:
    states = _states(tmp_path)
    bad = {"schema_version": "99", "contexts": []}
    (states / "spec_contexts.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="Unknown schema_version"):
        execute_migration(states)


# ---------------------------------------------------------------------------
# A15.2 — behavioural proof through the real store: a migrated v3 registry with
# zero associated repos behaves identically to the pre-migration v2 registry.
# ---------------------------------------------------------------------------


def test_migrated_registry_is_behaviourally_identical_to_v2(tmp_path: Path) -> None:
    states = _states(tmp_path)
    _write_v2(states)

    store = JsonContextStore(states)
    before = store.get("my-ctx")
    assert before is not None

    execute_migration(states)

    store_after = JsonContextStore(states)
    after = store_after.get("my-ctx")
    assert after is not None

    assert after.associated_repos == () == before.associated_repos
    assert (
        after.all_repos()
        == before.all_repos()
        == (AssociatedRepo(slug="my-ctx", url="https://github.com/org/my-ctx"),)
    )
    # Every other field is untouched by the hop.
    assert after.name == before.name
    assert after.state == before.state
    assert after.repo_slug == before.repo_slug
    assert after.repo_url == before.repo_url
    assert after.alive_since == before.alive_since
    assert after.dead_since == before.dead_since
    assert after.current_branch == before.current_branch
