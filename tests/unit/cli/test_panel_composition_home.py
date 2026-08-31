"""F001 (20260830-design-bug-surface-audit): the panel's 20-route composition leaves
the container for its single production consumer's side — cli/commands/
panel_composition.py (ADR-0001: a single consumer builds directly). The dead
process-ancestry chain (protocol + adapter + factory, zero production consumers) is
deleted outright. Intent: contract; size: unit."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_panel_views_compose_from_the_cli_side(tmp_path: Path) -> None:
    from dadaia_workspace.cli.commands import panel_composition

    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text('{"schema_version": "2", "contexts": []}')

    views = panel_composition.build_panel_views(tmp_path)

    assert isinstance(views, dict)
    assert "api_kanban" not in views
    assert "index" in views and "api_contexts" in views
    assert all(callable(v) for v in views.values())


def test_container_no_longer_carries_panel_or_ancestry_wiring() -> None:
    from dadaia_workspace import container

    for name in (
        "build_panel_views",
        "build_panel_service",
        "build_telemetry_service",
        "build_agent_model_policy_service",
        "build_process_ancestry",
    ):
        assert not hasattr(container, name), name


def test_process_ancestry_chain_is_deleted() -> None:
    repo = Path(__file__).resolve().parents[3]
    assert not (repo / "dadaia_workspace" / "core" / "protocols" / "process_ancestry.py").exists()
    assert not (
        repo / "dadaia_workspace" / "infrastructure" / "process_ancestry_adapter.py"
    ).exists()


def test_panel_service_still_guards_initialization(tmp_path: Path) -> None:
    from dadaia_workspace.cli.commands import panel_composition
    from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError

    with pytest.raises(WorkspaceNotInitializedError):
        panel_composition.build_panel_service(tmp_path)
