"""Unit tests for T-017-06: WorkflowsService injected into PanelService.

Keeps only the executed-path assertion: list_workflow_summaries() delegates to
the injected workflows_service. The ``inspect.signature``/``getsource``
introspection tests (constructor-parameter presence, source-string
non-construction) were DELETED — they assert on implementation strings, not
executed behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.panel.service import PanelService

pytestmark = pytest.mark.unit


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


def test_list_workflow_summaries_uses_injected_service() -> None:
    """list_workflow_summaries() must delegate to the injected workflows_service."""
    fake = _FakeWorkflowsService(["workflow-a", "workflow-b"])
    service = _build_service(workflows_service=fake)

    summaries = service.list_workflow_summaries()

    assert fake.list_summaries_called == 1
    assert len(summaries) == 2
    assert summaries[0].name == "workflow-a"
