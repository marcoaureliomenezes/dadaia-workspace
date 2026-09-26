"""Composition root — builds services with concrete infrastructure."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from dadaia_workspace.core.invocation import repo_owner

if TYPE_CHECKING:
    from dadaia_workspace.core.models.bugs import BugRecord
    from dadaia_workspace.features.certification import CertificationResult
    from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

from dadaia_workspace.core.handoff_index import HandoffIndex
from dadaia_workspace.core.workspace_resolver import not_initialized
from dadaia_workspace.features.chokepoints.denylist_scan import BaselinePatternLike
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.features.import_.service import ImportService
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.spec_context.service import SpecContextService, install_git_hooks
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

logger = logging.getLogger(__name__)


def _states_dir(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "states"


def _guard_initialized(workspace_root: Path) -> None:
    marker = _states_dir(workspace_root) / "spec_contexts.json"
    if not marker.exists():
        raise not_initialized(workspace_root)


def build_workspace_service(workspace_root: Path) -> WorkspaceService:
    return WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    )


def build_spec_context_service(workspace_root: Path) -> SpecContextService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)

    return SpecContextService(
        repo_owner=repo_owner,
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        install_hooks=install_git_hooks,
    )


def build_git_client() -> GitSubprocessClient:
    return GitSubprocessClient()


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


def build_git_object_reader() -> GitSubprocessObjectReader:
    """Composition-root seam for the push-range object reader (v0.9.0 FR1/FR7; ADR-0001:
    the sole adapter ``ci.push_gate_check`` reads the pushed range through).

    As of v0.4.3 T-043-15/FR11, the adapter this seam returns yields commit-object
    message bodies and (for a tag-ref push) annotated tag bodies IN ADDITION to blob
    content — see ``GitSubprocessObjectReader.new_objects``'s own docstring for the full
    contract.
    """
    return GitSubprocessObjectReader()


def build_bug_record_store(specs_dir: Path) -> "JsonlRecordStore[BugRecord]":
    """Composition-root seam for the generic bug-record JSONL store.

    Stays a container seam because the doctor reads the ledger through it
    (``bug_store_factory`` -> ``features.specs.doctor_governance.GovernanceValidator``);
    the ledger's ONE WRITER is the skill script ``dd-bug-resolution/scripts/bugs.py``
    which shares no code with this reader.

    Takes *specs_dir* directly — the SAME resolved directory the doctor's
    ``--specs-dir``/bind-resolution seam already produces (never a
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
    )


def build_export_service(workspace_root: Path) -> ExportService:
    _guard_initialized(workspace_root)
    states = _states_dir(workspace_root)
    return ExportService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
    )


def build_import_service(workspace_root: Path) -> ImportService:
    return ImportService(build_spec_context_service(workspace_root))


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
