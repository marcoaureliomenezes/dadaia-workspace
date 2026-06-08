"""PanelService — read-only orchestrator for the Dadaia Workspace Panel.

Responsibilities
----------------
- Fan out to ServerRegistryProvider and ContextProjectProvider (injected via DI).
- Group server registry entries by project against active contexts using
  best-effort case-insensitive matching (D1.A from architect report).
- Expose alive Spec Context Projects as PanelContext dataclasses, including the
  cached current_branch field from SpecContextService (R4: no git subprocess per
  request — potential staleness is accepted for Release-1; see PLAN risks R4).
- Expose the canonical agent catalog via list_canonical_agents() (PR3-08).

Dataclasses
-----------
- ServerRow   — one row in the server table (port, project, url, status, pid,
                expires_at, description).
- ServerGroup — a named group of ServerRows (group_label, context_name | None,
                rows).
- PanelContext — one alive Spec Context Project (slug, name, repo_path, branch,
                 status).

WorkflowLauncher DI (T-016-P06)
---------------------------------
PanelService no longer calls subprocess.Popen or os.kill directly.
Instead, it delegates to an injected WorkflowLauncher
(core/protocols/workflow_launcher.py).  The production implementation
(infrastructure/workflow_launcher_adapter.SubprocessWorkflowLauncher) lives in
the infrastructure layer where subprocess use is permitted.

PID state is persisted via an optional JsonWorkflowStateStore so that the
running-workflow registry survives panel restarts.  When no state store is
injected, state is kept in-memory only (backward-compatible default for tests).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.server_registry import PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.models.workflow import WorkflowSummaryDTO
from dadaia_workspace.core.protocols.context_project_provider import ContextProjectProvider
from dadaia_workspace.core.protocols.server_registry_provider import ServerRegistryProvider
from dadaia_workspace.core.protocols.workflow_launcher import WorkflowLauncher
from dadaia_workspace.core.protocols.workflow_provider import WorkflowProvider
from dadaia_workspace.features.agents.reader import AgentDTO, read_canonical_agents


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


@dataclass
class PanelContext:
    """One active Spec Context Project as seen by the panel.

    branch — consumed as-is from SpecContextService (cached at last activate/show).
             No git subprocess is invoked per request (R4 trade-off).
             The rendering layer displays "(unknown)" when branch is None.
    """

    slug: str
    name: str
    repo_path: Path
    branch: str | None
    status: str


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
    workflow_launcher:
        Optional WorkflowLauncher instance (injected, T-016-P06).
        When None, a SubprocessWorkflowLauncher is built lazily on first use.
    workflow_state_store:
        Optional state store for persisting running-workflow PIDs.
        When None, state is kept in-memory only (survives current process only).
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
        workflow_launcher: WorkflowLauncher | None = None,
        workflow_state_store: Any = None,
        workflows_service: WorkflowProvider | None = None,
        report_retention: Any = None,
        adapter_registry: dict[str, Any] | None = None,
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
        workflow_launcher:
            WorkflowLauncher protocol implementation (T-016-P06).
            When None, a SubprocessWorkflowLauncher is created on first use.
        workflow_state_store:
            State store for persisted PID tracking.
            When None, an in-memory dict is used (state lost on restart).
        workflows_service:
            WorkflowProvider instance (injected via DI, T-017-06/07).
            When None, a WorkflowsService is constructed lazily from
            workspace_root on first use (backward-compatible for callers
            that do not pass this parameter).
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
        # workflows_service is injected; fallback to lazy construction preserves
        # backward compatibility (T-017-06: no self-construction in __init__).
        self._workflows_service: WorkflowProvider | None = workflows_service
        self._workflow_launcher = workflow_launcher
        self._workflow_state_store = workflow_state_store
        # In-memory fallback when no persistent state store is injected.
        self._running_workflows: dict[str, int] = {}
        # AR-03: injected dependencies for report retention and adapter registry.
        self._report_retention = report_retention
        self._adapter_registry: dict[str, Any] = (
            adapter_registry if adapter_registry is not None else {}
        )

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
            )
            for ctx in self._active_contexts()
        ]

    def list_workflow_summaries(self) -> list[WorkflowSummaryDTO]:
        """Return card summaries for all canonical workflow files.

        Delegates to WorkflowsService.list_summaries(). Returns an empty list
        when no workflows directory is found.

        For testing, inject a fake WorkflowsService via the constructor's
        ``workflows_service`` parameter (T-017-06).  The legacy
        ``_workflows_service_override`` attribute escape-hatch is still honoured
        for backward compatibility with existing tests.
        """
        override = getattr(self, "_workflows_service_override", None)
        svc = override if override is not None else self._workflows_svc()
        return svc.list_summaries()

    def list_canonical_agents(self) -> list[AgentDTO]:
        """Return the canonical agent catalog.

        Resolution order (delegated to read_canonical_agents):
          1. $DADAIA_AGENTS_DIR env var
          2. <workspace_root>/.dadaia/agentic/agents/
          3. <workspace_root>/.claude/agents/

        For testing, ``_canonical_agents_override`` may be set on the instance
        to bypass the filesystem read and return a controlled list directly.
        """
        override = getattr(self, "_canonical_agents_override", None)
        if override is not None:
            return list(override)
        return read_canonical_agents(self._workspace_root)

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

    def run_workflow(self, workflow_name: str) -> dict[str, object]:
        """Spawn ``dadaia orchestrate <workflow_name>`` in the background.

        Delegates subprocess launch to the injected WorkflowLauncher
        (T-016-P06 — no subprocess.Popen in the features layer).

        State is persisted via the injected workflow_state_store so that the
        running-workflow registry survives panel restarts.

        Raises RuntimeError with "not found" if the workflow doesn't exist,
        or "already running" if a tracked PID is still alive.
        Returns {"pid": int, "workflow": str} on success.
        """
        override = getattr(self, "_workflows_service_override", None)
        svc = override if override is not None else self._workflows_svc()
        known = {s.name for s in svc.list_summaries()}
        if workflow_name not in known:
            raise RuntimeError(f"workflow not found: {workflow_name!r}")

        # Load persisted state if a store is available, otherwise use in-memory.
        running = self._load_running()
        existing_pid = running.get(workflow_name)
        if existing_pid is not None:
            if self._launcher().is_alive(existing_pid):
                raise RuntimeError(f"already running: {workflow_name!r} (PID {existing_pid})")
            # PID is dead — evict stale entry.
            del running[workflow_name]
            self._persist_running(running)

        pid = self._launcher().launch(
            workflow_name,
            str(self._workspace_root),
            python_executable=sys.executable,
        )
        running[workflow_name] = pid
        self._persist_running(running)
        return {"pid": pid, "workflow": workflow_name}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _workflows_svc(self) -> WorkflowProvider:
        """Return the injected WorkflowProvider.

        T-017-06: WorkflowsService is injected through the constructor.
        T-017-07: the concrete class is no longer imported here; the composition root
        (container.py) always injects a concrete WorkflowsService.  Callers that do not
        inject a WorkflowProvider receive a clear error rather than a hidden construction.
        """
        if self._workflows_service is None:
            raise RuntimeError(
                "PanelService requires a WorkflowProvider to be injected via "
                "'workflows_service'. The composition root (container.py) always "
                "provides one; pass a fake for tests."
            )
        return self._workflows_service

    def _launcher(self) -> WorkflowLauncher:
        """Return the injected launcher, or build a SubprocessWorkflowLauncher lazily."""
        if self._workflow_launcher is not None:
            return self._workflow_launcher
        # Lazy import to avoid a hard dependency at module level.
        from dadaia_workspace.infrastructure.workflow_launcher_adapter import (
            SubprocessWorkflowLauncher,
        )

        launcher = SubprocessWorkflowLauncher()
        self._workflow_launcher = launcher
        return launcher

    def _load_running(self) -> dict[str, int]:
        """Return the current running-workflow PID map."""
        if self._workflow_state_store is not None:
            loaded: dict[str, int] = self._workflow_state_store.load()
            return loaded
        return dict(self._running_workflows)

    def _persist_running(self, state: dict[str, int]) -> None:
        """Persist *state* back to the store and update the in-memory dict."""
        if self._workflow_state_store is not None:
            self._workflow_state_store.save(state)
        else:
            self._running_workflows = dict(state)

    def _active_contexts(self) -> list[SpecContextProject]:
        """Return contexts with state == alive."""
        return [ctx for ctx in self._spec_context.list_all() if ctx.state == ContextState.ALIVE]
