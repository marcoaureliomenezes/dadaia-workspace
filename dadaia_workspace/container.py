"""Composition root — builds services with concrete infrastructure."""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dadaia_workspace.core.models.bugs import BugRecord
    from dadaia_workspace.features.certification import CertificationResult
    from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

from dadaia_workspace.core.exceptions import (
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.handoff_index import HandoffIndex
from dadaia_workspace.features.chokepoints.denylist_scan import BaselinePatternLike
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.repos.service import ReposService
from dadaia_workspace.features.server_registry.service import ServerRegistryService
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.excel_reader import OpenpyxlExcelReader
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore
from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe, build_pid_probe
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

logger = logging.getLogger(__name__)


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
    # Injected so spec_context never imports its sibling feature; lazy because
    # `features.specs` pulls the doctor's jsonschema stack every other command skips.
    from dadaia_workspace.features.specs.canon import scaffold as scaffold_specs

    return SpecContextService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        scaffold_specs=scaffold_specs,
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


def build_git_object_reader() -> GitSubprocessObjectReader:
    """Composition-root seam for the push-range object reader (v0.9.0 FR1/FR7; ADR-0001:
    the sole adapter, shared by two CLI verbs — ``ci.push_gate_check`` and
    ``specs.doctor``'s ``head_sha``/``parent_sha`` resolution — so it stays a container
    seam rather than each verb constructing its own instance.

    As of v0.4.3 T-043-15/FR11, the adapter this seam returns yields commit-object
    message bodies and (for a tag-ref push) annotated tag bodies IN ADDITION to blob
    content — see ``GitSubprocessObjectReader.new_objects``'s own docstring for the full
    contract.
    """
    return GitSubprocessObjectReader()


def build_bug_record_store(specs_dir: Path) -> "JsonlRecordStore[BugRecord]":
    """Composition-root seam for the generic bug-record JSONL store (v0.5.0 FR2, AR-1
    ruling answer (b), ``specs/releases/0.5.0/reviews/S1-AR1-ruling.md`` §2).

    Stays a container seam (ADR-0001: a store builder collapses into its single
    consumer UNLESS two features share it) because two do: ``cli.commands.bugs``
    (``_service`` -> ``features.bugs.service.BugService``) and ``cli.commands.specs``
    (``bug_store_factory`` -> ``features.specs.doctor_governance.GovernanceValidator``).

    Takes *specs_dir* directly — the SAME resolved directory every ``dadaia bugs``
    verb's ``--specs-dir``/bind-resolution seam already produces (never a
    ``workspace_root``, which would silently assume ``<root>/specs`` and break every
    ``--specs-dir <tmp>`` test fixture and remote-context routing). The ledger's
    physical filename is ``BUGS.jsonl`` (T-050-10 physically migrated the ledger
    from the retired v5-event-shaped ``bugs.jsonl`` — the record model FR3
    produced, one line per bug id, commit provenance derived from git).
    """
    from dadaia_workspace.core.models.bugs import BugRecord
    from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

    return JsonlRecordStore(
        Path(specs_dir) / "bugs" / "BUGS.jsonl",
        to_dict=BugRecord.to_dict,
        from_dict=BugRecord.from_dict,
    )


def build_bug_record_validator() -> Callable[[Mapping[str, object]], None]:
    """Composition-root seam for ``bug-record-v1.schema.json`` validation (D9) — the
    ONE validation table, loaded once, reused by :meth:`~dadaia_workspace.features
    .bugs.service.BugService.register` (relocated from ``cli/commands/bugs.py``'s own
    schema loading, ``cli-no-infrastructure``: neither ``jsonschema``'s
    ``Draft202012Validator`` nor the packaged schema path belongs at the CLI layer).
    Raises ``jsonschema.exceptions.ValidationError`` on the first schema violation.
    """
    import json

    from jsonschema import Draft202012Validator

    package_root = Path(__file__).resolve().parent
    schema_path = package_root / "public" / "schemas" / "bugs" / "bug-record-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    def _validate(payload: Mapping[str, object]) -> None:
        validator.validate(payload)

    return _validate


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


@dataclass(frozen=True)
class RegistryContextIdentities:
    """Result of :func:`load_registry_context_identities` (SPEC v0.4.2 FR8(2)/GRILL P13).

    ``degraded`` is True only when the registry was present but genuinely malformed or
    otherwise unreadable and this seam fell back to an empty identity set — the caller
    (``cli/commands/ci.py#push_gate_check``) surfaces exactly one stderr note naming
    the degradation and the scan still proceeds (A8.3). ``degraded`` stays False for
    the legitimate "no registry file"/"empty registry" cases (A5.4) — those are not a
    failure, so they must never be reported as one.
    """

    identities: tuple[tuple[str, str], ...]
    degraded: bool = False


def load_registry_context_identities(workspace_root: Path) -> RegistryContextIdentities:
    """Composition-root seam over the Spec Context registry (v0.11.0 FR5, T-110-13).

    ``cli/commands/ci.py#_foreign_repo_slugs`` reads every registered context's
    ``(name, repo_slug)`` pair — one pair per repo in that context's ``all_repos()``
    (FR18/T-044-29: main + every FR15 associated repo, not the main repo alone) —
    through here, mirroring :func:`load_denylist_terms` /
    :func:`load_denylist_baseline_patterns` — rather than importing
    ``infrastructure.json_context_store`` directly (``cli-no-infrastructure``). Before
    FR18 an associated repo's slug never entered the foreign-name denylist layer, so a
    context's main-repo push was never protected against leaking a private associated
    repo's name.

    A5.4: a missing registry file already yields an empty result from
    :class:`JsonContextStore` itself (no exception); an EMPTY registry likewise yields
    an empty list — neither is a degradation. A MALFORMED registry — invalid JSON, an
    unsupported schema version, or a context row missing/mistyped a required field — IS
    a degradation (SPEC v0.4.2 FR8(2)): the push hook (``push-gate-check``) must never
    crash on registry state, but a malformed registry no longer shrinks the
    foreign-name layer SILENTLY either — the fallback to an empty identity tuple is
    reported via :attr:`RegistryContextIdentities.degraded`, and the caller surfaces
    exactly one stderr note naming it before falling back to the ``repos/``
    directory-derived set (``cli.commands.ci._foreign_repo_slugs``'s fallback union
    member).
    """
    from dadaia_workspace.core.exceptions import SchemaVersionError

    states = _states_dir(workspace_root)
    try:
        contexts = JsonContextStore(states).list_all()
    except (OSError, ValueError, KeyError, TypeError, SchemaVersionError):
        return RegistryContextIdentities(identities=(), degraded=True)
    return RegistryContextIdentities(
        identities=tuple((c.name, repo.slug) for c in contexts for repo in c.all_repos()),
        degraded=False,
    )


def is_source_repo_root(path: Path) -> bool:
    """Composition-root seam for the source-repo test (``cli`` may not import ``infrastructure``).

    ``ci preflight`` refuses outside the library checkout, and the test it uses must be the
    EXISTING one in ``infrastructure.workspace_guardrail`` — a second definition is how the
    two drift. The CLI reaches it here instead of importing infrastructure directly
    (``cli-no-infrastructure``).
    """
    from dadaia_workspace.infrastructure.workspace_guardrail import _is_source_repo_root

    return _is_source_repo_root(path)


def build_doctor_service(workspace_root: Path) -> DoctorService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return DoctorService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        pid_probe=build_pid_probe(),
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


def build_handoff_index(workspace_root: Path) -> HandoffIndex:
    """Compose the workspace-rooted :class:`HandoffIndex` (release 0.5.1 K6).

    Construction is cheap (no schema load) — schema loading happens lazily, once, on
    the first ``validate_file``/``validate_all`` call, from
    ``workspace_root/.dadaia/agentic/schemas/handoff-v1.schema.json``.

    Args:
        workspace_root: Root directory of the initialized dadaia workspace.
    """
    return HandoffIndex(workspace_root)
