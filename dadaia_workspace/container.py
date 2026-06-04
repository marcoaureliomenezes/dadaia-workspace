"""Composition root — builds services with concrete infrastructure."""

from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.exceptions import (
    NoActiveReleaseError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.protocols.agent_dispatcher import AgentDispatcher
from dadaia_workspace.core.protocols.process_probe import OsProcessProbe
from dadaia_workspace.features.academy.service import AcademyService
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.features.orchestration.service import OrchestrationService
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api import (
    delete_report_file,
    mark_report_important,
    render_api_academy,
    render_api_agent_prompt,
    render_api_agents_canonical,
    render_api_contexts,
    render_api_reports,
    render_api_servers,
    render_api_session_detail,
    render_api_sessions,
    render_api_workflow_detail,
    render_api_workflow_run,
    render_api_workflows_list,
    render_health,
    serve_report_file,
    unmark_report_important,
)
from dadaia_workspace.features.panel.views.index import render_index
from dadaia_workspace.features.panel.views.kanban import render_api_kanban
from dadaia_workspace.features.panel.views.memory import render_memory
from dadaia_workspace.features.panel.views.static import render_static
from dadaia_workspace.features.panel.views.wrapper import render_memory_wrapper
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.reports_next.service import ReportsNextService
from dadaia_workspace.features.reports_retention.service import ReportRetentionService
from dadaia_workspace.features.reports_validation.service import ReportsValidationService
from dadaia_workspace.features.repos.service import ReposService
from dadaia_workspace.features.server_registry.service import ServerRegistryService
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.claude_agent_dispatcher import ClaudeAgentDispatcher
from dadaia_workspace.infrastructure.cli_agent_dispatcher import (
    CliAgentDispatcher,
    OpenCodeAgentDispatcher,
)
from dadaia_workspace.infrastructure.codex_agent_dispatcher import CodexAgentDispatcher
from dadaia_workspace.infrastructure.excel_reader import OpenpyxlExcelReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_course_store import JsonCourseStore
from dadaia_workspace.infrastructure.json_run_state_store import JsonRunStateStore
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore
from dadaia_workspace.infrastructure.markdown_workflow_store import MarkdownWorkflowStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from dadaia_workspace.infrastructure.stdlib_handoff_validator import StdlibHandoffValidator
from dadaia_workspace.core.specs_resolver import resolve_bound_context_name


def _states_dir(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "states"


def _guard_initialized(workspace_root: Path) -> None:
    marker = _states_dir(workspace_root) / "spec_contexts.json"
    if not marker.exists():
        raise WorkspaceNotInitializedError(
            f"Workspace not initialized at '{workspace_root}'. Run 'dadaia init' first."
        )


def build_workspace_service(workspace_root: Path) -> WorkspaceService:
    return WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    )


def build_spec_context_service(workspace_root: Path) -> SpecContextService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return SpecContextService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
    )


def build_public_service() -> PublicAssetService:
    return PublicAssetService(public_assets=FileSystemPublicAssetManager())


def build_repos_service() -> ReposService:
    return ReposService(excel_reader=OpenpyxlExcelReader())


def build_doctor_service(workspace_root: Path) -> DoctorService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return DoctorService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
    )


def build_academy_service(workspace_root: Path) -> AcademyService:
    _guard_initialized(workspace_root)
    academy_dir = workspace_root / ".dadaia" / "academy"
    return AcademyService(
        course_store=JsonCourseStore(academy_dir),
        workspace_root=workspace_root,
    )


def build_export_service(workspace_root: Path) -> ExportService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return ExportService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
    )


def _select_dispatcher(runtime: str | None) -> AgentDispatcher:
    import os

    runtime = (runtime or os.environ.get("DADAIA_AGENT_RUNTIME") or "cli").lower()
    if runtime == "claude":
        return ClaudeAgentDispatcher()
    if runtime == "opencode":
        return OpenCodeAgentDispatcher()
    if runtime == "codex":
        return CodexAgentDispatcher()
    return CliAgentDispatcher()


def _agent_catalog(workspace_root: Path) -> tuple[str, ...]:
    agents_dir = workspace_root / ".dadaia" / "agentic" / "agents"
    if not agents_dir.exists():
        return ()
    return tuple(sorted(p.stem for p in agents_dir.glob("*.md")))


def build_orchestration_service(
    workspace_root: Path, runtime: str | None = None
) -> OrchestrationService:
    _guard_initialized(workspace_root)
    workflows_dir = workspace_root / ".dadaia" / "agentic" / "workflows"
    runs_dir = workspace_root / ".dadaia" / "runs"
    return OrchestrationService(
        workflow_store=MarkdownWorkflowStore(
            workflows_dir, agent_catalog=_agent_catalog(workspace_root)
        ),
        run_state_store=JsonRunStateStore(runs_dir),
        dispatcher=_select_dispatcher(runtime),
        workspace_root=workspace_root,
    )


def build_server_registry_service(workspace_root: Path) -> ServerRegistryService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return ServerRegistryService(
        store=JsonServerRegistryStore(states),
        probe=OsProcessProbe(),
    )


def build_panel_service(
    workspace_root: Path,
    telemetry: object | None = None,
    academy: object | None = None,
) -> PanelService:
    return PanelService(
        registry=build_server_registry_service(workspace_root),
        spec_context=build_spec_context_service(workspace_root),
        workspace_root=workspace_root,
        telemetry=telemetry,
        academy=academy,
    )


def build_reports_validation_service(workspace_root: Path) -> ReportsValidationService:
    """Compose ``ReportsValidationService`` with ``StdlibHandoffValidator``.

    Schema is read from the staged location:
    ``workspace_root/.dadaia/agentic/schemas/handoff-v1.schema.json``.
    Handoff root is ``workspace_root/.dadaia/handoff``.

    Args:
        workspace_root: Root directory of the initialized dadaia workspace.

    Returns:
        A fully wired ``ReportsValidationService`` instance.
    """
    schema_path = workspace_root / ".dadaia" / "agentic" / "schemas" / "handoff-v1.schema.json"
    reports_root = workspace_root / ".dadaia" / "handoff"
    validator = StdlibHandoffValidator(schema_path)
    return ReportsValidationService(validator=validator, reports_root=reports_root)


def build_reports_next_service(
    workspace_root: Path, context: str | None = None
) -> ReportsNextService:
    """Compose ``ReportsNextService`` for the active (or explicitly named) context.

    Context resolution (FR-RN-1): when *context* is given, specs live at
    ``repos/<context>/specs``; otherwise the bound context session is used. The
    reports tree is keyed by the context name under ``<workspace>/.dadaia/reports``.

    Args:
        workspace_root: Root directory of the initialized dadaia workspace.
        context: Optional explicit context name (overrides primary-context resolution).

    Raises:
        NoActiveReleaseError: No explicit context and no primary context is set.
    """
    _guard_initialized(workspace_root)
    reports_root = workspace_root / ".dadaia" / "handoff"
    context_name = resolve_bound_context_name(context)
    if not context_name:
        raise NoActiveReleaseError(
            "No bound context. Run `eval $(dadaia context bind <name> --mode read)` "
            "or pass --context <name>."
        )
    specs_dir = workspace_root / "repos" / context_name / "specs"
    return ReportsNextService(
        specs_dir=specs_dir, reports_root=reports_root, context_name=context_name
    )


def build_reports_retention_service(workspace_root: Path) -> ReportRetentionService:
    """Compose ``ReportRetentionService`` for workspace runtime report state."""
    _guard_initialized(workspace_root)
    return ReportRetentionService(workspace_root)


def build_panel_views(
    workspace_root: Path,
    telemetry: object | None = None,
) -> dict[str, Callable[..., tuple[int, str, bytes]]]:
    """Compose all panel view callables for injection into make_handler_class().

    Returns a dict mapping route names to view callables as required by
    ``features/panel/handler.py::make_handler_class(views)``.

    Parameters
    ----------
    workspace_root:
        Absolute path to the workspace root directory.
    telemetry:
        Optional TelemetryService instance.  When provided, it is injected
        into PanelService so that ``render_api_agents_canonical`` can overlay
        telemetry data on the canonical agent catalog (PR3-08).
    """
    academy = build_academy_service(workspace_root)
    service = build_panel_service(workspace_root, telemetry=telemetry, academy=academy)
    # WorkflowsService is exposed via PanelService._workflows_service for the
    # detail endpoint (get_detail needs name resolution against the filesystem).
    return {
        "index": render_index(service),
        "api_panel_status": render_api_servers(service),
        "health": render_health(),
        "api_contexts": render_api_contexts(service),
        "api_kanban": render_api_kanban(workspace_root),
        "api_academy": render_api_academy(service),
        "api_reports": render_api_reports(service),
        "reports_serve": serve_report_file(service),
        "api_report_delete": delete_report_file(service),
        "api_report_mark_important": mark_report_important(service),
        "api_report_unmark_important": unmark_report_important(service),
        "api_agents": render_api_agents_canonical(service),
        "api_agent_prompt": render_api_agent_prompt(service),
        "api_workflows": render_api_workflows_list(service),
        "api_workflow_detail": render_api_workflow_detail(service._workflows_service),
        "api_workflow_run": render_api_workflow_run(service),
        "api_sessions": render_api_sessions(service),
        "api_session_detail": render_api_session_detail(service),
        "memory": render_memory(workspace_root),
        "memory_view": render_memory_wrapper(workspace_root),
        "static": render_static(),
    }
