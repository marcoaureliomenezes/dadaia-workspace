"""Composition root — builds services with concrete infrastructure."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dadaia_workspace.features.certification import CertificationResult

from dadaia_workspace.core.workspace_resolver import not_initialized
from dadaia_workspace.features.chokepoints.denylist_scan import BaselinePatternLike
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.features.import_.service import ImportService
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.spec_context.service import (
    SpecContextService,
    WorktreeRows,
    install_git_hooks,
)
from dadaia_workspace.features.spec_context.sweep import hold
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.ledger_scripts import worktree_rows
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

logger = logging.getLogger(__name__)


def states_dir(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "states"


def _guard_initialized(workspace_root: Path) -> None:
    marker = states_dir(workspace_root) / "spec_contexts.json"
    if not marker.exists():
        raise not_initialized(workspace_root)


def build_workspace_service(workspace_root: Path) -> WorkspaceService:
    return WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
        hold=hold,
    )


def build_spec_context_service(
    workspace_root: Path, *, rows: WorktreeRows = worktree_rows
) -> SpecContextService:
    _guard_initialized(workspace_root)
    states = states_dir(workspace_root)

    return SpecContextService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        install_hooks=install_git_hooks,
        secret_scan=scan_publish_candidates,
        worktree_rows=rows,
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


def scan_publish_candidates(repo: Path, rels: list[str]) -> dict[str, str]:
    """AC5.6: the pre-push matcher, in-process, over the files baseline is about
    to commit, before any hook could see them.
    Read as the object reader reads a blob: undecodable bytes are scanned by path only."""
    from dadaia_workspace.core.models.git_scan import ScannedObject
    from dadaia_workspace.features.chokepoints.denylist_scan import scan_objects

    objects = []
    for rel in rels:
        if (repo / rel).is_file():
            data = (repo / rel).read_bytes()
            try:
                objects.append(ScannedObject(rel, "", data.decode("utf-8"), decodable=True))
            except UnicodeDecodeError:
                objects.append(ScannedObject(rel, "", "", decodable=False))
    outcome = scan_objects(objects, load_denylist_terms(), load_denylist_baseline_patterns())
    return {h.path: f"{h.source_layer} '{h.masked_term}' (line {h.line})" for h in outcome.hits}


def build_doctor_service(
    workspace_root: Path, *, rows: WorktreeRows = worktree_rows
) -> DoctorService:
    _guard_initialized(workspace_root)
    states = states_dir(workspace_root)
    return DoctorService(
        context_store=JsonContextStore(states),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        projection=build_public_service().verdict,
        worktree_rows=rows,
    )


def build_export_service(workspace_root: Path) -> ExportService:
    _guard_initialized(workspace_root)
    states = states_dir(workspace_root)
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
