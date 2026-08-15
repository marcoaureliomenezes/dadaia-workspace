"""Composition root — builds services with concrete infrastructure."""

import contextlib
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dadaia_workspace.core.protocols.git_client import GitClient
    from dadaia_workspace.features.agents.model_policy import AgentModelPolicyService
    from dadaia_workspace.features.certification import CertificationResult

from dadaia_workspace.core.exceptions import (
    NoActiveReleaseError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.protocols.git_object_reader import GitObjectReader
from dadaia_workspace.core.protocols.process_ancestry import ProcessAncestry
from dadaia_workspace.core.specs_resolver import repo_slug_for_context
from dadaia_workspace.core.specs_resolver import resolve_context as _core_resolve_context
from dadaia_workspace.features.academy.service import AcademyService
from dadaia_workspace.features.agents.reader import FileSystemAgentsProvider
from dadaia_workspace.features.chokepoints.denylist_scan import BaselinePatternLike
from dadaia_workspace.features.export.service import ExportService
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
from dadaia_workspace.features.panel.views.index import render_index
from dadaia_workspace.features.panel.views.memory import render_memory
from dadaia_workspace.features.panel.views.static import render_static
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
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.excel_reader import OpenpyxlExcelReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_course_store import JsonCourseStore
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore
from dadaia_workspace.infrastructure.markdown_agent_store import MarkdownAgentStore
from dadaia_workspace.infrastructure.process_ancestry_adapter import (
    LinuxProcAncestry,
    PsProcessAncestry,
    WindowsToolhelpAncestry,
)
from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe, build_pid_probe
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
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


def build_git_object_reader() -> GitObjectReader:
    """Composition-root seam for the ``GitObjectReader`` adapter (v0.9.0 FR1/FR7).

    The CLI layer must not import infrastructure directly (import-linter contract);
    ``push-gate-check`` composes the subprocess-backed reader here, exactly as
    :func:`build_git_client` does for the read-only git probe. A single concrete
    adapter today (subprocess-backed, cross-platform via the ``git`` executable on
    PATH) — no platform branching needed, unlike :func:`build_process_ancestry`.
    """
    from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader

    return GitSubprocessObjectReader()


def load_denylist_terms() -> tuple[tuple[str, str], ...]:
    """Composition-root seam over the operator privacy denylist (v0.9.0 FR3, source 1).

    ``push-gate-check`` reads operator terms through here rather than importing
    ``infrastructure.privacy_check`` directly (``cli-no-infrastructure``).
    """
    from dadaia_workspace.infrastructure.privacy_check import load_privacy_terms

    return load_privacy_terms()


def load_denylist_baseline_patterns() -> tuple[BaselinePatternLike, ...]:
    """Composition-root seam over the packaged baseline privacy patterns (v0.9.0 FR3,
    source 2) — same accessor :func:`load_denylist_terms` reuses the sibling of."""
    from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns

    return load_baseline_patterns()


def load_registry_context_identities(workspace_root: Path) -> tuple[tuple[str, str], ...]:
    """Composition-root seam over the Spec Context registry (v0.11.0 FR5, T-110-13).

    ``cli/commands/ci.py#_foreign_repo_slugs`` reads every registered context's
    ``(name, repo_slug)`` pair through here — mirroring :func:`load_denylist_terms` /
    :func:`load_denylist_baseline_patterns` — rather than importing
    ``infrastructure.json_context_store`` directly (``cli-no-infrastructure``).

    A5.4: a missing registry file already yields an empty result from
    :class:`JsonContextStore` itself (no exception); an EMPTY registry likewise yields
    an empty list. A MALFORMED registry — invalid JSON, an unsupported schema version,
    or a context row missing/mistyped a required field — is swallowed here into an
    empty tuple too: the push hook (``push-gate-check``) must never crash on registry
    state, only ever degrade to the ``repos/`` directory-derived set
    (``cli.commands.ci._foreign_repo_slugs``'s fallback union member).
    """
    from dadaia_workspace.core.exceptions import SchemaVersionError

    states = _states_dir(workspace_root)
    try:
        contexts = JsonContextStore(states).list_all()
    except (OSError, ValueError, KeyError, TypeError, SchemaVersionError):
        return ()
    return tuple((c.name, c.repo_slug) for c in contexts)


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


def is_source_repo_root(path: Path) -> bool:
    """Composition-root seam for the source-repo test (``cli`` may not import ``infrastructure``).

    ``ci preflight`` refuses outside the library checkout, and the test it uses must be the
    EXISTING one in ``infrastructure.workspace_guardrail`` — a second definition is how the
    two drift. The CLI reaches it here instead of importing infrastructure directly
    (``cli-no-infrastructure``).
    """
    from dadaia_workspace.infrastructure.workspace_guardrail import _is_source_repo_root

    return _is_source_repo_root(path)


def resolve_context(explicit: str | None = None, *, target_path: Path | None = None) -> str | None:
    """Composition-root seam for the single context-resolution authority (hooks path).

    T-50-02 (SPEC v0.5.0 FR1). ``core.specs_resolver`` is a forbidden direct import for
    ``hooks`` (``bind-resolution-seam-is-a-single-home``, ZERO ``ignore_imports``): the
    CLI routes through ``cli._specs_resolution`` (a sanctioned direct-import seam) and
    every hook routes here instead. A thin, transparent pass-through to
    :func:`dadaia_workspace.core.specs_resolver.resolve_context` (``DADAIA.md`` §3): no
    behavior of its own, so a hook consumer resolves the EXACT same rungs the CLI seam
    and every other consumer resolves.
    """
    return _core_resolve_context(explicit, target_path=target_path)


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


def build_server_registry_service(workspace_root: Path) -> ServerRegistryService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return ServerRegistryService(
        store=JsonServerRegistryStore(states),
        probe=OsProcessProbe(),
    )


def run_certification(workspace_root: Path, *, keep: bool = False) -> "CertificationResult":
    """Compose and run the disposable full-capability certification journey."""
    from dadaia_workspace.features.certification import certify
    from dadaia_workspace.infrastructure.certification_process import (
        SubprocessCertificationProcess,
    )

    return certify(workspace_root, SubprocessCertificationProcess(), keep=keep)


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
    context_name = _core_resolve_context(context)
    if not context_name:
        raise NoActiveReleaseError(
            "No bound context. Run `eval $(dadaia context bind <name> --mode read)` "
            "or pass --context <name>."
        )
    specs_dir = (
        workspace_root / "repos" / repo_slug_for_context(workspace_root, context_name) / "specs"
    )
    return ReportsNextService(
        specs_dir=specs_dir, reports_root=reports_root, context_name=context_name
    )


def build_reports_retention_service(workspace_root: Path) -> ReportRetentionService:
    """Compose ``ReportRetentionService`` for workspace runtime report state."""
    _guard_initialized(workspace_root)
    return ReportRetentionService(workspace_root)


def build_agent_model_policy_service(workspace_root: Path) -> "AgentModelPolicyService":
    """Compose the panel-facing L1 agent-model-policy service (v0.1.65 FR8 / T-65-10).

    Injects (D-4 — the features module carries no infrastructure import):

    - the concrete :class:`JsonAgentModelPolicyStore` (typed to the feature's store
      port), whose valid override targets are the 9 core agents;
    - the **re-render callable** — the agents-only ``public install`` path over both
      L1 projections (G-2 Apply semantics; profile-scoped like every install).
    """
    from dadaia_workspace.features.agents.model_policy import AgentModelPolicyService
    from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
        JsonAgentModelPolicyStore,
    )

    def _rerender_agents() -> list[str]:
        return build_public_service().install(workspace_root, target="all", only="agents")

    store = JsonAgentModelPolicyStore(workspace_root)
    return AgentModelPolicyService(store=store, rerender=_rerender_agents)


def _context_specs_dir(workspace_root: Path, context: str) -> Path:
    """Resolve a context's ``specs/`` tree (v0.1.57 FR2 / A1 — role→atom map wiring).

    A consumer context resolves
    to ``workspace_root/repos/<ctx>/specs``; the self-hosting library repo falls back to the
    workspace-root ``specs`` tree. All roots derive from ``workspace_root`` — never cwd.
    """
    context_name = _core_resolve_context(context) or context
    specs_dir = (
        workspace_root / "repos" / repo_slug_for_context(workspace_root, context_name) / "specs"
    )
    if not specs_dir.is_dir():
        specs_dir = workspace_root / "specs"
    return specs_dir


def resolve_context_specs_dir(workspace_root: Path, context: str) -> Path:
    """Public seam for :func:`_context_specs_dir` (FR3, v0.1.68).

    Lets a CLI verb resolve the same context→``specs/`` mapping the container
    uses internally, without duplicating the resolution logic.
    """
    return _context_specs_dir(workspace_root, context)


def _workspace_python_bin(workspace_root: Path) -> str | None:
    """The workspace venv interpreter, when provisioned — the runtime the bootstrap
    guarantees carries pytest (bug implementation-review-uses-parent-venv-without-
    pytest: the CLI may itself run from a foreign venv with no test toolchain).
    """
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    candidate = VenvPythonEnvironmentManager().python_executable(str(workspace_root))
    return candidate if Path(candidate).is_file() else None


#: Cache/artifact dirs that must never survive inside a context repo
#: (tmp-file-guardrail zero-tolerance list).
_REPO_CACHE_DIR_NAMES = (
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
)


def _repo_hygiene_sweeper(repo_root: Path) -> "Callable[[], None]":
    """Build the closure-time cache sweep for one context repo."""

    def _sweep() -> None:
        import shutil

        for name in _REPO_CACHE_DIR_NAMES:
            for path in repo_root.rglob(name):
                if path.is_dir() and ".git" not in path.parts:
                    shutil.rmtree(path, ignore_errors=True)

    return _sweep


def _definition_committer(repo_root: Path, release_id: str) -> "Callable[[], None] | None":
    """Build the definition-time commit of the context repo (Python-owned, post-success).

    Bug fake-release-definition-leaves-dirty-worktree: a completed release-definition
    leaves SPEC/PLAN/TASKS/backlog/ACTIVE.md uncommitted, and implementation-reviews
    then blocks at preflight on the dirty tree. Mirror of :func:`_closure_committer`
    — commits everything the definition produced with a conventional message and
    per-invocation identity fallbacks; ``None`` when the repo is not a git checkout
    (self-hosting fixtures). Push stays out of scope here (the baseline owns it).
    """
    if not (repo_root / ".git").exists():
        return None

    def _commit() -> None:
        import subprocess

        subprocess.run(  # noqa: S603 — fixed argv
            ["git", "-C", str(repo_root), "add", "-A"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        subprocess.run(  # noqa: S603 — fixed argv
            [
                "git",
                "-C",
                str(repo_root),
                "-c",
                "user.email=definition@dadaia.invalid",
                "-c",
                "user.name=dadaia-definition",
                "commit",
                "-m",
                f"definition({release_id}): approved release definition artifacts",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    return _commit


def _closure_committer(repo_root: Path, release_id: str) -> "Callable[[], None] | None":
    """Build the closure-time commit of the context repo (Python-owned, post-success).

    Commits everything the cycle produced (implementation, specs artifacts, memory)
    with a conventional message. Uses per-invocation identity fallbacks so a repo
    without user config still commits deterministically. ``None`` when the repo is not
    a git checkout (self-hosting fixtures).
    """
    if not (repo_root / ".git").exists():
        return None

    def _commit() -> None:
        import subprocess

        subprocess.run(  # noqa: S603 — fixed argv
            ["git", "-C", str(repo_root), "add", "-A"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        subprocess.run(  # noqa: S603 — fixed argv
            [
                "git",
                "-C",
                str(repo_root),
                "-c",
                "user.email=closure@dadaia.invalid",
                "-c",
                "user.name=dadaia-closure",
                "commit",
                "-m",
                f"closure({release_id}): finalize release artifacts",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    return _commit


def _memory_lint_gate(specs_dir: Path) -> "Callable[[], tuple[bool, str]] | None":
    """Build the closure-time memory-atom lint gate for one context specs dir.

    Runs the packaged ``lint-memory-atoms.py`` (the same script doctor LINT-1 shells
    out to); the gate passes only on exit 0 with no ``WARN:`` findings. ``None`` when
    the context has no memory dir or the script is not packaged (nothing to lint —
    never a silent fake-green: the doctor still covers drift after the fact).
    """
    memory_dir = specs_dir / "memory"
    script = Path(__file__).resolve().parent / "public" / "scripts" / "lint-memory-atoms.py"
    if not memory_dir.is_dir() or not script.is_file():
        return None

    def _gate() -> tuple[bool, str]:
        import subprocess
        import sys as _sys

        try:
            proc = subprocess.run(  # noqa: S603 — fixed argv, read-only lint run
                [_sys.executable, "-B", str(script), "--memory-dir", str(memory_dir)],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return True, f"memory lint could not run ({exc}); doctor covers it after the fact"
        merged = (proc.stdout + "\n" + proc.stderr).strip()
        ok = proc.returncode == 0 and "WARN:" not in merged
        # SPEC-DOC-002 leg (bug closure-generates-memory-atom-without-heading): the
        # lint script validates the headings PRESENT; a body with no markdown heading
        # at all sails through it — but doctor flags it post-closure. Enforce the
        # has-a-heading contract here so a heading-less atom never rides a green close.
        import re as _re

        heading_re = _re.compile(r"^#{1,6}\s+\S", _re.MULTILINE)
        fm_re = _re.compile(r"^---\n.*?\n---\n", _re.DOTALL)
        headingless: list[str] = []
        for md in sorted(memory_dir.rglob("*.md")):
            if md.name == "index.md":
                continue
            try:
                body = fm_re.sub("", md.read_text(encoding="utf-8"), count=1)
            except OSError:
                continue
            if heading_re.search(body) is None:
                headingless.append(str(md.relative_to(memory_dir)))
        if headingless:
            ok = False
            merged += "\nERROR: memory atom(s) with no markdown heading (doctor " + (
                "SPEC-DOC-002): " + ", ".join(headingless)
            )
        tail = "\n".join(merged.splitlines()[-30:])
        return ok, tail

    return _gate


def _normalize_memory_token_estimates(specs_dir: Path) -> None:
    """Recompute drifting ``token_estimate`` frontmatter values (derived data).

    Same formula as the packaged linter (``round(word_count * 1.35)``, contract-pinned
    by the render/lint suites). Only rewrites when the declared value drifts >20% —
    the linter's own warning threshold — so hand-tuned close values stay untouched.
    """
    import re as _re

    memory_dir = specs_dir / "memory"
    if not memory_dir.is_dir():
        return
    fm_re = _re.compile(r"^---\n(.*?)\n---\n", _re.DOTALL)
    for md in memory_dir.rglob("*.md"):
        try:
            content = md.read_text(encoding="utf-8")
        except OSError:
            continue
        match = fm_re.match(content)
        if match is None:
            continue
        body = content[match.end() :]
        declared_match = _re.search(r"^token_estimate:\s*(\d+)\s*$", match.group(1), _re.MULTILINE)
        if declared_match is None:
            continue
        declared = int(declared_match.group(1))
        actual = round(len(body.split()) * 1.35)
        if declared <= 0 or actual <= 0:
            continue
        if abs(actual - declared) / declared <= 0.20:
            continue
        updated = content.replace(f"token_estimate: {declared}", f"token_estimate: {actual}", 1)
        with contextlib.suppress(OSError):
            md.write_text(updated, encoding="utf-8")


def _memory_catalog_regenerator(specs_dir: Path) -> "Callable[[], None] | None":
    """Build the closure-time derived-catalog refresh for one context specs dir.

    Returns ``None`` when the context has no product-memory zone (nothing to derive).
    """
    if not (specs_dir / "memory" / "product").is_dir():
        return None

    def _regenerate() -> None:
        from dadaia_workspace.features.specs.catalog import (
            generate_catalog,
            write_catalog,
            write_index,
        )

        _normalize_memory_token_estimates(specs_dir)
        catalog = generate_catalog(specs_dir)
        write_catalog(specs_dir, catalog)
        write_index(specs_dir, catalog)

    return _regenerate


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

    # L1 agent model-governance (v0.1.65 FR8): store + re-render injected via the
    # dedicated factory (D-4 — the feature service never imports infrastructure).
    agent_policy_service = build_agent_model_policy_service(workspace_root)

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
        # L1 agent model-governance control plane (v0.1.65 FR8 — T-65-11).
        "api_agent_model_policy": render_api_agent_model_policy(agent_policy_service),
        "api_agent_model_templates": render_api_agent_model_templates(agent_policy_service),
        "api_agent_model_policy_validate": render_post_agent_model_policy_validate(
            agent_policy_service
        ),
        "api_agent_model_policy_put": render_put_agent_model_policy(agent_policy_service),
        "api_sessions": render_api_sessions(service),
        "memory": render_memory(workspace_root),
        "memory_view": render_memory_wrapper(workspace_root),
        "static": render_static(),
    }
