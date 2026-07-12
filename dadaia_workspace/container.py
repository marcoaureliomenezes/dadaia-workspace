"""Composition root — builds services with concrete infrastructure."""

import datetime as dt
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dadaia_workspace.core.models.lifecycle import LifecyclePhase
    from dadaia_workspace.core.models.workflow_execution import (
        WorkflowModelPolicyOverlay,
        WorkflowPolicySnapshot,
    )
    from dadaia_workspace.core.protocols.git_client import GitClient
    from dadaia_workspace.core.protocols.plugin_store import PluginStore
    from dadaia_workspace.core.protocols.workflow_model_policy_store import (
        WorkflowModelPolicyStorePort,
    )
    from dadaia_workspace.features.agents.model_policy import AgentModelPolicyService
    from dadaia_workspace.features.backlog.removal_lifecycle import (
        BacklogRemovalLifecycle,
    )
    from dadaia_workspace.features.lifecycle.fragments.loader import FragmentLoader
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowCatalog,
        WorkflowExecutionPolicyResolver,
    )
    from dadaia_workspace.features.lifecycle.service import LifecyclePreflightInput
    from dadaia_workspace.features.lifecycle.workflow_handoff_doctor import (
        WorkflowHandoffDoctor,
    )
    from dadaia_workspace.features.lifecycle.workflow_handoffs import (
        WorkflowHandoffResolver,
    )
    from dadaia_workspace.features.lifecycle.workflows.audit import AuditWorkflow
    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
        BacklogDefinitionWorkflow,
    )
    from dadaia_workspace.features.lifecycle.workflows.bug_report import BugReportWorkflow
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )
    from dadaia_workspace.features.lifecycle.workflows.research import ResearchWorkflow
    from dadaia_workspace.infrastructure.json_local_model_profile_store import (
        JsonLocalModelProfileStore,
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
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.academy import render_academy_lesson
from dadaia_workspace.features.panel.views.agent_policy import (
    render_api_agent_model_policy,
    render_api_agent_model_templates,
    render_post_agent_model_policy_validate,
    render_put_agent_model_policy,
)
from dadaia_workspace.features.panel.views.api_academy import render_api_academy
from dadaia_workspace.features.panel.views.api_agents import (
    render_api_agent_prompt,
    render_api_agents_canonical,
)
from dadaia_workspace.features.panel.views.api_contexts import render_api_contexts
from dadaia_workspace.features.panel.views.api_health import render_health
from dadaia_workspace.features.panel.views.api_reports import (
    delete_report_file,
    mark_report_important,
    render_api_reports,
    serve_report_file,
    unmark_report_important,
)
from dadaia_workspace.features.panel.views.api_servers import render_api_servers
from dadaia_workspace.features.panel.views.api_sessions import render_api_sessions
from dadaia_workspace.features.panel.views.api_workflows import (
    render_api_dadaia_workflow_detail,
    render_api_dadaia_workflows_list,
    render_api_workflow_detail,
    render_api_workflows_list,
)
from dadaia_workspace.features.panel.views.index import render_index
from dadaia_workspace.features.panel.views.memory import render_memory
from dadaia_workspace.features.panel.views.static import render_static
from dadaia_workspace.features.panel.views.workflow_policy import (
    render_api_lifecycle_runs,
    render_api_workflow_catalog,
    render_api_workflow_catalog_detail,
    render_api_workflow_fragment,
    render_api_workflow_model_policy,
    render_api_workflow_model_profiles,
    render_api_workflow_step_ledger,
    render_post_workflow_model_policy_validate,
    render_put_workflow_model_policy,
)
from dadaia_workspace.features.panel.views.wrapper import render_memory_wrapper
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.reports.next import ReportsNextService
from dadaia_workspace.features.reports.retention import ReportRetentionService
from dadaia_workspace.features.reports.validation import ReportsValidationService
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
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore
from dadaia_workspace.infrastructure.markdown_agent_store import MarkdownAgentStore
from dadaia_workspace.infrastructure.markdown_workflow_store import MarkdownWorkflowStore
from dadaia_workspace.infrastructure.process_ancestry_adapter import (
    LinuxProcAncestry,
    PsProcessAncestry,
    WindowsToolhelpAncestry,
)
from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe, build_pid_probe
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter
from dadaia_workspace.infrastructure.stdlib_handoff_validator import StdlibHandoffValidator


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
    # v0.1.65 FR7 (D-4): the agent-model-policy overlay loader is injected here so the
    # features-layer service never imports the infrastructure store directly.
    from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
        JsonAgentModelPolicyStore,
    )

    return PublicAssetService(
        public_assets=FileSystemPublicAssetManager(),
        agent_policy_loader=lambda root: JsonAgentModelPolicyStore(root).load(),
    )


def build_repos_service() -> ReposService:
    return ReposService(excel_reader=OpenpyxlExcelReader())


def build_git_client() -> "GitClient":
    """Composition-root seam for the subprocess-backed ``GitClient`` (v0.1.72 FR4).

    The CLI layer must not import infrastructure directly (import-linter contract);
    commands that need a read-only git probe (e.g. ``context show``'s live
    ``current_branch``) compose it here.
    """
    return GitSubprocessClient()


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


#: Default cap on ancestry pids collected into a bind-epoch marker / a resolver-side
#: attribution set (W1-7/W1-8, v0.1.47). Mirrors ``session_identity._BIND_EPOCH_MAX_CHAIN``.
_ANCESTRY_CHAIN_CAP = 8


def build_ancestry_pid_chain(start_pid: int, *, cap: int = _ANCESTRY_CHAIN_CAP) -> list[int]:
    """Return ``[start_pid, parent, grandparent, …]`` nearest-first, capped at ``cap``.

    Walks the PPID chain upward from ``start_pid`` using the platform-selected read-only
    :class:`ProcessAncestry` adapter (the SAME accessor the pre-commit chokepoint and
    ``context release`` use — :func:`build_process_ancestry`). This is the composition-root
    seam for the bind-epoch ancestry-chain attribution: ``dadaia context bind`` records this
    chain in the marker (W1-7) and the CLI resolver seam builds it for the current process
    (W1-8), so a marker written from an ephemeral harness shell is still attributable on a
    later call via the stable harness pid deeper in the chain.

    The adapter's ppid walk is private to each concrete adapter; the port itself only
    promises :meth:`~ProcessAncestry.is_ancestor`. When no ppid walk is available on this
    platform (or any probe error), we degrade to the single ``[start_pid]`` line — exactly
    the pre-v0.1.47 single-getppid behavior. Non-destructive (read-only /proc, ``ps``, or a
    Toolhelp32 snapshot); never raises.
    """
    if start_pid <= 0:
        return []
    chain: list[int] = [start_pid]
    try:
        ancestry = build_process_ancestry()
        ppid_of = getattr(ancestry, "_ppid_of", None)
        if not callable(ppid_of):
            return chain
        seen = {start_pid}
        current = start_pid
        while len(chain) < cap:
            raw = ppid_of(current)
            parent = raw if isinstance(raw, int) else None
            # Stop at an unreadable link, a root pid (0/1), or a cycle — none extend a
            # useful attribution chain.
            if parent is None or parent <= 1 or parent in seen:
                break
            chain.append(parent)
            seen.add(parent)
            current = parent
    except Exception:  # noqa: BLE001 — attribution is best-effort; bind/resolve never fail on it.
        return chain
    return chain


def build_doctor_service(workspace_root: Path) -> DoctorService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return DoctorService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        pid_probe=build_pid_probe(),
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


def build_orchestration_catalog_service(workspace_root: Path) -> WorkflowsService:
    """Compose the read-only orchestration catalog surface for ``dadaia orchestrate``.

    Since v0.1.53 the retired ``features/orchestration`` package (whose
    ``start_run``/``resume_run`` were honest no-ops and whose ``run``/``status``/``resume``
    verbs are gone) is replaced by a ``WorkflowsService`` accessor over the shared
    ``MarkdownWorkflowStore``. The service returns raw ``WorkflowDefinition`` objects
    (gate-kind preserving) so the ``list``/``show`` ``--json`` contract is unchanged. The
    workflow files are validated against the projected agent catalog exactly as the old
    surface did. Guards initialization so an uninitialized workspace still exits non-zero.
    """
    _guard_initialized(workspace_root)
    return WorkflowsService(
        workspace_root,
        agent_catalog=_agent_catalog(workspace_root),
        store_factory=MarkdownWorkflowStore,
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
    return WorkflowsService(workspace_root, store_factory=MarkdownWorkflowStore)


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
        workflows_service=build_workflow_catalog_service(workspace_root),
        report_retention=ReportRetentionService(workspace_root),
        adapter_registry=dict(ADAPTER_REGISTRY),
        agents_provider=FileSystemAgentsProvider(store_factory=MarkdownAgentStore),
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
    """Compose lifecycle hygiene service.

    v0.1.78 T-C / FR-C: always wires a real run store, so ``cleanup()``'s step-payload
    coverage (``.dadaia/runs/lifecycle/``) is live in every production caller — the CLI
    ``hygiene clean``/``hygiene status`` commands and the preflight gate's remediation
    text alike now share the SAME candidate classifier the handoffs doctor and the
    retention sweep already use for that zone.
    """
    _guard_initialized(workspace_root)
    return LifecycleHygieneService(
        workspace_root, run_store=build_lifecycle_run_store(workspace_root)
    )


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
            # A live run's workflow-step payloads are sacrosanct — claim each one so the
            # retention sweep never reclaims a mid-flight step's payload (A23).
            for step_record in run.workflow_steps:
                claims.add(step_record.payload_ref.lstrip("/"))
        return frozenset(claims)

    return _provider


def _step_payload_reclaim_allow(
    workspace_root: Path,
) -> Callable[[], frozenset[str]]:
    """Provider of cleanup-eligible workflow-step payload refs (T-30-D-07 / A23).

    A step payload is reclaim-eligible only when its ledger record is ``cleanup_eligible``
    (every declared consumer consumed it AND its retention mode is delete-after-consumed)
    AND the run is terminal (a live run's payloads are protected by ``_live_lifecycle_claims``).
    Promoted-to-evidence payloads are never cleanup-eligible, so they are never in this set
    and always survive. The retention sweep applies its own past-TTL gate on top of this
    allow-list. Fail-soft: a bad record is skipped, never crashing the sweep.
    """
    from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus

    terminal = {LifecycleRunStatus.COMPLETED, LifecycleRunStatus.FAILED}

    def _provider() -> frozenset[str]:
        store = build_lifecycle_run_store(workspace_root)
        run_dir = store.root
        if not run_dir.is_dir():
            return frozenset()
        allow: set[str] = set()
        for record in sorted(run_dir.glob("*.json")):
            try:
                run = store.load(record.stem)
            except Exception:  # noqa: BLE001 — a single bad record never breaks the sweep.
                continue
            if run is None or run.status not in terminal:
                continue
            for step_record in run.workflow_steps:
                if step_record.is_cleanup_eligible():
                    allow.add(step_record.payload_ref.lstrip("/"))
        return frozenset(allow)

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
        step_payload_reclaim_allow=_step_payload_reclaim_allow(workspace_root),
    )


def build_lifecycle_preflight_service(workspace_root: Path) -> LifecyclePreflightService:
    """Compose lifecycle preflight service."""
    _guard_initialized(workspace_root)
    return LifecyclePreflightService()


def _expected_phase_for_active_phase(raw_phase: str | None) -> "LifecyclePhase":
    """Resolve the preflight ``expected_phase`` from an ``ACTIVE.md`` phase token (FR3).

    Maps an ``ACTIVE.md`` ``phase:`` token (release-lifecycle vocabulary) to the
    corresponding step-lifecycle
    :class:`~dadaia_workspace.core.models.lifecycle.LifecyclePhase`.
    ``DEFINITION``/``SPEC``/``PLAN``/``TASKS`` all precede implementation and map to
    ``RELEASE_DEFINITION``; anything unrecognized (incl. ``BLOCKED``/absent) degrades to
    ``IMPLEMENTATION`` — the safest default (most releases spend most of their life
    there, and a preflight run is itself an implementation-phase diagnostic).
    """
    from dadaia_workspace.core.models.lifecycle import LifecyclePhase

    normalized = (raw_phase or "").strip().upper()
    mapping: dict[str, LifecyclePhase] = {
        "DEFINITION": LifecyclePhase.RELEASE_DEFINITION,
        "SPEC": LifecyclePhase.RELEASE_DEFINITION,
        "PLAN": LifecyclePhase.RELEASE_DEFINITION,
        "TASKS": LifecyclePhase.RELEASE_DEFINITION,
        "IMPLEMENTATION": LifecyclePhase.IMPLEMENTATION,
        "CLOSURE": LifecyclePhase.CLOSURE,
    }
    return mapping.get(normalized, LifecyclePhase.IMPLEMENTATION)


def _required_mode_for_expected_phase(expected_phase: "LifecyclePhase") -> str:
    """Resolve the preflight ``required_mode`` policy from the expected phase (FR3).

    Only ``CLOSURE`` calls for ``review`` (the closing gate ladder); every other phase —
    including the release-definition phases, which still require a session bound to
    actually edit SPEC/PLAN/TASKS — requires ``implementation``.
    """
    from dadaia_workspace.core.models.lifecycle import LifecyclePhase

    if expected_phase is LifecyclePhase.CLOSURE:
        return "review"
    return "implementation"


def build_lifecycle_preflight_input(
    workspace_root: Path,
    *,
    context: str,
    release_id: str | None = None,
) -> "LifecyclePreflightInput":
    """Compose the real preflight-input probe assembly (v0.1.69 FR3).

    ``LifecyclePreflightInput``'s state classes (``ActiveReleaseState``,
    ``GitPreflightState``, ``SpecsDoctorState``, ``LeaseModeState``, ``HygieneCounters``)
    had ZERO production producers before this builder — only
    ``test_preflight_service.py`` hand-fed them. This composes each from an EXISTING
    reader (never a second/forked implementation):

    * ``active_release`` ← ``ACTIVE.md`` via the shared ``read_active_md`` parser
      (``features.specs.doctor_common``, the same reader ``specs doctor``/CLI verbs use).
    * ``git`` ← ``GitSubprocessClient`` (``infrastructure.git_subprocess`` — the same
      client every other git-backed builder in this module composes) against
      ``repos/<context>``.
    * ``specs_doctor`` ← a real ``SpecsDoctor(specs_dir).check()`` run (the same doctor
      ``dadaia specs doctor`` invokes); ``ok`` is true iff no ERROR-severity issue fired.
    * ``lease``/``binding`` ← ``features.spec_context.{lease, session_identity}`` — the
      same incumbent-pointer + lease-record readers ``context show``/``bind`` use.
    * ``hygiene`` ← ``build_lifecycle_hygiene_service(workspace_root).status()``
      (unchanged, reused directly).
    * ``expected_phase``/``required_mode`` ← a small policy derived from the ACTIVE.md
      phase token (:func:`_expected_phase_for_active_phase` /
      :func:`_required_mode_for_expected_phase`).

    ``release_id=None`` defaults to the context's ACTIVE.md release id (a bare
    ``preflight --context <ctx>`` with no explicit ``--release-id`` targets whatever
    release is currently active).
    """
    from dadaia_workspace.core.models.lifecycle import LifecyclePhase
    from dadaia_workspace.features.lifecycle.service import (
        ActiveReleaseState,
        BoundContext,
        GitPreflightState,
        LeaseModeState,
        LifecyclePreflightInput,
        SpecsDoctorState,
    )
    from dadaia_workspace.features.spec_context import lease as _lease
    from dadaia_workspace.features.spec_context import session_identity
    from dadaia_workspace.features.specs import Severity, SpecsDoctor
    from dadaia_workspace.features.specs.doctor_common import read_active_md
    from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

    _guard_initialized(workspace_root)
    specs_dir = _context_specs_dir(workspace_root, context)
    repo_dir = workspace_root / "repos" / context

    # --- active-release ← ACTIVE.md ------------------------------------------------
    active_md_release, _segment, active_md_phase, _err = read_active_md(
        specs_dir / "releases" / "ACTIVE.md"
    )
    active_release = ActiveReleaseState(release_id=active_md_release, phase=active_md_phase)
    resolved_release_id = release_id if release_id is not None else (active_md_release or "")

    # --- expected_phase / required_mode policy -------------------------------------
    expected_phase: LifecyclePhase = _expected_phase_for_active_phase(active_md_phase)
    required_mode = _required_mode_for_expected_phase(expected_phase)

    # --- git ← GitSubprocessClient --------------------------------------------------
    # v0.1.69 FR3: reuses the SAME infrastructure git adapter every other builder in this
    # module composes — never a second/forked git implementation. upstream_branch()/
    # unpushed_commit_count() are the two producer-specific reads this state needs.
    git_client = GitSubprocessClient()
    if repo_dir.is_dir() and git_client.is_git_root(repo_dir):
        dirty_paths = tuple(git_client.diff_name_only(repo_dir))
        upstream_branch = git_client.upstream_branch(repo_dir)
        unpushed_commit_count = (
            git_client.unpushed_commit_count(repo_dir) if upstream_branch is not None else 0
        )
        git_state = GitPreflightState(
            dirty_paths=dirty_paths,
            upstream_branch=upstream_branch,
            unpushed_commit_count=unpushed_commit_count,
        )
    else:
        # No repo on disk (e.g. the self-hosting workspace-root specs tree, or a context
        # never cloned): nothing to report dirty/unpushed on; no upstream to demand.
        git_state = GitPreflightState()

    # --- specs_doctor ← a real SpecsDoctor run --------------------------------------
    doctor_issues = SpecsDoctor(specs_dir).check()
    doctor_errors = [i for i in doctor_issues if i.severity is Severity.ERROR]
    specs_doctor_state = SpecsDoctorState(
        ok=not doctor_errors,
        summary=(
            "; ".join(f"{i.code}: {i.description}" for i in doctor_errors) if doctor_errors else ""
        ),
    )

    # --- binding + lease/mode ← session_identity / lease ----------------------------
    identity = session_identity.resolve_identity(workspace_root, context)
    incumbent_sid = identity.get("incumbent")
    incumbent_mode = identity.get("mode")
    binding: BoundContext | None = None
    if incumbent_sid:
        rec = session_identity.read_session(workspace_root, incumbent_sid)
        if rec is not None:
            binding = BoundContext(
                context=str(rec.get("context") or context),
                release_id=str(rec.get("release") or resolved_release_id),
                mode=str(rec.get("mode") or incumbent_mode or ""),
                session_id=incumbent_sid,
            )

    lease_record = _lease.read_record(workspace_root, context)
    live_foreign_holder = False
    holder_session_id: str | None = None
    if lease_record is not None:
        holder_session_id = str(lease_record.get("session_id") or "") or None
        # is_held() is the single canonical liveness verdict (core.lock_liveness.is_stale,
        # wrapped) — never a forked liveness check.
        #
        # v0.1.72 FR2 (bug `rebind-does-not-adopt-same-process-lease`): a record whose
        # holder pid is in THIS process's ancestry chain is never a foreign holder — a
        # session rotation inside the same harness process leaves the record naming an
        # old sid while the pid IS our lineage (acquire's rung-1 `.ptr` semantics would
        # RENEW it, so preflight must not call it foreign — the old forked identity
        # check contradicted the canon and permanently blocked rebinds).
        own_lineage = _lease.holder_in_lineage(
            lease_record, frozenset(build_ancestry_pid_chain(os.getpid()))
        )
        if (
            _lease.is_held(workspace_root, context)
            and holder_session_id != incumbent_sid
            and not own_lineage
        ):
            live_foreign_holder = True
    lease_state = LeaseModeState(
        mode=str(incumbent_mode or ""),
        holder_session_id=holder_session_id,
        live_foreign_holder=live_foreign_holder,
    )

    # --- hygiene ← the existing lifecycle hygiene service ---------------------------
    hygiene_counters = build_lifecycle_hygiene_service(workspace_root).status()

    return LifecyclePreflightInput(
        context=context,
        release_id=resolved_release_id,
        expected_phase=expected_phase,
        required_mode=required_mode,
        current_step="preflight",
        binding=binding,
        active_release=active_release,
        git=git_state,
        specs_doctor=specs_doctor_state,
        lease=lease_state,
        hygiene=hygiene_counters,
    )


def build_lifecycle_run_store(workspace_root: Path) -> JsonLifecycleRunStore:
    """Compose lifecycle run-state store."""
    _guard_initialized(workspace_root)
    return JsonLifecycleRunStore(workspace_root)


def build_workflow_handoff_doctor(
    workspace_root: Path,
    *,
    now: dt.datetime | None = None,
    context: str | None = None,
    release_id: str | None = None,
) -> "WorkflowHandoffDoctor":
    """Compose the workflow-step handoff doctor (v0.1.30 Item 5 / T-30-D-08 / A26).

    Read-only reconciliation of every run's ``workflow_steps`` ledger against the on-disk
    payloads under ``.dadaia/runs/lifecycle/<run>/steps/``; reports orphan / malformed /
    stale / undeclared / unconsumed-required incoherences. The clock is injectable for
    hermetic tests. v0.1.71 FR2: optional ``context``/``release_id`` narrow the report to
    the runs of one Spec Context release (``LifecycleRun`` carries both); ``None`` on both
    preserves the whole-workspace scope.
    """
    from dadaia_workspace.features.lifecycle.workflow_handoff_doctor import WorkflowHandoffDoctor

    _guard_initialized(workspace_root)
    return WorkflowHandoffDoctor(
        workspace_root,
        build_lifecycle_run_store(workspace_root),
        now=now,
        context=context,
        release_id=release_id,
    )


def build_workflow_handoff_resolver(
    workspace_root: Path,
) -> "WorkflowHandoffResolver":
    """Compose the run-scoped workflow-step handoff resolver (v0.1.30 Item 5 / T-30-D-03).

    The resolver is the queue engine over the ``LifecycleRun.workflow_steps`` control plane
    (persisted atomically through the run store) and the immutable step payload data plane
    (written under the WORKSPACE-ROOT ``.dadaia/runs/lifecycle/<run_id>/steps/`` canonical
    zone by ``FilesystemRuntimeFileAdapter``, which satisfies the narrow
    ``WorkflowStepPayloadWriter`` port). The clock is injected as an ISO-8601-UTC string
    factory.
    """
    from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver

    _guard_initialized(workspace_root)

    def _clock() -> str:
        return dt.datetime.now(tz=dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    return WorkflowHandoffResolver(
        run_store=build_lifecycle_run_store(workspace_root),
        payload_writer=FilesystemRuntimeFileAdapter(workspace_root),
        clock=_clock,
    )


def build_workflow_model_profile_registry() -> "WorkflowCatalog":
    """Compose the governed workflow catalog the policy resolver reads (T-28-B-01).

    Wave B promotes the governed catalog to **the** governed source: every worker step
    carries a default harness + a default model profile per supported harness (validated at
    import time against the built-in :mod:`model_profiles` registry).
    :func:`governed_workflow_catalog` projects that single source onto the resolver's
    :class:`WorkflowCatalog` seam, so the resolver and the panel read the *same* catalog (no
    second table). The function is pure (no I/O), so it takes no ``workspace_root``. v0.1.54
    FR2: the governed catalog now lives in ``features/lifecycle/governed_catalog`` (the
    cycle-break home); import it directly from the canonical lifecycle module.
    """
    from dadaia_workspace.features.lifecycle.governed_catalog import governed_workflow_catalog

    return governed_workflow_catalog()


def build_fragment_loader() -> "FragmentLoader":
    """Compose the shared :class:`FragmentLoader` over the packaged fragment library.

    Used by the read-only panel fragment inspector (Wave D — T-28-D-01) to resolve a
    governed step's fragment id to its resolved body + metadata. The loader reads from
    the packaged ``public/lifecycle_fragments/`` root (no I/O at construction), so it
    takes no ``workspace_root``.
    """
    from dadaia_workspace.features.lifecycle.fragments.loader import FragmentLoader

    return FragmentLoader()


def build_workflow_model_policy_store(workspace_root: Path) -> "WorkflowModelPolicyStorePort":
    """Compose the workflow-model-policy overlay store (T-28-A-08).

    Returns the store typed as the :class:`WorkflowModelPolicyStorePort` seam (FR1a): the
    consumers (``policy_doctor``, ``panel.views.workflow_policy``) depend on the port in
    ``core``, never the concrete JSON adapter. Reads/writes
    ``.dadaia/states/workflow_model_policy.json`` with atomic temp+rename and a
    ``.last-good.json`` backup. ``load()`` returns ``None`` on a missing file (defaults); a
    present-but-invalid file raises (missing != invalid).
    """
    from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
        JsonWorkflowModelPolicyStore,
    )

    _guard_initialized(workspace_root)
    return JsonWorkflowModelPolicyStore(workspace_root)


def build_local_model_profile_store(
    workspace_root: Path,
) -> "JsonLocalModelProfileStore":
    """Compose the operator-local model-profile store (T-30-C-01 / WS-PROFILES).

    Reads ``.dadaia/states/workflow_model_profiles.local.json`` with atomic temp+rename.
    ``load()`` returns ``()`` on a missing file (default-first — L3) and raises on a
    present-but-invalid store (``harness != "pi"`` per L1, any API-key-bearing field per
    L8, corrupt JSON, unknown field). The store is workspace-local and **never projected**
    into ``public/`` (L8).
    """
    from dadaia_workspace.infrastructure.json_local_model_profile_store import (
        JsonLocalModelProfileStore,
    )

    _guard_initialized(workspace_root)
    return JsonLocalModelProfileStore(workspace_root)


def build_agent_model_policy_service(workspace_root: Path) -> "AgentModelPolicyService":
    """Compose the panel-facing L1 agent-model-policy service (v0.1.65 FR8 / T-65-10).

    Injects (D-4 — the features module carries no infrastructure import):

    - the concrete :class:`JsonAgentModelPolicyStore` (typed to the feature's store
      port), whose valid override targets are the 9 core agents plus the INSTALLED
      plugin agents (FR3);
    - the **re-render callable** — the agents-only ``public install`` path over both
      L1 projections (G-2 Apply semantics; profile-scoped like every install);
    - the **plugin pack defaults** provider — ``{agent_name: pack model}`` parsed from
      the installed packs' staged bodies (D-5), so the resolved roster covers them.
    """
    from dadaia_workspace.features.agents.model_policy import AgentModelPolicyService
    from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
        JsonAgentModelPolicyStore,
    )
    from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
        _parse_agent_frontmatter,
    )

    def _installed_pack_defaults() -> dict[str, str]:
        states_dir = workspace_root / ".dadaia" / "states"
        ledger = build_plugin_store().read(states_dir)
        packs = ledger.plugins if ledger is not None else ()
        agentic_dir = workspace_root / ".dadaia" / "agentic"
        defaults: dict[str, str] = {}
        for pack in packs:
            for md in sorted((agentic_dir / "plugins" / pack / "agents").glob("*.md")):
                fm = _parse_agent_frontmatter(md.read_text(encoding="utf-8"))
                model = str(fm.get("model", "")) or None
                if model is None:
                    continue
                name = str(fm.get("name", "")) or md.stem
                defaults[name] = model
        return defaults

    def _rerender_agents() -> list[str]:
        return build_public_service().install(workspace_root, target="all", only="agents")

    store = JsonAgentModelPolicyStore(
        workspace_root, plugin_agent_names=frozenset(_installed_pack_defaults())
    )
    return AgentModelPolicyService(
        store=store,
        rerender=_rerender_agents,
        plugin_pack_defaults=_installed_pack_defaults,
    )


def build_plugin_store() -> "PluginStore":
    """Compose the installed-plugins ledger store (T-61-20 / FR4 — A-1 wired).

    Returns the store typed as the :class:`PluginStore` port: consumers (the ``dadaia
    plugin`` CLI and ``infrastructure/public_assets``) depend on the Protocol in ``core``,
    never on the ``JsonPluginStore`` adapter directly. The store is path-parametric —
    ``read``/``write`` take the target ``states_dir`` per call — so composition needs no
    workspace root.
    """
    from dadaia_workspace.infrastructure.json_plugin_store import JsonPluginStore

    return JsonPluginStore()


def load_operator_model_profiles(workspace_root: Path) -> None:
    """Load + merge the operator-local profiles into the process registry (WS-PROFILES).

    Idempotent: re-reads the local store and re-registers its profiles with
    :mod:`features.lifecycle.model_profiles`, so :func:`model_profiles.list_profiles` /
    :func:`profiles_for` / :func:`resolve` surface built-in + operator profiles. A missing
    store loads nothing (default-first — L3); a present-but-invalid store raises through the
    store's typed error, before any model call.
    """
    from dadaia_workspace.features.lifecycle import model_profiles

    store = build_local_model_profile_store(workspace_root)
    model_profiles.load_operator_profiles(store)


def build_workflow_policy_resolver(
    workspace_root: Path,
    *,
    context: str = "default",
    overlay: "WorkflowModelPolicyOverlay | None" = None,
) -> "WorkflowExecutionPolicyResolver":
    """Compose the single shared :class:`WorkflowExecutionPolicyResolver` (T-28-A-08).

    Loads the overlay from the policy store (missing ⇒ ``None`` ⇒ library defaults; an
    invalid overlay raises here, before any model call — LAW 4/5) and binds it to the
    governed catalog. CLI and panel both consume *this* resolver so they never disagree on
    which model a step runs. ``context`` is reserved for future per-context overlays; only
    the ``default`` context is honored this release (D-2).

    ``overlay`` lets a caller bind a **candidate** overlay (the panel validate/PUT path,
    T-28-C-02) instead of the on-disk one — the validation resolve runs against the
    candidate without persisting it. When ``overlay`` is ``None`` the on-disk overlay is
    loaded (the normal execution path).
    """
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        WorkflowExecutionPolicyResolver,
    )

    _guard_initialized(workspace_root)
    _ = context  # reserved (D-2: only `default` honored); recorded for call-site clarity.
    resolved_overlay = (
        overlay if overlay is not None else build_workflow_model_policy_store(workspace_root).load()
    )
    return WorkflowExecutionPolicyResolver(
        catalog=build_workflow_model_profile_registry(),
        overlay=resolved_overlay,
    )


def build_lifecycle_report_workflow(workspace_root: Path) -> LifecycleReportWorkflow:
    """Compose lifecycle report workflow."""
    _guard_initialized(workspace_root)
    return LifecycleReportWorkflow(
        workspace_root=workspace_root,
        runtime_files=FilesystemRuntimeFileAdapter(workspace_root),
        # v0.1.78 T-C / FR-C: same run-store wiring as build_lifecycle_hygiene_service so an
        # explicit report-workflow cleanup shares the one canonical candidate classifier.
        hygiene=LifecycleHygieneService(
            workspace_root, run_store=build_lifecycle_run_store(workspace_root)
        ),
        validation=build_reports_validation_service(workspace_root),
    )


def _context_specs_dir(workspace_root: Path, context: str) -> Path:
    """Resolve a context's ``specs/`` tree (v0.1.57 FR2 / A1 — role→atom map wiring).

    Mirrors :func:`build_release_definition_workflow`'s resolution: a consumer context resolves
    to ``workspace_root/repos/<ctx>/specs``; the self-hosting library repo falls back to the
    workspace-root ``specs`` tree. All roots derive from ``workspace_root`` — never cwd.
    """
    context_name = resolve_bound_context_name(context) or context
    specs_dir = workspace_root / "repos" / context_name / "specs"
    if not specs_dir.is_dir():
        specs_dir = workspace_root / "specs"
    return specs_dir


def resolve_context_specs_dir(workspace_root: Path, context: str) -> Path:
    """Public seam for :func:`_context_specs_dir` (FR3, v0.1.68).

    Lets a CLI verb resolve the same context→``specs/`` mapping the pipeline container
    already uses internally — e.g. so ``lifecycle pipeline`` can derive the implement
    step's write scope from the release's ``TASKS.md`` (see
    :func:`dadaia_workspace.features.lifecycle.tasks_write_scope.write_scope_from_tasks`)
    without duplicating the resolution logic.
    """
    return _context_specs_dir(workspace_root, context)


def _active_phase(specs_dir: Path) -> str | None:
    """Resolve the active ``ACTIVE.md`` lifecycle phase under *specs_dir* (v0.1.57 FR2).

    Reads ``<specs_dir>/releases/ACTIVE.md`` via the shared ``read_active_md`` parser. An
    absent or malformed ``ACTIVE.md`` (no ``release:``/``phase:`` line) degrades to ``None``
    (fail-open) so a context with no active release never crashes workflow construction.
    """
    from dadaia_workspace.features.specs.doctor_common import read_active_md

    _, _, phase, err = read_active_md(specs_dir / "releases" / "ACTIVE.md")
    return phase if err is None else None


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
    The ``specs_dir_resolver`` (v0.1.57 FR2 / A1) closes over ``workspace_root`` so the
    role→atom map resolves the run's context (only known at ``run()`` from ``scope.context``)
    to its ``specs/`` tree with a real path — the map is not inert in the real phase-verb path.
    """
    _guard_initialized(workspace_root)
    return LifecyclePhaseWorkflow(
        runtime=build_agent_runtime(runtime_kind, cwd=cwd or workspace_root, model=model),
        run_store=build_lifecycle_run_store(workspace_root),
        specs_dir_resolver=lambda ctx: _context_specs_dir(workspace_root, ctx),
        # v0.1.78 T-D / FR-D: a noncompliant worker attempt's diagnostic is persisted under
        # the run's step-artifact zone via the same canonical runtime-file writer every other
        # lifecycle artifact uses.
        runtime_files=FilesystemRuntimeFileAdapter(workspace_root),
        # Bug gate-accepts-phantom-artifact-evidence: declared refs must exist.
        artifact_root=workspace_root,
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
    runtime_factory: "Callable[[AgentRuntimeKind], AgentRuntimePort] | None" = None,
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

    v0.1.78 T-B / FR-B: the ``handoff_resolver`` is now ALWAYS wired (bug
    ``full-pipeline-success-persists-running-empty-ledger`` — the production ``pipeline``
    CLI verb used to build a pipeline with no resolver, so every full-ladder run's
    ``workflow_steps`` ledger stayed permanently empty). Every real ``build_lifecycle_pipeline``
    caller now gets the same run-scoped per-step handoff-ledger payloads
    ``run_implement_review_loop`` already produced; only a direct, fixture-level
    ``LifecyclePipeline(...)`` construction (tests) can still omit it.
    """
    _guard_initialized(workspace_root)
    run_cwd = cwd or workspace_root
    model_by_kind = models or {}
    return LifecyclePipeline(
        context=context,
        release_id=release_id,
        run_store=build_lifecycle_run_store(workspace_root),
        # v0.1.72 FR5: an injected factory (the CLI's driving-fake-aware seam) wins;
        # the bare default remains for direct composition in tests.
        runtime_factory=runtime_factory
        or (lambda kind: build_agent_runtime(kind, cwd=run_cwd, model=model_by_kind.get(kind))),
        prefix=prefix,
        policy_snapshot=policy_snapshot,
        handoff_resolver=build_workflow_handoff_resolver(workspace_root),
        # Bug gate-accepts-phantom-artifact-evidence: declared refs must exist.
        artifact_root=workspace_root,
        # FR2 (A1): the real ``specs/`` tree so the role→atom map grounds the review_qa step
        # (qa-engineer → quality-assurance.md) in the production pipeline path, not just fixtures.
        specs_dir=_context_specs_dir(workspace_root, context),
        # v0.1.78 T-D / FR-D: same canonical runtime-file writer as the phase workflow —
        # a noncompliant worker attempt persists its diagnostic under the run's
        # step-artifact zone.
        runtime_files=FilesystemRuntimeFileAdapter(workspace_root),
    )


def _release_definition_runtime_factory(
    *,
    context: str,
    run_cwd: Path,
    release_id: str | None = None,
) -> Callable[[AgentRuntimeKind], AgentRuntimePort]:
    """Build the per-step runtime factory for the release-definition workflow.

    Real harnesses (pi/codex/claude) resolve to their live adapters — the policy-resolved
    concrete model reaches each adapter through ``request.resolved_model`` (threaded from
    the step's ``resolved_model`` by ``apply_resolved_policy``), not a construction-time
    model. ``FAKE`` resolves to a *driving* fake so ``--harness fake`` walks the whole
    §6.1 sequence deterministically. The fake is STEP-AWARE: a create step
    (spec/plan/tasks) also declares + materializes its real deliverable under the
    release's specs zone — the gate now requires deliverable-zone evidence and verifies
    refs exist (bugs gate-accepts-phantom-artifact-evidence /
    create-step-gate-accepts-refusal-handoff-as-success).
    """
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunRequest,
        AgentRunResult,
        AgentRunStatus,
    )

    _CREATE_DELIVERABLES = {
        "spec_create": "SPEC.md",
        "plan_create": "PLAN.md",
        "tasks_create": "TASKS.md",
    }

    class _ReleaseDefinitionDrivingFake:
        def __init__(self, kind: AgentRuntimeKind) -> None:
            self._kind = kind

        def runtime_kind(self) -> AgentRuntimeKind:
            return self._kind

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            label = (request.task_id or "").rsplit(":", 1)[-1]
            refs = [f".dadaia/handoff/{context}/release-definition-step.handoff.json"]
            deliverable = _CREATE_DELIVERABLES.get(label)
            if deliverable is not None and release_id is not None:
                specs_prefix = (
                    f"repos/{context}/specs"
                    if (run_cwd / "repos" / context / "specs").is_dir()
                    else "specs"
                )
                refs.append(f"{specs_prefix}/releases/{release_id}/{deliverable}")
            for ref in refs:
                target = run_cwd / ref
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(
                        '{"fake": true, "summary": "driving-fake stub artifact"}\n'
                        if ref.endswith(".json")
                        else "# driving-fake stub artifact\n\n> **Status:** Draft\n",
                        encoding="utf-8",
                    )
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="fake release-definition worker: APPROVED",
                artifact_refs=tuple(refs),
                structured_output={"verdict": "APPROVED"},
            )

    def factory(kind: AgentRuntimeKind) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            return _ReleaseDefinitionDrivingFake(kind)
        return build_agent_runtime(kind, cwd=run_cwd)

    return factory


def build_release_definition_workflow(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    default_runtime_kind: AgentRuntimeKind = AgentRuntimeKind.FAKE,
    prefix: PromptPrefix | None = None,
    cwd: Path | None = None,
    policy_snapshot: "WorkflowPolicySnapshot | None" = None,
) -> "ReleaseDefinitionWorkflow":
    """Compose the fragment-driven release-definition workflow (WS-5 / §6.1).

    The workflow runs the §6.1 step sequence with fragment-assembled, scoped prompts and
    Python-owned gates (no generic ``"Run the step"`` suffix). The injected runtime
    factory resolves each step's ``AgentRuntimeKind`` to its adapter so harnesses can be
    mixed per step; ``FAKE`` drives the sequence end-to-end. The :class:`ContextSelector`
    resolves each fragment's dynamic inputs, bounded by the fragment's ``max_context_policy``.
    ``policy_snapshot`` is the resolved governance snapshot (v0.1.56 / FR1, from
    :func:`build_workflow_policy_resolver`); when present it is frozen onto the run before
    the first step (LAW 7). The per-step concrete model reaches the adapter through the
    step's ``resolved_model`` (threaded by ``apply_resolved_policy``), so no model-by-kind
    construction arg is needed.
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
    context_name = resolve_bound_context_name(context) or context
    specs_dir = workspace_root / "repos" / context_name / "specs"
    if not specs_dir.is_dir():
        # Self-hosting library repo: specs live at the workspace-root tree.
        specs_dir = workspace_root / "specs"
    handoff_dir = workspace_root / ".dadaia" / "handoff" / context_name
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs_dir,
            release_id=release_id,
            handoff_dir=handoff_dir,
            phase=_active_phase(specs_dir),
        )
    )
    return ReleaseDefinitionWorkflow(
        context=context,
        release_id=release_id,
        run_store=build_lifecycle_run_store(workspace_root),
        runtime_factory=_release_definition_runtime_factory(
            context=context, run_cwd=run_cwd, release_id=release_id
        ),
        context_selector=selector,
        default_runtime_kind=default_runtime_kind,
        prefix=prefix,
        policy_snapshot=policy_snapshot,
        # Bug fragment-workflows-never-persist-step-handoffs: same ALWAYS-wired rule as
        # build_lifecycle_pipeline (v0.1.78 FR-B) — without it every produces= step's
        # payload is silently dropped and the run's ledger stays empty.
        handoff_resolver=build_workflow_handoff_resolver(workspace_root),
        # Bug gate-accepts-phantom-artifact-evidence: declared refs must exist.
        artifact_root=workspace_root,
    )


def _backlog_definition_runtime_factory(
    *,
    context: str,
    run_cwd: Path,
) -> Callable[[AgentRuntimeKind], AgentRuntimePort]:
    """Build the per-step runtime factory for the backlog-definition workflow.

    Real harnesses (pi/codex) resolve to their live adapters — the policy-resolved concrete
    model reaches each adapter through ``request.resolved_model`` (threaded from the step's
    ``resolved_model``), not a construction-time model; ``FAKE`` resolves to a *driving*
    fake that returns an APPROVED handoff with an in-scope artifact_ref, so ``--harness
    fake`` walks the whole §4 sequence deterministically (mirrors the release-definition
    fake factory).
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
            # materialize_root: the gate now verifies declared refs EXIST (bug
            # gate-accepts-phantom-artifact-evidence) — the driving fake writes its stub.
            return FakeAgentRuntime(result=approving, materialize_root=run_cwd)
        return build_agent_runtime(kind, cwd=run_cwd)

    return factory


def build_backlog_definition_workflow(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    default_runtime_kind: AgentRuntimeKind = AgentRuntimeKind.FAKE,
    prefix: PromptPrefix | None = None,
    cwd: Path | None = None,
    policy_snapshot: "WorkflowPolicySnapshot | None" = None,
) -> "BacklogDefinitionWorkflow":
    """Compose the fragment-driven backlog-definition workflow (R2 / epic §4).

    Mirrors :func:`build_release_definition_workflow` field-for-field: the injected runtime
    factory resolves each step's ``AgentRuntimeKind`` to its adapter (``FAKE`` drives the
    sequence end-to-end); the :class:`ContextSelector` resolves each fragment's dynamic
    inputs bounded by ``max_context_policy``; the R1 canonical-subject :class:`Registry`
    backs the ``subject_bind`` Python step. ``policy_snapshot`` is the resolved governance
    snapshot (v0.1.56 / FR1) frozen onto the run before the first step; the per-step model
    reaches the adapter through the step's ``resolved_model``. All roots are derived from
    ``workspace_root`` — never cwd.
    """
    from dadaia_workspace.cli.anchors import derive_cli_anchors
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
    context_name = resolve_bound_context_name(context) or context
    specs_dir = workspace_root / "repos" / context_name / "specs"
    source_root = workspace_root / "repos" / context_name
    if not specs_dir.is_dir():
        # Self-hosting library repo: specs live at the workspace-root tree.
        specs_dir = workspace_root / "specs"
        source_root = workspace_root
    handoff_dir = workspace_root / ".dadaia" / "handoff" / context_name
    # cli-kind anchors derived at the composition boundary (FR1b) — the selector's
    # ``backlog_index`` resolution and the ``subject_bind`` registry both bind cli subjects.
    cli_anchors = derive_cli_anchors()
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs_dir,
            release_id=release_id,
            handoff_dir=handoff_dir,
            phase=_active_phase(specs_dir),
        ),
        cli_anchors=cli_anchors,
    )
    registry = build_registry(
        source_root=source_root,
        catalog_path=specs_dir / "memory" / "product" / "catalog.json",
        alias_map_path=workspace_root / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs_dir,
        cli_anchors=cli_anchors,
    )
    return BacklogDefinitionWorkflow(
        context=context,
        release_id=release_id,
        run_store=build_lifecycle_run_store(workspace_root),
        runtime_factory=_backlog_definition_runtime_factory(context=context, run_cwd=run_cwd),
        context_selector=selector,
        registry=registry,
        default_runtime_kind=default_runtime_kind,
        prefix=prefix,
        policy_snapshot=policy_snapshot,
        # Bug gate-accepts-phantom-artifact-evidence: declared refs must exist.
        artifact_root=workspace_root,
    )


def _handoff_driving_fake_factory(
    *,
    context: str,
    run_cwd: Path,
    summary: str,
    artifact_ref: str,
) -> Callable[[AgentRuntimeKind], AgentRuntimePort]:
    """Build a per-step runtime factory whose FAKE returns one in-scope handoff APPROVED result.

    Shared by the ``audit`` and ``research`` builders (v0.1.56 / FR2): every step of those
    workflows scopes writes to ``.dadaia/handoff/<ctx>/**``, so a single APPROVED handoff ref
    is in-scope for the whole sequence and ``--harness fake`` walks it end-to-end. Real
    harnesses (pi/codex) resolve to their live adapters; the policy-resolved concrete model
    reaches each adapter through ``request.resolved_model`` (threaded from the step's
    ``resolved_model`` by ``apply_resolved_policy``), not a construction-time model.
    """
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunResult,
        AgentRunStatus,
    )
    from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime

    approving = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary=summary,
        artifact_refs=(artifact_ref,),
        structured_output={"verdict": "APPROVED"},
    )

    def factory(kind: AgentRuntimeKind) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            # materialize_root: the gate now verifies declared refs EXIST (bug
            # gate-accepts-phantom-artifact-evidence) — the driving fake writes its stub.
            return FakeAgentRuntime(result=approving, materialize_root=run_cwd)
        return build_agent_runtime(kind, cwd=run_cwd)

    return factory


def build_audit_workflow(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    default_runtime_kind: AgentRuntimeKind = AgentRuntimeKind.FAKE,
    prefix: PromptPrefix | None = None,
    cwd: Path | None = None,
    policy_snapshot: "WorkflowPolicySnapshot | None" = None,
) -> "AuditWorkflow":
    """Compose the fragment-driven audit workflow (v0.1.56 / FR2), born resolver-governed.

    Mirrors :func:`build_release_definition_workflow`: the injected runtime factory resolves
    each step's ``AgentRuntimeKind`` to its adapter (``FAKE`` drives the whole
    scope→drift-scan→triage sequence end-to-end with an in-scope handoff ref); the
    :class:`ContextSelector` resolves each fragment's dynamic inputs, bounded by
    ``max_context_policy``. ``policy_snapshot`` is the resolved governance snapshot frozen onto
    the run before the first step (LAW 7); the per-step model reaches the adapter through the
    step's ``resolved_model``.
    """
    from dadaia_workspace.features.lifecycle.context_selector import (
        ContextSelector,
        SpecContext,
    )
    from dadaia_workspace.features.lifecycle.workflows.audit import AuditWorkflow

    _guard_initialized(workspace_root)
    run_cwd = cwd or workspace_root
    context_name = resolve_bound_context_name(context) or context
    specs_dir = workspace_root / "repos" / context_name / "specs"
    if not specs_dir.is_dir():
        specs_dir = workspace_root / "specs"
    handoff_dir = workspace_root / ".dadaia" / "handoff" / context_name
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs_dir,
            release_id=release_id,
            handoff_dir=handoff_dir,
            phase=_active_phase(specs_dir),
        )
    )
    return AuditWorkflow(
        context=context,
        release_id=release_id,
        run_store=build_lifecycle_run_store(workspace_root),
        runtime_factory=_handoff_driving_fake_factory(
            context=context,
            run_cwd=run_cwd,
            summary="fake audit worker: APPROVED",
            artifact_ref=f".dadaia/handoff/{context}/audit-step.handoff.json",
        ),
        context_selector=selector,
        default_runtime_kind=default_runtime_kind,
        prefix=prefix,
        policy_snapshot=policy_snapshot,
        # Bug fragment-workflows-never-persist-step-handoffs (v0.1.78 FR-B parity).
        handoff_resolver=build_workflow_handoff_resolver(workspace_root),
        # Bug gate-accepts-phantom-artifact-evidence: declared refs must exist.
        artifact_root=workspace_root,
    )


def build_research_workflow(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    default_runtime_kind: AgentRuntimeKind = AgentRuntimeKind.FAKE,
    prefix: PromptPrefix | None = None,
    cwd: Path | None = None,
    policy_snapshot: "WorkflowPolicySnapshot | None" = None,
) -> "ResearchWorkflow":
    """Compose the fragment-driven research workflow (v0.1.56 / FR2), born resolver-governed.

    Mirrors :func:`build_release_definition_workflow`: ``FAKE`` drives the
    scope→investigate→synthesis sequence end-to-end with an in-scope handoff ref;
    ``policy_snapshot`` is frozen onto the run before the first step.
    """
    from dadaia_workspace.features.lifecycle.context_selector import (
        ContextSelector,
        SpecContext,
    )
    from dadaia_workspace.features.lifecycle.workflows.research import ResearchWorkflow

    _guard_initialized(workspace_root)
    run_cwd = cwd or workspace_root
    context_name = resolve_bound_context_name(context) or context
    specs_dir = workspace_root / "repos" / context_name / "specs"
    if not specs_dir.is_dir():
        specs_dir = workspace_root / "specs"
    handoff_dir = workspace_root / ".dadaia" / "handoff" / context_name
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs_dir,
            release_id=release_id,
            handoff_dir=handoff_dir,
            phase=_active_phase(specs_dir),
        )
    )
    return ResearchWorkflow(
        context=context,
        release_id=release_id,
        run_store=build_lifecycle_run_store(workspace_root),
        runtime_factory=_handoff_driving_fake_factory(
            context=context,
            run_cwd=run_cwd,
            summary="fake research worker: APPROVED",
            artifact_ref=f".dadaia/handoff/{context}/research-step.handoff.json",
        ),
        context_selector=selector,
        default_runtime_kind=default_runtime_kind,
        prefix=prefix,
        policy_snapshot=policy_snapshot,
        # Bug fragment-workflows-never-persist-step-handoffs (v0.1.78 FR-B parity).
        handoff_resolver=build_workflow_handoff_resolver(workspace_root),
        # Bug gate-accepts-phantom-artifact-evidence: declared refs must exist.
        artifact_root=workspace_root,
    )


def _bug_report_runtime_factory(
    *,
    context: str,
    run_cwd: Path,
) -> Callable[[AgentRuntimeKind], AgentRuntimePort]:
    """Build the per-step runtime factory for the bug-report workflow (v0.1.56 / FR2).

    Unlike audit/research, the bug-report ``bug_write`` step scopes writes to the ADDITIVE
    ``specs/bugs/`` channel ONLY (A29), while its other steps scope to ``.dadaia/handoff/``.
    A single uniform handoff ref would out-of-scope-BLOCK at ``bug_write``; a uniform
    ``specs/bugs/`` ref would out-of-scope-BLOCK at the handoff-only steps. So the driving
    FAKE is **step-aware** (mirroring the ``_StepAwareFake`` in
    ``tests/unit/features/lifecycle/test_bug_report_workflow.py``): it returns an in-scope
    ``specs/bugs/`` ref for the ``bug_write`` step and an in-scope handoff ref for every other
    step, so ``--harness fake`` walks the whole intake→dedupe→bug_write sequence to COMPLETED.
    Real harnesses (pi/codex) resolve to their live adapters.
    """
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunRequest,
        AgentRunResult,
        AgentRunStatus,
    )
    from dadaia_workspace.features.lifecycle.workflows.bug_report import _BUG_WRITE_STEP

    class _BugReportDrivingFake:
        """A driving FAKE whose in-scope artifact ref depends on the current step (A29)."""

        def __init__(self, kind: AgentRuntimeKind) -> None:
            self._kind = kind

        def runtime_kind(self) -> AgentRuntimeKind:
            return self._kind

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            if (request.task_id or "").endswith(f":{_BUG_WRITE_STEP}"):
                ref = f"repos/{context}/specs/bugs/fake-bug-report-record.md"
            else:
                ref = f".dadaia/handoff/{context}/bug-report-step.handoff.json"
            # Gate now verifies refs EXIST (bug gate-accepts-phantom-artifact-evidence):
            # materialize the stub like FakeAgentRuntime's driving mode does.
            target = run_cwd / ref
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    '{"fake": true, "summary": "driving-fake stub artifact"}\n',
                    encoding="utf-8",
                )
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="fake bug-report worker: APPROVED",
                artifact_refs=(ref,),
                structured_output={"verdict": "APPROVED"},
            )

    def factory(kind: AgentRuntimeKind) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            return _BugReportDrivingFake(kind)
        return build_agent_runtime(kind, cwd=run_cwd)

    return factory


def build_bug_report_workflow(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    default_runtime_kind: AgentRuntimeKind = AgentRuntimeKind.FAKE,
    prefix: PromptPrefix | None = None,
    cwd: Path | None = None,
    policy_snapshot: "WorkflowPolicySnapshot | None" = None,
) -> "BugReportWorkflow":
    """Compose the fragment-driven bug-report workflow (v0.1.56 / FR2), born resolver-governed.

    Mirrors :func:`build_release_definition_workflow`, except the driving FAKE is **step-aware**
    (:func:`_bug_report_runtime_factory`) so the ADDITIVE ``bug_write`` step stays in-scope and
    ``--harness fake`` reaches COMPLETED. ``policy_snapshot`` is frozen onto the run before the
    first step; the per-step model reaches the adapter through the step's ``resolved_model``.
    """
    from dadaia_workspace.features.lifecycle.context_selector import (
        ContextSelector,
        SpecContext,
    )
    from dadaia_workspace.features.lifecycle.workflows.bug_report import BugReportWorkflow

    _guard_initialized(workspace_root)
    run_cwd = cwd or workspace_root
    context_name = resolve_bound_context_name(context) or context
    specs_dir = workspace_root / "repos" / context_name / "specs"
    if not specs_dir.is_dir():
        specs_dir = workspace_root / "specs"
    handoff_dir = workspace_root / ".dadaia" / "handoff" / context_name
    selector = ContextSelector(
        SpecContext(
            specs_dir=specs_dir,
            release_id=release_id,
            handoff_dir=handoff_dir,
            phase=_active_phase(specs_dir),
        )
    )
    return BugReportWorkflow(
        context=context,
        release_id=release_id,
        run_store=build_lifecycle_run_store(workspace_root),
        runtime_factory=_bug_report_runtime_factory(context=context, run_cwd=run_cwd),
        context_selector=selector,
        default_runtime_kind=default_runtime_kind,
        prefix=prefix,
        policy_snapshot=policy_snapshot,
        # Bug fragment-workflows-never-persist-step-handoffs (v0.1.78 FR-B parity).
        handoff_resolver=build_workflow_handoff_resolver(workspace_root),
        # Bug gate-accepts-phantom-artifact-evidence: declared refs must exist.
        artifact_root=workspace_root,
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
    from dadaia_workspace.cli.anchors import derive_cli_anchors
    from dadaia_workspace.features.backlog.removal_lifecycle import BacklogRemovalLifecycle
    from dadaia_workspace.features.backlog.subject_registry import build_registry

    _guard_initialized(workspace_root)
    specs_dir, source_root = _backlog_context_roots(workspace_root, context)
    registry = build_registry(
        source_root=source_root,
        catalog_path=specs_dir / "memory" / "product" / "catalog.json",
        alias_map_path=workspace_root / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs_dir,
        cli_anchors=derive_cli_anchors(),
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

    # Workflow model-governance control plane (Wave C). The panel reads the SAME governed
    # catalog + built-in profiles + policy store + run snapshots the CLI uses, through the
    # shared resolver — one source of truth, no second model table. The resolver +
    # overlay types are TYPE_CHECKING-only imports (used in the closure's string
    # annotations below).
    wf_catalog = build_workflow_model_profile_registry()
    policy_store = build_workflow_model_policy_store(workspace_root)
    run_store = build_lifecycle_run_store(workspace_root)
    fragment_loader = build_fragment_loader()
    # L1 agent model-governance (v0.1.65 FR8): store + re-render injected via the
    # dedicated factory (D-4 — the feature service never imports infrastructure).
    agent_policy_service = build_agent_model_policy_service(workspace_root)

    def _resolver_factory(
        context: str, *, overlay: "WorkflowModelPolicyOverlay | None" = None
    ) -> "WorkflowExecutionPolicyResolver":
        return build_workflow_policy_resolver(workspace_root, context=context, overlay=overlay)

    return {
        "index": render_index(service),
        "api_panel_status": render_api_servers(service),
        "health": render_health(),
        "api_contexts": render_api_contexts(service),
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
        # Workflow model-governance control plane (Wave C — T-28-C-01/02).
        "api_workflow_catalog": render_api_workflow_catalog(wf_catalog, _resolver_factory),
        "api_workflow_catalog_detail": render_api_workflow_catalog_detail(
            wf_catalog, _resolver_factory
        ),
        "api_workflow_model_profiles": render_api_workflow_model_profiles(),
        # Read-only fragment inspector (Wave D — T-28-D-01).
        "api_workflow_fragment": render_api_workflow_fragment(fragment_loader),
        "api_workflow_model_policy": render_api_workflow_model_policy(policy_store),
        "api_workflow_model_policy_validate": render_post_workflow_model_policy_validate(
            policy_store, _resolver_factory
        ),
        "api_workflow_model_policy_put": render_put_workflow_model_policy(
            policy_store, _resolver_factory
        ),
        # L1 agent model-governance control plane (v0.1.65 FR8 — T-65-11).
        "api_agent_model_policy": render_api_agent_model_policy(agent_policy_service),
        "api_agent_model_templates": render_api_agent_model_templates(agent_policy_service),
        "api_agent_model_policy_validate": render_post_agent_model_policy_validate(
            agent_policy_service
        ),
        "api_agent_model_policy_put": render_put_agent_model_policy(agent_policy_service),
        "api_lifecycle_runs": render_api_lifecycle_runs(run_store),
        "api_workflow_step_ledger": render_api_workflow_step_ledger(run_store),
        "api_sessions": render_api_sessions(service),
        "memory": render_memory(workspace_root),
        "memory_view": render_memory_wrapper(workspace_root),
        "static": render_static(),
    }
