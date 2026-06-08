"""Unit tests for T-017-06: WorkflowsService injected into PanelService.

The test verifies that:
1. PanelService accepts workflows_service as a constructor parameter.
2. PanelService does NOT construct WorkflowsService internally (no
   self._workflows_service = WorkflowsService(...) in __init__).
3. When a workflows_service is injected, list_workflow_summaries() and
   run_workflow() use it (not an internally-created instance).
"""

from __future__ import annotations

import inspect
from pathlib import Path

from dadaia_workspace.features.panel.service import PanelService


class _FakeWorkflowSummary:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeWorkflowsService:
    """Minimal fake matching the WorkflowsService surface used by PanelService."""

    def __init__(self, names: list[str]) -> None:
        self._names = names
        self.list_summaries_called = 0

    def list_summaries(self) -> list[_FakeWorkflowSummary]:
        self.list_summaries_called += 1
        return [_FakeWorkflowSummary(n) for n in self._names]

    def get_detail(self, name: str) -> None:
        return None


class _FakeServerRegistryService:
    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[object]:
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


def test_panel_service_accepts_workflows_service_parameter() -> None:
    """PanelService constructor must accept a workflows_service parameter."""
    sig = inspect.signature(PanelService.__init__)
    assert "workflows_service" in sig.parameters, (
        "PanelService.__init__ must accept a workflows_service parameter (T-017-06)"
    )


def test_panel_service_does_not_construct_workflows_service_internally() -> None:
    """PanelService __init__ source must not contain WorkflowsService(workspace_root).

    This test is a code-quality guard: if WorkflowsService is constructed
    inside __init__, DI is bypassed.
    """
    import inspect as _inspect

    source = _inspect.getsource(PanelService.__init__)
    assert "WorkflowsService(workspace_root)" not in source, (
        "PanelService.__init__ must not self-construct WorkflowsService; "
        "inject it via the constructor parameter instead (T-017-06)"
    )


def test_list_workflow_summaries_uses_injected_service() -> None:
    """list_workflow_summaries() must delegate to the injected workflows_service."""
    fake = _FakeWorkflowsService(["workflow-a", "workflow-b"])
    service = _build_service(workflows_service=fake)

    summaries = service.list_workflow_summaries()

    assert fake.list_summaries_called == 1
    assert len(summaries) == 2
    assert summaries[0].name == "workflow-a"


def test_injected_service_is_used_by_run_workflow() -> None:
    """run_workflow must look up workflow names via the injected service."""
    fake = _FakeWorkflowsService(["my-workflow"])

    class _FakeLauncher:
        def launch(self, workflow_name: str, workspace_root: str, *, python_executable: str) -> int:
            return 42

        def is_alive(self, pid: int) -> bool:
            return False

    service = _build_service(workflows_service=fake)
    service._workflow_launcher = _FakeLauncher()  # type: ignore[attr-defined]

    result = service.run_workflow("my-workflow")
    assert result["pid"] == 42
    assert result["workflow"] == "my-workflow"
