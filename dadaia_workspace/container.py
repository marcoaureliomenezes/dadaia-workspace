"""Composition root — builds services with concrete infrastructure."""

import datetime as dt
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dadaia_workspace.core.models.workflow_execution import WorkflowPolicySnapshot
    from dadaia_workspace.features.backlog.removal_lifecycle import (
        BacklogRemovalLifecycle,
    )
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowCatalog,
        WorkflowExecutionPolicyResolver,
    )
    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
        BacklogDefinitionWorkflow,
    )
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )
    from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
        JsonWorkflowModelPolicyStore,
    )

from dadaia_workspace.core.exceptions import (
    NoActiveReleaseError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.harness_models import HarnessModelOption
from dadaia_workspace.core.models.hygiene import SlopPolicy
from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.core.protocols.process_ancestry import ProcessAncestry
from dadaia_workspace.core.specs_resolver import resolve_bound_context_name
from dadaia_workspace.features.academy.service import AcademyService
from dadaia_workspace.features.agents.reader import FileSystemAgentsProvider
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.features.lifecycle.antislop.retention import RetentionSweep
from dadaia_workspace.features.lifecycle.antislop.slop_scan import SlopReport, slop_scan
from dadaia_workspace.features.lifecycle.hygiene import LifecycleHygieneService
from dadaia_workspace.features.lifecycle.phase_workflow import LifecyclePhaseWorkflow
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline
from dadaia_workspace.features.lifecycle.prompt_builder import PromptPrefix
from dadaia_workspace.features.lifecycle.report_workflow import LifecycleReportWorkflow
from dadaia_workspace.features.lifecycle.service import LifecyclePreflightService
from dadaia_workspace.features.orchestration.service import OrchestrationService
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.academy import render_academy_lesson
from dadaia_workspace.features.panel.views.api import (
    delete_report_file,
    mark_report_important,
    render_api_academy,
    render_api_agent_prompt,
    render_api_agents_canonical,
    render_api_contexts,
    render_api_dadaia_workflow_detail,
    render_api_dadaia_workflows_list,
    render_api_reports,
    render_api_servers,
    render_api_session_detail,
    render_api_sessions,
    render_api_workflow_detail,
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
from dadaia_workspace.features.telemetry.aggregator.runtimes import ADAPTER_REGISTRY
from dadaia_workspace.features.workflows.service import WorkflowsService
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.excel_reader import OpenpyxlExcelReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_course_store import JsonCourseStore
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.json_run_state_store import JsonRunStateStore
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore
from dadaia_workspace.infrastructure.json_workflow_state_store import JsonWorkflowStateStore
from dadaia_workspace.infrastructure.markdown_workflow_store import MarkdownWorkflowStore
from dadaia_workspace.infrastructure.process_ancestry_adapter import (
    LinuxProcAncestry,
    PsProcessAncestry,
    WindowsToolhelpAncestry,
)
from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter
from dadaia_workspace.infrastructure.stdlib_handoff_validator import StdlibHandoffValidator
from dadaia_workspace.infrastructure.workflow_launcher_adapter import SubprocessWorkflowLauncher


def _build_permission_setter() -> Any:
    """Return the appropriate FilePermissionSetter for the current platform.

    Reads ``PLATFORM.has_posix_chmod`` (the sole authorized platform capability
    flag) and returns the POSIX adapter on platforms with effective chmod, or the
    Windows ``icacls`` adapter otherwise.  The import is lazy so that importing
    ``container`` never triggers the Windows module's guard on Linux/macOS.

    Returns:
        ``PosixFilePermissionSetter`` when ``PLATFORM.has_posix_chmod`` is ``True``,
        or ``WindowsFilePermissionSetter`` when ``False``.
    """
    from dadaia_workspace.core.platform import PLATFORM

    if PLATFORM.has_posix_chmod:
        from dadaia_workspace.infrastructure.file_permission_posix import (
            PosixFilePermissionSetter,
        )

        return PosixFilePermissionSetter()
    from dadaia_workspace.infrastructure.file_permission_windows import (
        WindowsFilePermissionSetter,
    )

    return WindowsFilePermissionSetter()


def _select_lock_adapter() -> Any:
    """Return the appropriate file-lock adapter module for the current platform.

    Reads ``PLATFORM.has_fcntl`` (the sole authorized platform capability flag)
    and returns the POSIX adapter on platforms that provide ``fcntl``, or the
    Windows adapter otherwise.  The import is lazy so that importing
    ``container`` never triggers the Windows module's guard on Linux/macOS.

    Returns:
        The adapter module: ``infrastructure.file_lock_posix`` when
        ``PLATFORM.has_fcntl`` is ``True``, or
        ``infrastructure.file_lock_windows`` when ``False``.
    """
    from dadaia_workspace.core.platform import PLATFORM

    if PLATFORM.has_fcntl:
        import dadaia_workspace.infrastructure.file_lock_posix as _adapter
    else:
        import dadaia_workspace.infrastructure.file_lock_windows as _adapter  # type: ignore[no-redef]
    return _adapter


def build_shutdown_handler() -> Any:
    """Return the appropriate ShutdownHandler for the current platform.

    Reads ``PLATFORM.has_sigterm`` (the sole authorized platform capability flag)
    and returns the POSIX adapter on platforms with effective SIGTERM support
    (Linux, macOS), or the Windows adapter on platforms without it.  The import
    is lazy so that importing ``container`` never triggers the Windows module's
    guard on Linux/macOS.

    Returns:
        ``PosixSignalShutdownHandler`` on Linux / macOS (SIGTERM + SIGINT),
        or ``WindowsSignalShutdownHandler`` on Windows (SIGINT only).
    """
    from dadaia_workspace.core.platform import PLATFORM

    if not PLATFORM.has_sigterm:
        from dadaia_workspace.infrastructure.signal_shutdown_windows import (
            WindowsSignalShutdownHandler,
        )

        return WindowsSignalShutdownHandler()
    from dadaia_workspace.infrastructure.signal_shutdown_posix import (
        PosixSignalShutdownHandler,
    )

    return PosixSignalShutdownHandler()


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


def _build_pid_probe() -> Callable[[int], bool] | None:
    """Composition-root PID-liveness probe wiring for the DoctorService LOCK-GC sweep.

    The container is the composition root: it may reach into the hook layer's canonical
    probe builder (``hooks/sdd_gate._build_pid_probe``, which wires the container's
    ``OsProcessProbe``) and inject the resulting ``(pid) -> alive?`` callable into the
    ``DoctorService``. Without it, ``dadaia doctor --fix`` runs LOCK-GC TTL-only and would
    reclaim a TTL-expired lease whose holder pid is STILL ALIVE — violating the no-steal
    invariant (FR-W1-02: a live-pid holder is NEVER reclaimed). This mirrors the
    ``SpecsDoctor`` seam in ``cli/commands/specs.py``: ``features/spec_context/doctor.py``
    never imports the infrastructure adapter. Any failure ⇒ ``None`` ⇒ TTL-only liveness
    (Windows-safe / legacy-record-safe), exactly as the gate degrades.
    """
    try:
        from dadaia_workspace.hooks.sdd_gate import _build_pid_probe as _hook_build_probe

        return _hook_build_probe()
    except Exception:  # noqa: BLE001 — probe wiring must never break `dadaia doctor`.
        return None


def build_process_ancestry() -> ProcessAncestry:
    """Composition-root selection of the read-only ``ProcessAncestry`` adapter (T-014-06).

    Platform is decided here via the ``PLATFORM`` seam — never by an in-adapter
    ``sys.platform`` branch:

    * ``has_proc_fs`` (Linux) → ``LinuxProcAncestry`` (``/proc`` PPID walk).
    * else ``has_os_kill_liveness`` (other POSIX, incl. macOS) → ``PsProcessAncestry``
      (``ps -o ppid=`` via the injected ``SubprocessProcessRunner``).
    * else (Windows) → ``WindowsToolhelpAncestry`` (read-only Toolhelp32 snapshot).

    Every adapter is non-destructive and returns ``Ancestry.UNKNOWN`` for any
    indeterminate case; the ALLOW+WARN policy decision lives in the chokepoint caller.
    """
    from dadaia_workspace.core.platform import PLATFORM
    from dadaia_workspace.infrastructure.subprocess_runner import SubprocessProcessRunner

    if PLATFORM.has_proc_fs:
        return LinuxProcAncestry()
    if PLATFORM.has_os_kill_liveness:
        return PsProcessAncestry(SubprocessProcessRunner())
    return WindowsToolhelpAncestry()


def _build_alive_contexts_provider(
    workspace_root: Path,
) -> Callable[[], list[tuple[str, str]]]:
    """Composition-root provider of ALIVE Spec Contexts for the Kanban view (kanban-v2).

    Returns a callable yielding ``(context_name, repo_slug)`` for every ALIVE context in
    the registry, so the Kanban board's swimlanes are the live-project set (not "whatever
    has session files"). ``features/panel/views/kanban.py`` never imports the context
    store adapter — the container injects this callable, mirroring the ``pid_probe`` seam.
    Fail-soft: any registry error ⇒ empty list (the view falls back to session-derived
    lanes only).
    """
    from dadaia_workspace.core.models.spec_context import ContextState

    def _provider() -> list[tuple[str, str]]:
        try:
            store = JsonContextStore(_states_dir(workspace_root))
            return [
                (ctx.name, ctx.repo_slug)
                for ctx in store.list_all()
                if ctx.state == ContextState.ALIVE
            ]
        except Exception:  # noqa: BLE001 — registry read must never break the panel.
            return []

    return _provider


def build_doctor_service(workspace_root: Path) -> DoctorService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return DoctorService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        pid_probe=_build_pid_probe(),
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


def build_agent_runtime(
    kind: AgentRuntimeKind,
    *,
    cwd: Path | None = None,
    model: HarnessModelOption | None = None,
) -> AgentRuntimePort:
    """Map an ``AgentRuntimeKind`` to its concrete adapter behind ``AgentRuntimePort``.

    This is the single seam that binds a runtime kind to an infrastructure adapter —
    the runtime-adapter analogue of ``PLATFORM`` selecting OS adapters. ``core/`` and
    ``features/`` stay provider-agnostic and never import an adapter directly; a
    lifecycle workflow asks for the kind a step declares and injects the result into
    ``LifecycleAgentRunner``.

    ``model`` is the discrete Layer-2 model selection (LAW 2 / ADR-B) resolved from
    :mod:`core.harness_models` — a ``(model_id, effort)`` pair. When supplied it is
    threaded verbatim into the adapter config: PI passes ``pi --model <model_id>`` and
    Codex passes ``-m <model_id> -c model_reasoning_effort=<effort>``. When ``None``
    each adapter keeps its prior behaviour (PI omits ``--model``; Codex falls back to
    the registry tier view). ``model`` is inert for ``FAKE`` and ``CLAUDE_SDK`` (the
    latter is Layer-1 only — LAW 1).

    Codex (``codex exec``) and PI (``pi --mode json``) are live CLI-headless adapters,
    each carrying a real git-diff Ring-2 ``changed_paths`` boundary via the injected
    ``GitSubprocessClient``.
    The Claude SDK adapter body is real (Ring-1 write boundary via ``core/scope_match``);
    only its default ``query_fn`` transport is deferred (lazy ``claude-agent-sdk`` import).
    The factory is total over the enum: an unhandled kind raises ``ValueError``.
    """
    run_dir = cwd or Path.cwd()
    if kind is AgentRuntimeKind.FAKE:
        from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime

        return FakeAgentRuntime()
    if kind is AgentRuntimeKind.CODEX_EXEC:
        from dadaia_workspace.infrastructure.codex_runtime import (
            CodexExecAdapter,
            CodexExecConfig,
        )

        codex_config = (
            CodexExecConfig(cwd=run_dir, model=model.model_id, reasoning_effort=model.effort)
            if model is not None
            else CodexExecConfig(cwd=run_dir)
        )
        return CodexExecAdapter(codex_config, git=GitSubprocessClient())
    if kind is AgentRuntimeKind.CLAUDE_SDK:
        from dadaia_workspace.infrastructure.claude_sdk_runtime import ClaudeSdkAdapter

        return ClaudeSdkAdapter(cwd=run_dir)
    if kind is AgentRuntimeKind.PI_HEADLESS:
        from dadaia_workspace.infrastructure.pi_runtime import (
            PiHeadlessAdapter,
            PiHeadlessConfig,
        )

        pi_config = (
            PiHeadlessConfig(cwd=run_dir, model=model.model_id, reasoning_effort=model.effort)
            if model is not None
            else PiHeadlessConfig(cwd=run_dir)
        )
        return PiHeadlessAdapter(pi_config, git=GitSubprocessClient())
    raise ValueError(f"unsupported agent runtime kind: {kind!r}")


def _agent_catalog(workspace_root: Path) -> tuple[str, ...]:
    agents_dir = workspace_root / ".dadaia" / "agentic" / "agents"
    if not agents_dir.exists():
        return ()
    return tuple(sorted(p.stem for p in agents_dir.glob("*.md")))


def build_orchestration_service(
    workspace_root: Path, runtime: str | None = None
) -> OrchestrationService:
    """Compose the read-only orchestration catalog/run-status surface.

    Workflow execution moved to the lifecycle engine (WS-3); this service no longer
    takes a dispatcher. The ``runtime`` parameter is retained for CLI call-site
    compatibility (it is now inert — no agent runtime is selected here).
    """
    _guard_initialized(workspace_root)
    _ = runtime  # retained for CLI compatibility; no dispatcher is selected.
    workflows_dir = workspace_root / ".dadaia" / "agentic" / "workflows"
    runs_dir = workspace_root / ".dadaia" / "runs"
    return OrchestrationService(
        workflow_store=MarkdownWorkflowStore(
            workflows_dir, agent_catalog=_agent_catalog(workspace_root)
        ),
        run_state_store=JsonRunStateStore(runs_dir),
    )


def build_server_registry_service(workspace_root: Path) -> ServerRegistryService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return ServerRegistryService(
        store=JsonServerRegistryStore(states),
        probe=OsProcessProbe(),
    )


def build_workflow_catalog_service(workspace_root: Path) -> WorkflowsService:
    """Compose a ``WorkflowsService`` for the given workspace root."""
    return WorkflowsService(workspace_root)


def build_panel_service(
    workspace_root: Path,
    telemetry: object | None = None,
    academy: object | None = None,
) -> PanelService:
    states = _states_dir(workspace_root)
    return PanelService(
        registry=build_server_registry_service(workspace_root),
        spec_context=build_spec_context_service(workspace_root),
        workspace_root=workspace_root,
        telemetry=telemetry,
        academy=academy,
        workflow_launcher=SubprocessWorkflowLauncher(),
        workflow_state_store=JsonWorkflowStateStore(states),
        workflows_service=build_workflow_catalog_service(workspace_root),
        report_retention=ReportRetentionService(workspace_root),
        adapter_registry=dict(ADAPTER_REGISTRY),
        agents_provider=FileSystemAgentsProvider(),
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


def build_lifecycle_hygiene_service(workspace_root: Path) -> LifecycleHygieneService:
    """Compose lifecycle hygiene service."""
    _guard_initialized(workspace_root)
    return LifecycleHygieneService(workspace_root)


def build_slop_report(
    workspace_root: Path,
    *,
    now: dt.datetime | None = None,
    policy: SlopPolicy | None = None,
) -> SlopReport:
    """Run the read-only directory-aware anti-slop metric (WS-6).

    Pure measurement: walks the canonical swept ``.dadaia/`` zones and classifies each
    reporting unit (a directory tree counts as one entry with recursive size). Never
    mutates the filesystem. The clock is injectable for hermetic tests.
    """
    _guard_initialized(workspace_root)
    scan_now = now or dt.datetime.now(tz=dt.UTC)
    return slop_scan(workspace_root, now=scan_now, policy=policy or SlopPolicy())


def _live_lifecycle_claims(workspace_root: Path) -> Callable[[], frozenset[str]]:
    """Composition-root provider of swept-zone paths claimed by LIVE lifecycle runs (D6).

    The retention SWEEP must NEVER reclaim a tmp/handoff/report path that a live worker is
    mid-flight on. This callable reads the persisted ``LifecycleRun`` records and, for every
    NON-TERMINAL run (status not COMPLETED/FAILED), claims any of that run's
    ``expected_artifacts`` whose path falls inside a recognised swept zone
    (``.dadaia/{tmp,reports,handoff,runs}``). The deleter (``RetentionSweep``) spares any
    candidate equal to, nested under, or containing a claim.

    ``features/lifecycle/antislop/retention.py`` never imports the run-store adapter — the
    container injects this callable, mirroring the ``pid_probe`` seam. Fail-soft: any
    store/parse error ⇒ empty set (the sweep then relies on TTL + zone + escape guards
    alone, never reclaiming inside ``.dadaia/`` it cannot read).
    """
    from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus

    terminal = {LifecycleRunStatus.COMPLETED, LifecycleRunStatus.FAILED}
    swept_prefixes = tuple(f".dadaia/{zone}/" for zone in ("tmp", "reports", "handoff", "runs"))

    def _provider() -> frozenset[str]:
        store = build_lifecycle_run_store(workspace_root)
        run_dir = store.root
        if not run_dir.is_dir():
            return frozenset()
        claims: set[str] = set()
        for record in sorted(run_dir.glob("*.json")):
            try:
                run = store.load(record.stem)
            except Exception:  # noqa: BLE001 — a single bad record never breaks the sweep.
                continue
            if run is None or run.status in terminal:
                continue
            for artifact in run.expected_artifacts:
                ref = artifact.lstrip("/")
                if ref.startswith(swept_prefixes):
                    claims.add(ref)
        return frozenset(claims)

    return _provider


def build_retention_sweep(
    workspace_root: Path,
    *,
    now: dt.datetime | None = None,
    policy: SlopPolicy | None = None,
) -> RetentionSweep:
    """Compose the directory-aware retention SWEEP (D5) — the guarded deleter.

    Dry-run by default; deletes only when ``RetentionSweep.sweep(apply=True)`` is called
    explicitly. The live-claim provider (``_live_lifecycle_claims``) gates the destructive
    path against in-flight lifecycle runs (D6); the important-ref provider reuses
    ``LifecycleHygieneService`` so operator-marked reports and current-release evidence are
    spared. The clock is injectable for hermetic tests.
    """
    _guard_initialized(workspace_root)
    hygiene = LifecycleHygieneService(workspace_root)
    return RetentionSweep(
        workspace_root,
        now=now or dt.datetime.now(tz=dt.UTC),
        policy=policy or SlopPolicy(),
        live_claims=_live_lifecycle_claims(workspace_root),
        important_paths=hygiene.protected_refs,
    )


def build_lifecycle_preflight_service(workspace_root: Path) -> LifecyclePreflightService:
    """Compose lifecycle preflight service."""
    _guard_initialized(workspace_root)
    return LifecyclePreflightService()


def build_lifecycle_run_store(workspace_root: Path) -> JsonLifecycleRunStore:
    """Compose lifecycle run-state store."""
    _guard_initialized(workspace_root)
    return JsonLifecycleRunStore(workspace_root)


def build_workflow_model_profile_registry() -> "WorkflowCatalog":
    """Compose the governed workflow catalog the policy resolver reads (T-28-B-01).

    Wave B promotes :mod:`dadaia_workspace.features.workflows.dadaia_catalog` to **the**
    governed source: every worker step carries a default harness + a default model profile
    per supported harness (validated at import time against the built-in :mod:`model_profiles`
    registry). :func:`governed_workflow_catalog` projects that single source onto the
    resolver's :class:`WorkflowCatalog` seam, so the resolver and the panel read the *same*
    catalog (no second table). The function is pure (no I/O), so it takes no ``workspace_root``.
    """
    from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog

    return governed_workflow_catalog()


def build_workflow_model_policy_store(workspace_root: Path) -> "JsonWorkflowModelPolicyStore":
    """Compose the workflow-model-policy overlay store (T-28-A-08).

    Reads/writes ``.dadaia/states/workflow_model_policy.json`` with atomic temp+rename and
    a ``.last-good.json`` backup. ``load()`` returns ``None`` on a missing file (defaults);
    a present-but-invalid file raises (missing != invalid).
    """
    from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
        JsonWorkflowModelPolicyStore,
    )

    _guard_initialized(workspace_root)
    return JsonWorkflowModelPolicyStore(workspace_root)


def build_workflow_policy_resolver(
    workspace_root: Path,
    *,
    context: str = "default",
) -> "WorkflowExecutionPolicyResolver":
    """Compose the single shared :class:`WorkflowExecutionPolicyResolver` (T-28-A-08).

    Loads the overlay from the policy store (missing ⇒ ``None`` ⇒ library defaults; an
    invalid overlay raises here, before any model call — LAW 4/5) and binds it to the
    governed catalog. CLI and panel both consume *this* resolver so they never disagree on
    which model a step runs. ``context`` is reserved for future per-context overlays; only
    the ``default`` context is honored this release (D-2).
    """
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowExecutionPolicyResolver,
    )

    _guard_initialized(workspace_root)
    _ = context  # reserved (D-2: only `default` honored); recorded for call-site clarity.
    overlay = build_workflow_model_policy_store(workspace_root).load()
    return WorkflowExecutionPolicyResolver(
        catalog=build_workflow_model_profile_registry(),
        overlay=overlay,
    )


def build_lifecycle_report_workflow(workspace_root: Path) -> LifecycleReportWorkflow:
    """Compose lifecycle report workflow."""
    _guard_initialized(workspace_root)
    return LifecycleReportWorkflow(
        workspace_root=workspace_root,
        runtime_files=FilesystemRuntimeFileAdapter(workspace_root),
        hygiene=LifecycleHygieneService(workspace_root),
        validation=build_reports_validation_service(workspace_root),
    )


def build_lifecycle_phase_workflow(
    workspace_root: Path,
    *,
    runtime_kind: AgentRuntimeKind,
    cwd: Path | None = None,
    model: HarnessModelOption | None = None,
) -> LifecyclePhaseWorkflow:
    """Compose the single-step lifecycle phase workflow on a selected harness.

    Binds the per-step runtime adapter (via :func:`build_agent_runtime`) to the
    persistent run store. The chosen ``runtime_kind`` is what makes the harness
    selectable per verb invocation; ``model`` is the discrete Layer-2 model (LAW 2)
    threaded into the adapter when supplied. The caller passes a resolved
    ``policy_snapshot`` to ``LifecyclePhaseWorkflow.run`` (composed via
    :func:`build_workflow_policy_resolver`) — the workflow itself never parses policy JSON.
    """
    _guard_initialized(workspace_root)
    return LifecyclePhaseWorkflow(
        runtime=build_agent_runtime(runtime_kind, cwd=cwd or workspace_root, model=model),
        run_store=build_lifecycle_run_store(workspace_root),
    )


def build_lifecycle_pipeline(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    prefix: PromptPrefix | None = None,
    cwd: Path | None = None,
    models: dict[AgentRuntimeKind, HarnessModelOption] | None = None,
    policy_snapshot: "WorkflowPolicySnapshot | None" = None,
) -> LifecyclePipeline:
    """Compose the multi-step lifecycle pipeline with a per-step harness factory.

    The injected ``runtime_factory`` resolves each step's declared ``AgentRuntimeKind`` to
    its adapter, so a single run can mix harnesses across steps (pi implements, codex
    reviews, ...). ``models`` maps a runtime kind to its discrete Layer-2 model (LAW 2),
    so a step running on a given harness gets that harness's selected ``(id, effort)``.
    An optional cacheable ``prefix`` (WS-7) is assembled once and reused verbatim by
    every step. ``policy_snapshot`` is the resolved governance snapshot (T-28-A-08, from
    :func:`build_workflow_policy_resolver`); when present it is frozen onto the run before
    the first step (LAW 7) — an overlay mutated after start cannot change the in-flight run.
    """
    _guard_initialized(workspace_root)
    run_cwd = cwd or workspace_root
    model_by_kind = models or {}
    return LifecyclePipeline(
        context=context,
        release_id=release_id,
        run_store=build_lifecycle_run_store(workspace_root),
        runtime_factory=lambda kind: build_agent_runtime(
            kind, cwd=run_cwd, model=model_by_kind.get(kind)
        ),
        prefix=prefix,
        policy_snapshot=policy_snapshot,
    )


def _release_definition_runtime_factory(
    *,
    context: str,
    run_cwd: Path,
    model_by_kind: dict[AgentRuntimeKind, HarnessModelOption],
) -> Callable[[AgentRuntimeKind], AgentRuntimePort]:
    """Build the per-step runtime factory for the release-definition workflow.

    Real harnesses (pi/codex/claude) resolve to their live adapters. ``FAKE`` resolves
    to a *driving* fake that returns an APPROVED handoff with an in-scope artifact_ref —
    so ``--harness fake`` walks the whole §6.1 sequence deterministically (the DoD
    requirement), exercising every fragment-assembled prompt and Python gate without a
    live worker. The artifact_ref stays inside the step's allowed handoff path.
    """
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunResult,
        AgentRunStatus,
    )
    from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime

    approving = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake release-definition worker: APPROVED",
        artifact_refs=(f".dadaia/handoff/{context}/release-definition-step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )

    def factory(kind: AgentRuntimeKind) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            return FakeAgentRuntime(result=approving)
        return build_agent_runtime(kind, cwd=run_cwd, model=model_by_kind.get(kind))

    return factory


def build_release_definition_workflow(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    default_runtime_kind: AgentRuntimeKind = AgentRuntimeKind.FAKE,
    prefix: PromptPrefix | None = None,
    cwd: Path | None = None,
    models: dict[AgentRuntimeKind, HarnessModelOption] | None = None,
) -> "ReleaseDefinitionWorkflow":
    """Compose the fragment-driven release-definition workflow (WS-5 / §6.1).

    The workflow runs the §6.1 step sequence with fragment-assembled, scoped prompts and
    Python-owned gates (no generic ``"Run the step"`` suffix). The injected runtime
    factory resolves each step's ``AgentRuntimeKind`` to its adapter so harnesses can be
    mixed per step; ``FAKE`` drives the sequence end-to-end. ``models`` maps a runtime
    kind to its discrete Layer-2 model (LAW 2). The :class:`ContextSelector` resolves
    each fragment's dynamic inputs, bounded by the fragment's ``max_context_policy``.
    """
    from dadaia_workspace.features.lifecycle.context_selector import (
        ContextSelector,
        SpecContext,
    )
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )

    _guard_initialized(workspace_root)
    run_cwd = cwd or workspace_root
    model_by_kind = models or {}
    context_name = resolve_bound_context_name(context) or context
    specs_dir = workspace_root / "repos" / context_name / "specs"
    if not specs_dir.is_dir():
        # Self-hosting library repo: specs live at the workspace-root tree.
        specs_dir = workspace_root / "specs"
    handoff_dir = workspace_root / ".dadaia" / "handoff" / context_name
    selector = ContextSelector(
        SpecContext(specs_dir=specs_dir, release_id=release_id, handoff_dir=handoff_dir)
    )
    return ReleaseDefinitionWorkflow(
        context=context,
        release_id=release_id,
        run_store=build_lifecycle_run_store(workspace_root),
        runtime_factory=_release_definition_runtime_factory(
            context=context, run_cwd=run_cwd, model_by_kind=model_by_kind
        ),
        context_selector=selector,
        default_runtime_kind=default_runtime_kind,
        prefix=prefix,
    )


def _backlog_definition_runtime_factory(
    *,
    context: str,
    run_cwd: Path,
    model_by_kind: dict[AgentRuntimeKind, HarnessModelOption],
) -> Callable[[AgentRuntimeKind], AgentRuntimePort]:
    """Build the per-step runtime factory for the backlog-definition workflow.

    Real harnesses (pi/codex) resolve to their live adapters; ``FAKE`` resolves to a
    *driving* fake that returns an APPROVED handoff with an in-scope artifact_ref, so
    ``--harness fake`` walks the whole §4 sequence deterministically (mirrors the
    release-definition fake factory).
    """
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunResult,
        AgentRunStatus,
    )
    from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime

    approving = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake backlog-definition worker: APPROVED",
        artifact_refs=(f".dadaia/handoff/{context}/backlog-definition-step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )

    def factory(kind: AgentRuntimeKind) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            return FakeAgentRuntime(result=approving)
        return build_agent_runtime(kind, cwd=run_cwd, model=model_by_kind.get(kind))

    return factory


def build_backlog_definition_workflow(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    default_runtime_kind: AgentRuntimeKind = AgentRuntimeKind.FAKE,
    prefix: PromptPrefix | None = None,
    cwd: Path | None = None,
    models: dict[AgentRuntimeKind, HarnessModelOption] | None = None,
) -> "BacklogDefinitionWorkflow":
    """Compose the fragment-driven backlog-definition workflow (R2 / epic §4).

    Mirrors :func:`build_release_definition_workflow` field-for-field: the injected runtime
    factory resolves each step's ``AgentRuntimeKind`` to its adapter (``FAKE`` drives the
    sequence end-to-end); the :class:`ContextSelector` resolves each fragment's dynamic
    inputs bounded by ``max_context_policy``; the R1 canonical-subject :class:`Registry`
    backs the ``subject_bind`` Python step. ``models`` maps a runtime kind to its discrete
    Layer-2 model (LAW 2). All roots are derived from ``workspace_root`` — never cwd.
    """
    from dadaia_workspace.features.backlog.subject_registry import build_registry
    from dadaia_workspace.features.lifecycle.context_selector import (
        ContextSelector,
        SpecContext,
    )
    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
        BacklogDefinitionWorkflow,
    )

    _guard_initialized(workspace_root)
    run_cwd = cwd or workspace_root
    model_by_kind = models or {}
    context_name = resolve_bound_context_name(context) or context
    specs_dir = workspace_root / "repos" / context_name / "specs"
    source_root = workspace_root / "repos" / context_name
    if not specs_dir.is_dir():
        # Self-hosting library repo: specs live at the workspace-root tree.
        specs_dir = workspace_root / "specs"
        source_root = workspace_root
    handoff_dir = workspace_root / ".dadaia" / "handoff" / context_name
    selector = ContextSelector(
        SpecContext(specs_dir=specs_dir, release_id=release_id, handoff_dir=handoff_dir)
    )
    registry = build_registry(
        source_root=source_root,
        catalog_path=specs_dir / "memory" / "product" / "catalog.json",
        alias_map_path=workspace_root / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs_dir,
    )
    return BacklogDefinitionWorkflow(
        context=context,
        release_id=release_id,
        run_store=build_lifecycle_run_store(workspace_root),
        runtime_factory=_backlog_definition_runtime_factory(
            context=context, run_cwd=run_cwd, model_by_kind=model_by_kind
        ),
        context_selector=selector,
        registry=registry,
        default_runtime_kind=default_runtime_kind,
        prefix=prefix,
    )


def _backlog_context_roots(workspace_root: Path, context: str) -> tuple[Path, Path]:
    """Resolve ``(specs_dir, source_root)`` for a context's backlog ops.

    Mirrors the release/backlog-definition factories: a consumer context resolves to
    ``repos/<ctx>/specs`` + ``repos/<ctx>``; the self-hosting library repo falls back to the
    workspace-root tree. All roots are derived from ``workspace_root`` — never cwd.
    """
    context_name = resolve_bound_context_name(context) or context
    specs_dir = workspace_root / "repos" / context_name / "specs"
    source_root = workspace_root / "repos" / context_name
    if not specs_dir.is_dir():
        specs_dir = workspace_root / "specs"
        source_root = workspace_root
    return specs_dir, source_root


def build_release_spec_path(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
) -> Path:
    """Resolve ``<specs_dir>/releases/<release_id>/SPEC.md`` for a context's release.

    Uses the same root resolution as :func:`build_backlog_removal_lifecycle`
    (:func:`_backlog_context_roots`): a consumer context resolves to ``repos/<ctx>/specs``;
    the self-hosting library repo falls back to the workspace-root ``specs``. All roots are
    derived from ``workspace_root`` — never cwd. The producer post-step reads the
    ``**Consumes:**`` line from this path (SPEC §3.2).
    """
    specs_dir, _source_root = _backlog_context_roots(workspace_root, context)
    return specs_dir / "releases" / release_id / "SPEC.md"


def build_backlog_removal_lifecycle(
    workspace_root: Path,
    *,
    context: str,
) -> "BacklogRemovalLifecycle":
    """Compose the removal-on-release lifecycle (SPEC §3.6) over a context's backlog.

    Binds the injected backlog/archive roots + the R1 canonical-subject registry so the
    caller can write the ``consumed_backlog`` ledger at release-definition and apply the
    residual-aware removal hook at closure. All roots are derived from ``workspace_root``.
    """
    from dadaia_workspace.features.backlog.removal_lifecycle import BacklogRemovalLifecycle
    from dadaia_workspace.features.backlog.subject_registry import build_registry

    _guard_initialized(workspace_root)
    specs_dir, source_root = _backlog_context_roots(workspace_root, context)
    registry = build_registry(
        source_root=source_root,
        catalog_path=specs_dir / "memory" / "product" / "catalog.json",
        alias_map_path=workspace_root / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs_dir,
    )
    return BacklogRemovalLifecycle(
        backlog_dir=specs_dir / "backlog",
        archive_root=specs_dir / "_archive",
        registry=registry,
    )


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
    workflows_service = build_workflow_catalog_service(workspace_root)
    service = build_panel_service(workspace_root, telemetry=telemetry, academy=academy)
    return {
        "index": render_index(service),
        "api_panel_status": render_api_servers(service),
        "health": render_health(),
        "api_contexts": render_api_contexts(service),
        "api_kanban": render_api_kanban(
            workspace_root,
            alive_contexts=_build_alive_contexts_provider(workspace_root),
            pid_probe=_build_pid_probe(),
        ),
        "api_academy": render_api_academy(service),
        "academy_lesson": render_academy_lesson(academy),
        "api_reports": render_api_reports(service),
        "reports_serve": serve_report_file(service),
        "api_report_delete": delete_report_file(service),
        "api_report_mark_important": mark_report_important(service),
        "api_report_unmark_important": unmark_report_important(service),
        "api_agents": render_api_agents_canonical(service),
        "api_agent_prompt": render_api_agent_prompt(service),
        "api_workflows": render_api_workflows_list(service),
        "api_workflow_detail": render_api_workflow_detail(workflows_service),
        "api_dadaia_workflows": render_api_dadaia_workflows_list(workflows_service),
        "api_dadaia_workflow_detail": render_api_dadaia_workflow_detail(workflows_service),
        "api_sessions": render_api_sessions(service),
        "api_session_detail": render_api_session_detail(service),
        "memory": render_memory(workspace_root),
        "memory_view": render_memory_wrapper(workspace_root),
        "static": render_static(),
    }
