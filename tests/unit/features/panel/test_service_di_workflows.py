"""PanelService delegates workflow reads to its governed catalog provider."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.panel.service import PanelService

pytestmark = pytest.mark.unit


class _FakeWorkflow:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeWorkflowsService:
    """Minimal fake matching the WorkflowsService surface used by PanelService."""

    def __init__(self, names: list[str]) -> None:
        self._names = names
        self.list_called = 0

    def list_dadaia_workflows(self) -> list[_FakeWorkflow]:
        self.list_called += 1
        return [_FakeWorkflow(n) for n in self._names]

    def get_dadaia_workflow(self, name: str) -> None:
        return None


class _FakeServerRegistryService:
    def list_entries(self, project: str | None = None, include_stale: bool = True) -> list[object]:
        return []


class _FakeSpecContextService:
    def list_all(self) -> list[object]:
        return []


def _build_service(
    workflows_service: _FakeWorkflowsService | None = None,
    workspace_root: Path = Path("/workspace"),
) -> PanelService:
    return PanelService(
        registry=_FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=_FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=workspace_root,
        workflows_service=workflows_service,  # type: ignore[arg-type]
    )


def test_list_dadaia_workflows_uses_injected_service() -> None:
    fake = _FakeWorkflowsService(["workflow-a", "workflow-b"])
    service = _build_service(workflows_service=fake)

    workflows = service.list_dadaia_workflows()

    assert fake.list_called == 1
    assert len(workflows) == 2
    assert workflows[0].name == "workflow-a"
