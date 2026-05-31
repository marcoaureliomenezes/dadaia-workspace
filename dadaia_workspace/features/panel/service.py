"""PanelService — read-only orchestrator for the Dadaia Workspace Panel.

Responsibilities
----------------
- Fan out to ServerRegistryService and SpecContextService (injected via DI).
- Group server registry entries by project against active contexts using
  best-effort case-insensitive matching (D1.A from architect report).
- Expose active Spec Context Projects as PanelContext dataclasses, including
  the cached current_branch field from SpecContextService (R4: no git subprocess
  per request — potential staleness is accepted for Release-1; see PLAN risks R4).
- Expose the canonical agent catalog via list_canonical_agents() (PR3-08).

Dataclasses
-----------
- ServerRow   — one row in the server table (port, project, url, status, pid,
                expires_at, description).
- ServerGroup — a named group of ServerRows (group_label, context_name | None,
                rows).
- PanelContext — one active Spec Context Project (slug, name, repo_path, branch,
                 is_primary).
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.server_registry import PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.agents.reader import AgentDTO, read_canonical_agents
from dadaia_workspace.features.server_registry.service import ServerRegistryService
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.features.workflows.service import WorkflowsService, WorkflowSummaryDTO


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
    is_primary: bool


class PanelService:
    """Read-only orchestrator for the panel data model.

    Parameters
    ----------
    registry:
        A ServerRegistryService instance (injected).
    spec_context:
        A SpecContextService instance (injected).
    workspace_root:
        Absolute path to the workspace root directory.  Used to construct
        repo_path in PanelContext without reaching into SpecContextService
        private attributes.
    """

    def __init__(
        self,
        registry: ServerRegistryService,
        spec_context: SpecContextService,
        workspace_root: Path,
        telemetry: Any = None,
        academy: Any = None,
    ) -> None:
        """Initialise PanelService.

        Parameters
        ----------
        registry:
            A ServerRegistryService instance (injected).
        spec_context:
            A SpecContextService instance (injected).
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
        """
        self._registry = registry
        self._spec_context = spec_context
        self._workspace_root = workspace_root
        self.telemetry = telemetry
        self.academy = academy
        self._workflows_service = WorkflowsService(workspace_root)
        self._running_workflows: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
                is_primary=False,
            )
            for ctx in self._active_contexts()
        ]

    def list_workflow_summaries(self) -> list[WorkflowSummaryDTO]:
        """Return card summaries for all canonical workflow files.

        Delegates to WorkflowsService.list_summaries(). Returns an empty list
        when no workflows directory is found.

        For testing, ``_workflows_service_override`` may be set on the instance
        to bypass the real service and return a controlled result.
        """
        override = getattr(self, "_workflows_service_override", None)
        svc = override if override is not None else self._workflows_service
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

    def run_workflow(self, workflow_name: str) -> dict[str, object]:
        """Spawn `dadaia orchestrate <workflow_name>` in the background.

        Raises RuntimeError with "not found" if the workflow doesn't exist,
        or "already running" if a tracked PID is still alive.
        Returns {"pid": int, "workflow": str} on success.
        """
        override = getattr(self, "_workflows_service_override", None)
        svc = override if override is not None else self._workflows_service
        known = {s.name for s in svc.list_summaries()}
        if workflow_name not in known:
            raise RuntimeError(f"workflow not found: {workflow_name!r}")

        existing_pid = self._running_workflows.get(workflow_name)
        if existing_pid is not None:
            try:
                os.kill(existing_pid, 0)
                raise RuntimeError(f"already running: {workflow_name!r} (PID {existing_pid})")
            except ProcessLookupError:
                del self._running_workflows[workflow_name]

        proc = subprocess.Popen(
            [sys.executable, "-m", "dadaia_workspace", "orchestrate", workflow_name],
            cwd=str(self._workspace_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._running_workflows[workflow_name] = proc.pid
        return {"pid": proc.pid, "workflow": workflow_name}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _active_contexts(self) -> list[SpecContextProject]:
        """Return contexts with state == alive."""
        return [ctx for ctx in self._spec_context.list_all() if ctx.state == ContextState.ALIVE]
