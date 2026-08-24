"""Unit tests for PanelService — T-1.4.

Real service logic, two survivors:
  1. Grouping: casing tolerance + unmatched entry falls into "Outros".
  2. DEAD-context filtered from grouping AND from list_active_contexts +
     empty registry/contexts both return empty results.
"""

from pathlib import Path

import pytest

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.panel.service import PanelAssociatedRepo, PanelService

pytestmark = pytest.mark.unit


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
    associated_repos: tuple[AssociatedRepo, ...] = (),
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
        associated_repos=associated_repos,
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
# 1. Grouping: casing tolerance + unmatched entry falls into "Outros"
# ---------------------------------------------------------------------------


def test_grouping_casing_tolerance_and_unmatched_falls_into_outros() -> None:
    # project.lower() == repo_slug.lower() — case differences must still match.
    ctx = _make_context(name="My Workspace", repo_slug="dadaia-workspace")
    matched_entry = _make_entry(port=3000, project="DadaiA-WorkSpace")
    unmatched_entry = _make_entry(port=4000, project="completely-unknown")

    service = _build_service([matched_entry, unmatched_entry], [ctx])
    groups = service.list_servers_grouped()

    labels = [g.group_label for g in groups]
    assert "dadaia-workspace" in labels
    assert "Outros" in labels

    matched_group = next(g for g in groups if g.group_label == "dadaia-workspace")
    assert matched_group.context_name == "My Workspace"
    assert len(matched_group.rows) == 1
    assert matched_group.rows[0].port == 3000

    outros = next(g for g in groups if g.group_label == "Outros")
    assert len(outros.rows) == 1
    assert outros.rows[0].port == 4000
    assert outros.context_name is None


# ---------------------------------------------------------------------------
# 2. DEAD-context filtered + empty registry/contexts both return empty
# ---------------------------------------------------------------------------


def test_dead_context_filtered_and_empty_inputs_yield_empty_results() -> None:
    # A DEAD context cannot match a server entry -> the entry lands in Outros,
    # and the DEAD context is excluded from list_active_contexts().
    dead_ctx = _make_context(
        name="Inactive Project", repo_slug="inactive-project", state=ContextState.DEAD
    )
    entry = _make_entry(port=5000, project="inactive-project")

    service = _build_service([entry], [dead_ctx])
    groups = service.list_servers_grouped()
    labels = [g.group_label for g in groups]
    assert "Outros" in labels
    assert "inactive-project" not in labels
    assert service.list_active_contexts() == []

    # Empty registry -> no groups at all.
    ctx = _make_context(name="Some Project", repo_slug="some-project")
    empty_registry_service = _build_service([], [ctx])
    assert empty_registry_service.list_servers_grouped() == []

    # All-DEAD contexts -> list_active_contexts() returns [].
    only_dead_service = _build_service([], [dead_ctx])
    assert only_dead_service.list_active_contexts() == []


# ---------------------------------------------------------------------------
# 3. FR18/A18.5 — list_active_contexts() carries associated repos on the card
# ---------------------------------------------------------------------------


def test_panel_context_carries_associated_repos_with_and_without() -> None:
    """Intent: CONTRACT — FR18/A18.5. A context WITH associated repos surfaces them
    (slug + url, no live git status — R4); a context WITHOUT them keeps the empty
    default, so the pre-FR18 shape is unchanged for the common case."""
    with_assoc = _make_context(
        name="With Associated",
        repo_slug="with-associated",
        associated_repos=(AssociatedRepo(slug="infra", url="https://example.com/infra.git"),),
    )
    without_assoc = _make_context(name="No Associated", repo_slug="no-associated")

    service = _build_service([], [with_assoc, without_assoc])
    panel_contexts = {ctx.slug: ctx for ctx in service.list_active_contexts()}

    assert panel_contexts["with-associated"].associated == (
        PanelAssociatedRepo(slug="infra", url="https://example.com/infra.git"),
    )
    assert panel_contexts["no-associated"].associated == ()
