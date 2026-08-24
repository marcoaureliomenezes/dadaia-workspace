"""PanelService — read-only orchestrator for the Dadaia Workspace Panel.

Responsibilities
----------------
- Fan out to ServerRegistryProvider and ContextProjectProvider (injected via DI).
- Group server registry entries by project against active contexts using
  best-effort case-insensitive matching (D1.A from architect report).
- Expose alive Spec Context Projects as PanelContext dataclasses, including the
  cached current_branch field from SpecContextService (R4: no git subprocess per
  request — potential staleness is accepted for Release-1; see PLAN risks R4). FR18
  (T-044-29) extends this to also carry each context's associated repos (slug + url,
  the FR15 registry data — no live git status, keeping the R4 no-subprocess posture).
- Expose the canonical agent catalog via list_canonical_agents() (PR3-08).

Dataclasses
-----------
- ServerRow   — one row in the server table (port, project, url, status, pid,
                expires_at, description).
- ServerGroup — a named group of ServerRows (group_label, context_name | None,
                rows).
- PanelContext — one alive Spec Context Project (slug, name, repo_path, branch,
                 status, associated).
- PanelAssociatedRepo — one associated repo on a PanelContext (slug, url).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.agent import AgentDTO, AgentPromptResult
from dadaia_workspace.core.models.server_registry import PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.protocols.agents_provider import AgentsProvider
from dadaia_workspace.core.protocols.context_project_provider import ContextProjectProvider
from dadaia_workspace.core.protocols.server_registry_provider import ServerRegistryProvider


@dataclass
class ServerRow:
    """One row in the panel's Servers table."""

    port: int
    project: str
    url: str
    status: str  # "active" | "stale"
    pid: int | None
    expires_at: str
    description: str | None


@dataclass
class ServerGroup:
    """A labelled group of server rows.

    group_label    — repo_slug of the matching context, or "Outros".
    context_name   — human-readable context name, or None when unmatched.
    rows           — ordered list of ServerRow entries belonging to this group.
    """

    group_label: str
    context_name: str | None
    rows: list[ServerRow] = field(default_factory=list)


@dataclass(frozen=True)
class PanelAssociatedRepo:
    """One FR15 associated repo on a :class:`PanelContext` card (FR18/T-044-29).

    slug/url only — no live on-disk/branch status, matching the R4 no-git-subprocess
    posture the main repo's ``branch`` field already carries.
    """

    slug: str
    url: str


@dataclass
class PanelContext:
    """One active Spec Context Project as seen by the panel.

    branch — consumed as-is from SpecContextService (cached at last activate/show).
             No git subprocess is invoked per request (R4 trade-off).
             The rendering layer displays "(unknown)" when branch is None.
    associated — this context's FR15 associated repos (main repo excluded, matching
                 FR19's "one place of control" boundary); empty tuple when none.
    """

    slug: str
    name: str
    repo_path: Path
    branch: str | None
    status: str
    associated: tuple[PanelAssociatedRepo, ...] = ()


class PanelService:
    """Read-only orchestrator for the panel data model.

    Parameters
    ----------
    registry:
        A ServerRegistryProvider instance (injected).
    spec_context:
        A ContextProjectProvider instance (injected).
    workspace_root:
        Absolute path to the workspace root directory.  Used to construct
        repo_path in PanelContext without reaching into SpecContextService
        private attributes.
    report_retention:
        Optional ReportRetentionService instance (injected, T-017-08).
        When None, a RuntimeError is raised on first use.  The container always
        injects one; pass a fake for tests.
    adapter_registry:
        Optional mapping of runtime name -> RuntimeAdapter (injected, T-017-08).
        When None defaults to an empty dict (no enrichment).  The container
        always injects ADAPTER_REGISTRY; pass a fake mapping for tests.
    """

    def __init__(
        self,
        registry: ServerRegistryProvider,
        spec_context: ContextProjectProvider,
        workspace_root: Path,
        telemetry: Any = None,
        academy: Any = None,
        report_retention: Any = None,
        adapter_registry: dict[str, Any] | None = None,
        agents_provider: AgentsProvider | None = None,
    ) -> None:
        """Initialise PanelService.

        Parameters
        ----------
        registry:
            A ServerRegistryProvider instance (injected).
        spec_context:
            A ContextProjectProvider instance (injected).
        workspace_root:
            Absolute path to the workspace root directory.
        telemetry:
            Optional TelemetryService instance (injected).  When None,
            a default TelemetryService is NOT built automatically here —
            wiring the default instance is the responsibility of the
            boot layer (``dadaia_workspace/cli/commands/panel.py``).
            Passing None is safe: telemetry endpoints will return 503
            until a real TelemetryService is injected.
        academy:
            Optional AcademyService instance (injected).  When None,
            the Academy tab returns an empty course list.
        report_retention:
            ReportRetentionService instance (injected, T-017-08).
            When None, calling get_report_retention() raises RuntimeError.
        adapter_registry:
            Mapping of runtime name to RuntimeAdapter (injected, T-017-08).
            When None, get_session_adapter() always returns None (no enrichment).
        """
        self._registry = registry
        self._spec_context = spec_context
        self._workspace_root = workspace_root
        self.telemetry = telemetry
        self.academy = academy
        # AR-03: injected dependencies for report retention and adapter registry.
        self._report_retention = report_retention
        self._adapter_registry: dict[str, Any] = (
            adapter_registry if adapter_registry is not None else {}
        )
        # NEW-02: agents read surface injected via the AgentsProvider protocol;
        # lazy fallback keeps callers that do not inject one working.
        self._agents_provider = agents_provider

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def workspace_root(self) -> Path:
        """Return the workspace root path (public accessor, T-017-08)."""
        return self._workspace_root

    def list_servers_grouped(self) -> list[ServerGroup]:
        """Return all server registry entries grouped by matching context.

        Matching rule (D1.A): project.lower() == repo_slug.lower() against
        active contexts only. Unmatched entries fall into group "Outros".

        Returns an empty list when the registry is empty.
        """
        entries = self._registry.list_entries(include_stale=True)
        if not entries:
            return []

        active_contexts = self._active_contexts()
        # Build a lookup: lowercased repo_slug -> SpecContextProject
        slug_index: dict[str, SpecContextProject] = {
            ctx.repo_slug.lower(): ctx for ctx in active_contexts
        }

        # Map group_label -> ServerGroup (order: matched first, Outros last)
        groups: dict[str, ServerGroup] = {}

        for entry, status in entries:
            project_lower = entry.project.lower()
            matched_ctx = slug_index.get(project_lower)

            if matched_ctx is not None:
                label = matched_ctx.repo_slug
                if label not in groups:
                    groups[label] = ServerGroup(
                        group_label=label,
                        context_name=matched_ctx.name,
                    )
                target_group = groups[label]
            else:
                if "Outros" not in groups:
                    groups["Outros"] = ServerGroup(group_label="Outros", context_name=None)
                target_group = groups["Outros"]

            target_group.rows.append(
                ServerRow(
                    port=entry.port,
                    project=entry.project,
                    url=entry.url,
                    status=PortStatus.ACTIVE if status == PortStatus.ACTIVE else PortStatus.STALE,
                    pid=entry.pid,
                    expires_at=entry.expires_at,
                    description=entry.description,
                )
            )

        # Return matched groups first, Outros last (stable order)
        result = [g for label, g in groups.items() if label != "Outros"]
        if "Outros" in groups:
            result.append(groups["Outros"])
        return result

    def list_active_contexts(self) -> list[PanelContext]:
        """Return all active Spec Context Projects as PanelContext dataclasses.

        Filters to state == alive only.  branch is taken from the cached
        current_branch field of SpecContextProject (no git subprocess — R4).
        """
        return [
            PanelContext(
                slug=ctx.repo_slug,
                name=ctx.name,
                repo_path=self._workspace_root / "repos" / ctx.repo_slug,
                branch=ctx.current_branch,
                status="alive",
                associated=tuple(
                    PanelAssociatedRepo(slug=repo.slug, url=repo.url)
                    for repo in ctx.associated_repos
                ),
            )
            for ctx in self._active_contexts()
        ]

    def _agents(self) -> AgentsProvider:
        """Return the injected AgentsProvider.

        NEW-02: PanelService depends only on the ``AgentsProvider`` protocol —
        no concrete sibling-feature import (module-level or lazy). The
        composition root (container.py) always injects ``FileSystemAgentsProvider``;
        callers that do not inject one receive a clear error (same fail-clear
        contract). For tests, set ``_canonical_agents_override``
        or pass a fake ``agents_provider``.
        """
        if self._agents_provider is None:
            raise RuntimeError(
                "PanelService requires an AgentsProvider to be injected via "
                "'agents_provider'. The composition root (container.py) always "
                "provides one; pass a fake for tests."
            )
        return self._agents_provider

    def list_canonical_agents(self) -> list[AgentDTO]:
        """Return the canonical agent catalog.

        Resolution order (delegated to the AgentsProvider):
          1. $DADAIA_AGENTS_DIR env var
          2. <workspace_root>/.dadaia/agentic/agents/
          3. <workspace_root>/.claude/agents/

        For testing, ``_canonical_agents_override`` may be set on the instance
        to bypass the filesystem read and return a controlled list directly.
        """
        override = getattr(self, "_canonical_agents_override", None)
        if override is not None:
            return list(override)
        return self._agents().read_canonical_agents(self._workspace_root)

    def get_agent_prompt(self, agent_id: str) -> AgentPromptResult:
        """Resolve an agent ID to its system prompt and source path.

        NEW-01: the panel view layer calls this instead of importing
        ``features.agents.reader.get_prompt`` directly. Raises the core-typed
        ``InvalidAgentIdError`` / ``AgentNotFoundError`` from
        ``core.models.agent`` on bad input / missing agent.
        """
        return self._agents().get_prompt(agent_id, self._workspace_root)

    def get_report_retention(self) -> Any:
        """Return the injected ReportRetentionService.

        AR-03: views must not construct ReportRetentionService per-request.
        The container always injects one; tests pass a fake.

        Raises
        ------
        RuntimeError
            When no ReportRetentionService was injected.
        """
        if self._report_retention is None:
            raise RuntimeError(
                "PanelService requires a ReportRetentionService to be injected via "
                "'report_retention'. The composition root (container.py) always "
                "provides one; pass a fake for tests."
            )
        return self._report_retention

    def get_session_adapter(self, runtime: str) -> Any:
        """Return the RuntimeAdapter for *runtime*, or None if not found.

        AR-03: views must not import ADAPTER_REGISTRY directly.
        The container injects the registry; tests pass a fake mapping.
        """
        return self._adapter_registry.get(runtime)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _active_contexts(self) -> list[SpecContextProject]:
        """Return contexts with state == alive."""
        return [ctx for ctx in self._spec_context.list_all() if ctx.state == ContextState.ALIVE]
