"""Composition root — builds services with concrete infrastructure."""

from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.protocols.agent_dispatcher import AgentDispatcher
from dadaia_workspace.features.academy.service import AcademyService
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.features.orchestration.service import OrchestrationService
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.repos.service import ReposService
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.claude_agent_dispatcher import ClaudeAgentDispatcher
from dadaia_workspace.infrastructure.cli_agent_dispatcher import (
    CliAgentDispatcher,
    CodexAgentDispatcher,
    OpenCodeAgentDispatcher,
)
from dadaia_workspace.infrastructure.excel_reader import OpenpyxlExcelReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_course_store import JsonCourseStore
from dadaia_workspace.infrastructure.json_primary_context_store import JsonPrimaryContextStore
from dadaia_workspace.infrastructure.json_run_state_store import JsonRunStateStore
from dadaia_workspace.infrastructure.markdown_workflow_store import MarkdownWorkflowStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager


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
        primary_store=JsonPrimaryContextStore(states),
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
        primary_store=JsonPrimaryContextStore(states),
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
