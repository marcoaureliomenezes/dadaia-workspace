"""Composition root — builds services with concrete infrastructure."""

import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from dadaia_workspace.features.certification import CertificationResult

from dadaia_workspace.core.cli_line import git_line
from dadaia_workspace.core.exceptions import DadaiaError, GitSyncError
from dadaia_workspace.core.models.git_scan import GitObjectReadError, GitRunError
from dadaia_workspace.core.platform import act, write_text
from dadaia_workspace.core.workspace_resolver import not_initialized
from dadaia_workspace.features.capabilities import distribution_version
from dadaia_workspace.features.chokepoints.denylist_scan import BaselinePatternLike
from dadaia_workspace.features.chokepoints.push_gate import read_failure_fix
from dadaia_workspace.features.export.service import ExportService, new_scratch, scratch_fix
from dadaia_workspace.features.import_.service import ImportService
from dadaia_workspace.features.migrate.state_v2 import execute_migration, plan_migration
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.reconcile import ReconcileResult
from dadaia_workspace.features.reconcile import reconcile_workspace as _reconcile_workspace
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


def build_context_store(workspace_root: Path) -> JsonContextStore:
    return JsonContextStore(states_dir(workspace_root))


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
    return SpecContextService(
        context_store=build_context_store(workspace_root),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        install_hooks=install_git_hooks,
        secret_scan=scan_publish_candidates,
        worktree_rows=rows,
    )


def build_git_client() -> GitSubprocessClient:
    return GitSubprocessClient()


def build_public_service() -> PublicAssetService:
    # The agent-model-policy overlay loader is injected here so the
    # features-layer service never imports the infrastructure store directly.
    from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
        JsonAgentModelPolicyStore,
    )

    return PublicAssetService(
        public_assets=FileSystemPublicAssetManager(),
        agent_policy_loader=lambda root: JsonAgentModelPolicyStore(root).load(),
    )


def build_git_object_reader() -> GitSubprocessObjectReader:
    """Composition-root seam for the push-range object reader: the sole adapter
    ``ci.push_gate_check`` reads the pushed range through.

    The adapter this seam returns yields commit-object
    message bodies and (for a tag-ref push) annotated tag bodies IN ADDITION to blob
    content — see ``GitSubprocessObjectReader.new_objects``'s own docstring for the full
    contract.
    """
    return GitSubprocessObjectReader()


def load_denylist_terms() -> tuple[tuple[str, str], ...]:
    """Composition-root seam over the operator privacy denylist.

    ``push-gate-check`` reads operator terms through here rather than importing
    ``infrastructure.privacy_check`` directly (``cli-no-infrastructure``).
    """
    from dadaia_workspace.infrastructure.privacy_check import load_privacy_terms

    return load_privacy_terms()


def load_denylist_baseline_patterns() -> tuple[BaselinePatternLike, ...]:
    """Composition-root seam over the packaged baseline privacy patterns, the sibling of
    :func:`load_denylist_terms`."""
    from dadaia_workspace.infrastructure.privacy_check import load_baseline_patterns

    return load_baseline_patterns()


def scan_publish_candidates(repo: Path, rels: list[str]) -> dict[str, str]:
    """The pre-push matcher, in-process, over the files baseline is about
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


def scan_bundle(workspace_root: Path, bundle: Path, repo: Path) -> dict[str, str]:
    """The pre-push matcher over the objects *bundle* adds to *repo*, as the push gate reads
    them: git's own exit statuses tell the cases apart (`list-heads` fails: a damaged header;
    `verify` fails: a missing prerequisite), a scratch bare repo borrows *repo*'s objects and
    `origin` refs, and the bundle is unbundled there. Nothing is written into *repo*.
    A failure raises `DadaiaError` relaying git's reason, with the act that clears its cause."""
    from dadaia_workspace.features.chokepoints.denylist_scan import scan_objects

    # An open lane's bundle was written a moment ago: its damage is git's, never the operator's.
    damaged = (
        act("operator", f"rule whether {bundle} is restored from a copy or discarded")
        if bundle.is_relative_to(workspace_root / ".dadaia" / "dist")
        else git_line(repo, "fsck")
    )

    def refuse(why: str, fix: str) -> NoReturn:
        raise DadaiaError(f"{bundle.name} cannot be scanned ({why})", fix=fix)

    def git(cwd: Path, *args: str, why: str, fix: str) -> str:
        try:
            return GitSubprocessClient().git(cwd, *args)
        except GitSyncError as exc:
            refuse(f"{why}: {exc.message.partition(':\n')[2].strip()}", fix)
        except (OSError, TimeoutError):
            refuse("git could not run", read_failure_fix(GitRunError("git"), repo))

    try:
        bundle.open("rb").close()
    except OSError as exc:
        refuse(
            type(exc).__name__, act("agent", f"make {bundle} readable, then run the export again")
        )
    heads = git(
        repo, "bundle", "list-heads", str(bundle), why="its header is unreadable", fix=damaged
    )
    if not heads:
        refuse("it holds no ref", damaged)
    git(
        repo,
        "bundle",
        "verify",
        str(bundle),
        why="its repo lacks a prerequisite",
        fix=git_line(repo, "fetch", "origin"),
    )
    tmp = workspace_root / ".dadaia" / "tmp"
    with new_scratch(tmp, "scan-") as name:
        scratch, fsck = Path(name), git_line(repo, "fsck")
        git(scratch, "init", "-q", "--bare", why="no scratch repo", fix=fsck)
        store = git(
            repo,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "objects",
            why="no repo",
            fix=fsck,
        )
        try:
            write_text(scratch / "objects" / "info" / "alternates", store + "\n")
        except OSError as exc:
            refuse(type(exc).__name__, scratch_fix(tmp))
        git(
            scratch,
            "fetch",
            "-q",
            str(repo),
            "+refs/remotes/origin/*:refs/remotes/origin/*",
            why="no origin refs",
            fix=fsck,
        )
        git(scratch, "bundle", "unbundle", str(bundle), why="git refused it", fix=scratch_fix(tmp))
        try:
            found = GitSubprocessObjectReader().new_objects(scratch, heads.split()[0], "")
            outcome = scan_objects(found, load_denylist_terms(), load_denylist_baseline_patterns())
        except GitObjectReadError as exc:
            refuse(str(exc), read_failure_fix(exc, repo))
    return {h.path: f"{h.source_layer} '{h.masked_term}' (line {h.line})" for h in outcome.hits}


def build_doctor_service(
    workspace_root: Path, *, rows: WorktreeRows = worktree_rows
) -> DoctorService:
    _guard_initialized(workspace_root)
    return DoctorService(
        context_store=build_context_store(workspace_root),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        projection=build_public_service().verdict,
        worktree_rows=rows,
    )


def build_export_service(workspace_root: Path) -> ExportService:
    _guard_initialized(workspace_root)
    return ExportService(
        context_store=build_context_store(workspace_root),
        workspace_root=workspace_root,
        scan_bundle=partial(scan_bundle, workspace_root),
    )


def build_import_service(workspace_root: Path) -> ImportService:
    return ImportService(build_spec_context_service(workspace_root))


def reconcile_workspace(
    workspace_root: Path, *, expected_version: str, actual_version: str | None = None
) -> ReconcileResult:
    return _reconcile_workspace(
        workspace_root,
        context_store=build_context_store(workspace_root),
        version=distribution_version,
        migration_plan=plan_migration,
        migrate=execute_migration,
        expected_version=expected_version,
        public_service=build_public_service(),
        doctor_service=build_doctor_service(workspace_root),
        actual_version=actual_version,
    )


def run_certification(workspace_root: Path, *, keep: bool = False) -> "CertificationResult":
    """Compose and run the disposable full-capability certification journey."""
    from dadaia_workspace.features.certification import certify
    from dadaia_workspace.infrastructure.certification_process import (
        SubprocessCertificationProcess,
    )

    return certify(workspace_root, SubprocessCertificationProcess(), keep=keep)
