"""Intent: CONTRACT — migrate-and-reconcile-crash-on-a-schema-3-context-registry.

A registry at or above the migration target (the store writes schema 3) is a no-op
for plan and execute alike; a non-numeric version is still refused.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.state_v2 import execute_migration, plan_migration


def _registry(tmp_path: Path, version: object) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": version, "contexts": [{"name": "a", "state": "alive"}]}),
        encoding="utf-8",
    )
    return states


def test_schema_3_registry_plans_nothing_and_executes_unchanged(tmp_path: Path) -> None:
    states = _registry(tmp_path, "3")
    before = (states / "spec_contexts.json").read_text(encoding="utf-8")
    plan = plan_migration(states)
    assert plan.already_v2 is True
    assert plan.contexts_to_migrate == []
    execute_migration(states, tmp_path)
    assert (states / "spec_contexts.json").read_text(encoding="utf-8") == before


def test_non_numeric_schema_version_is_refused(tmp_path: Path) -> None:
    states = _registry(tmp_path, "banana")
    with pytest.raises(ValueError, match="banana"):
        plan_migration(states)
    with pytest.raises(ValueError, match="banana"):
        execute_migration(states, tmp_path)
