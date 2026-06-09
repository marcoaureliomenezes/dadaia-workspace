"""Unit tests for PanelService — T-1.4.

5 cases:
  (a) best-effort matcher casing tolerance
  (b) unmatched server entry falls into group "Outros"
  (c) inativo contexts are filtered out before matching
  (d) empty registry returns empty groups list
  (e) no active context returns empty contexts list
"""

from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import (
    PanelService,
)

# ---------------------------------------------------------------------------
# Fakes for ServerRegistryService and SpecContextService
# ---------------------------------------------------------------------------


class FakeServerRegistryService:
    def __init__(self, entries: list[tuple[PortEntry, PortStatus]]) -> None:
        self._entries = entries

    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[tuple[PortEntry, PortStatus]]:
        if project is None:
            return list(self._entries)
        return [(e, s) for e, s in self._entries if e.project == project]


class FakeSpecContextService:
    def __init__(self, contexts: list[SpecContextProject]) -> None:
        self._contexts = contexts

    def list_all(self) -> list[SpecContextProject]:
        return list(self._contexts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    port: int,
    project: str,
    status: PortStatus = PortStatus.ACTIVE,
) -> tuple[PortEntry, PortStatus]:
    entry = PortEntry(
        port=port,
        project=project,
        reserved_at="2026-01-01T00:00:00+00:00",
        expires_at="2026-01-01T08:00:00+00:00",
        url=f"http://localhost:{port}",
        pid=None,
        description=None,
    )
    return (entry, status)


def _make_context(
    name: str,
    repo_slug: str,
    state: ContextState = ContextState.ALIVE,
    current_branch: str | None = "main",
) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=repo_slug,
        repo_url=f"https://github.com/org/{repo_slug}",
        created_at="2026-01-01T00:00:00+00:00",
        alive_since="2026-01-01T00:00:00+00:00" if state == ContextState.ALIVE else None,
        dead_since=None if state == ContextState.ALIVE else "2026-01-01T00:00:00+00:00",
        current_branch=current_branch,
    )


def _build_service(
    entries: list[tuple[PortEntry, PortStatus]],
    contexts: list[SpecContextProject],
    workspace_root: Path = Path("/workspace"),
) -> PanelService:
    return PanelService(
        registry=FakeServerRegistryService(entries),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(contexts),  # type: ignore[arg-type]
        workspace_root=workspace_root,
    )


# ---------------------------------------------------------------------------
# (a) Best-effort matcher — casing tolerance
# ---------------------------------------------------------------------------


def test_grouping_casing_tolerance() -> None:
    """(a) project.lower() == repo_slug.lower() — case differences must match."""
    ctx = _make_context(name="My Workspace", repo_slug="dadaia-workspace")
    entry = _make_entry(port=3000, project="DadaiA-WorkSpace")

    service = _build_service([entry], [ctx])
    groups = service.list_servers_grouped()

    assert len(groups) == 1
    group = groups[0]
    assert group.group_label == "dadaia-workspace"
    assert group.context_name == "My Workspace"
    assert len(group.rows) == 1
    assert group.rows[0].port == 3000


# ---------------------------------------------------------------------------
# (b) Unmatched entry falls into group "Outros"
# ---------------------------------------------------------------------------


def test_unmatched_entry_falls_into_outros() -> None:
    """(b) A server whose project has no matching context goes to 'Outros'."""
    ctx = _make_context(name="Some Project", repo_slug="some-project")
    entry = _make_entry(port=4000, project="completely-unknown")

    service = _build_service([entry], [ctx])
    groups = service.list_servers_grouped()

    labels = [g.group_label for g in groups]
    assert "Outros" in labels

    outros = next(g for g in groups if g.group_label == "Outros")
    assert len(outros.rows) == 1
    assert outros.rows[0].port == 4000
    assert outros.context_name is None


# ---------------------------------------------------------------------------
# (c) Inativo contexts filtered out before matching
# ---------------------------------------------------------------------------


def test_inativo_context_filtered_out() -> None:
    """(c) Contexts with state=inativo are excluded from matching and from list_active_contexts."""
    inactive_ctx = _make_context(
        name="Inactive Project",
        repo_slug="inactive-project",
        state=ContextState.DEAD,
    )
    entry = _make_entry(port=5000, project="inactive-project")

    service = _build_service([entry], [inactive_ctx])

    # The server entry cannot match an inactive context — goes to Outros
    groups = service.list_servers_grouped()
    labels = [g.group_label for g in groups]
    assert "Outros" in labels
    assert "inactive-project" not in labels

    # list_active_contexts returns only ativo contexts
    active = service.list_active_contexts()
    assert active == []


# ---------------------------------------------------------------------------
# (d) Empty registry returns empty groups list
# ---------------------------------------------------------------------------


def test_empty_registry_returns_no_groups() -> None:
    """(d) When server_registry is empty, list_servers_grouped() returns []."""
    ctx = _make_context(name="Some Project", repo_slug="some-project")

    service = _build_service([], [ctx])
    groups = service.list_servers_grouped()

    assert groups == []


# ---------------------------------------------------------------------------
# (e) No active context returns empty contexts list
# ---------------------------------------------------------------------------


def test_no_active_context_returns_empty_contexts() -> None:
    """(e) When all contexts are inativo, list_active_contexts() returns []."""
    inactive = _make_context(name="Inactive", repo_slug="inactive", state=ContextState.DEAD)

    service = _build_service([], [inactive])
    result = service.list_active_contexts()

    assert result == []


# ---------------------------------------------------------------------------
# T-WH-18 — run_workflow() tests
# ---------------------------------------------------------------------------


class _FakeWorkflowSummary:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeWorkflowsService:
    def __init__(self, names: list[str]) -> None:
        self._names = names

    def list_summaries(self) -> list[_FakeWorkflowSummary]:
        return [_FakeWorkflowSummary(n) for n in self._names]


class _FakeWorkflowLauncher:
    """Test double for the WorkflowLauncher protocol (T-016-P06)."""

    def __init__(self, launch_pid: int = 99999, alive: bool = False) -> None:
        self._pid = launch_pid
        self._alive = alive

    def launch(self, workflow_name: str, workspace_root: str, *, python_executable: str) -> int:
        return self._pid

    def is_alive(self, pid: int) -> bool:
        return self._alive


def _build_service_with_workflows(
    workflow_names: list[str],
    workspace_root: Path = Path("/workspace"),
) -> PanelService:
    service = PanelService(
        registry=FakeServerRegistryService([]),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService([]),  # type: ignore[arg-type]
        workspace_root=workspace_root,
    )
    service._workflows_service_override = _FakeWorkflowsService(workflow_names)  # type: ignore[attr-defined]
    return service


def test_run_workflow_starts_subprocess(tmp_path: Path) -> None:
    """run_workflow returns a dict with pid and workflow name via the launcher."""
    service = _build_service_with_workflows(["my-workflow"])
    service._workflow_launcher = _FakeWorkflowLauncher(launch_pid=99999)  # type: ignore[attr-defined]

    result = service.run_workflow("my-workflow")

    assert result["workflow"] == "my-workflow"
    assert result["pid"] == 99999


def test_run_workflow_unknown_returns_error(tmp_path: Path) -> None:
    """run_workflow raises RuntimeError with 'not found' for unknown workflows."""
    import pytest

    service = _build_service_with_workflows(["existing-workflow"])

    with pytest.raises(RuntimeError, match="not found"):
        service.run_workflow("nonexistent-workflow")


def test_run_workflow_already_running_409(tmp_path: Path) -> None:
    """run_workflow raises RuntimeError with 'already running' when PID is alive."""
    import pytest

    service = _build_service_with_workflows(["my-workflow"])
    service._workflow_launcher = _FakeWorkflowLauncher(  # type: ignore[attr-defined]
        launch_pid=12345, alive=True
    )

    # First launch registers PID 12345.
    service.run_workflow("my-workflow")

    # Second launch: the tracked PID is still alive → 409 already-running.
    with pytest.raises(RuntimeError, match="already running"):
        service.run_workflow("my-workflow")
