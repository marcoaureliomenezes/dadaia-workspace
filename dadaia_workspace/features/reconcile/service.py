"""Post-install transaction for state, projections, doctors, and capabilities."""

from __future__ import annotations

import shutil
import uuid
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from dadaia_workspace.features.capabilities import build_capabilities
from dadaia_workspace.features.migrate.legacy_dadaia_dirs import quarantine_legacy_dadaia_dirs
from dadaia_workspace.features.migrate.state_v2 import execute_migration, plan_migration


@dataclass(frozen=True)
class ReconcileResult:
    ok: bool
    expected_version: str
    actual_version: str
    steps: tuple[str, ...]
    error: str | None = None
    rollback_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _distribution_version() -> str:
    try:
        return metadata.version("dadaia-workspace")
    except metadata.PackageNotFoundError:
        return "0+source"


def _snapshot_state(workspace_root: Path) -> tuple[Path, dict[Path, Path | None]]:
    backup_root = workspace_root / ".dadaia" / "tmp" / "reconcile" / f"state-{uuid.uuid4().hex}"
    backup_root.mkdir(parents=True, exist_ok=False)
    targets = (
        workspace_root / ".dadaia" / "states" / "spec_contexts.json",
        workspace_root / ".dadaia" / "states" / "primary_context.json",
    )
    snapshots: dict[Path, Path | None] = {}
    for target in targets:
        if target.is_file():
            backup = backup_root / target.name
            shutil.copy2(target, backup)
            snapshots[target] = backup
        else:
            snapshots[target] = None
    return backup_root, snapshots


def _restore_state(snapshots: dict[Path, Path | None]) -> None:
    for target, backup in snapshots.items():
        if backup is None:
            target.unlink(missing_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)


def reconcile_workspace(
    workspace_root: Path,
    *,
    expected_version: str,
    public_service: Any,
    doctor_service: Any,
    actual_version: str | None = None,
) -> ReconcileResult:
    """Converge a workspace after an exact candidate wheel has been installed."""
    actual = actual_version or _distribution_version()
    if actual != expected_version:
        return ReconcileResult(
            ok=False,
            expected_version=expected_version,
            actual_version=actual,
            steps=(),
            error=f"provider version mismatch: expected {expected_version}, found {actual}",
            rollback_required=False,
        )

    steps: list[str] = ["provider-version"]
    backup_root, snapshots = _snapshot_state(workspace_root)
    projections_started = False
    try:
        # Bug reconcile-root-owned-agentic: a mixed-ownership workspace (e.g.
        # .dadaia/agentic owned by root from a previous sudo run) fails the projection
        # step mid-transaction with a bare "Permission denied". Preflight it: the
        # transaction never starts, and the operator gets the exact path + repair
        # command instead of a rollback-flavored ok:false.
        ownership_error = _ownership_preflight(workspace_root)
        if ownership_error is not None:
            return ReconcileResult(
                ok=False,
                expected_version=expected_version,
                actual_version=actual,
                steps=(),
                error=ownership_error,
            )

        states_dir = workspace_root / ".dadaia" / "states"
        plan = plan_migration(states_dir)
        if not plan.already_v2:
            execute_migration(states_dir, workspace_root)
        steps.append("state-schema-v2")

        # Known-legacy .dadaia subdirs (pre-0.2.x leftovers) are quarantined — moved,
        # never deleted — so ROOT-4 can hold without blocking convergence of a
        # long-lived upgraded workspace (bug reconcile-legacy-dadaia-dirs-unmigrated).
        quarantine_legacy_dadaia_dirs(workspace_root)
        steps.append("legacy-dir-quarantine")

        public_service.stage(workspace_root)
        steps.append("public-stage")
        projections_started = True
        public_service.install(
            workspace_root,
            target="all",
            force=True,
            scope="all",
            only=None,
        )
        steps.append("public-install")

        public_report = public_service.doctor(workspace_root)
        blocking = [line.render() for line in public_report.lines if line.status.blocking]
        if blocking:
            raise RuntimeError("public doctor failed: " + "; ".join(blocking[:8]))
        steps.append("public-doctor")

        workspace_issues = doctor_service.check()
        if workspace_issues:
            summary = "; ".join(
                f"{issue.code}: {issue.description}" for issue in workspace_issues[:8]
            )
            raise RuntimeError("workspace doctor failed: " + summary)
        steps.append("workspace-doctor")

        capabilities = build_capabilities()
        if capabilities.get("schema_version") != "dadaia-capabilities-v2":
            raise RuntimeError("capability canary returned an unsupported schema version")
        if capabilities["provider"]["distribution_version"] != expected_version:
            raise RuntimeError("capability canary does not identify the expected provider")
        steps.append("capability-canary")
    except Exception as exc:  # noqa: BLE001 - transaction boundary returns structured failure.
        _restore_state(snapshots)
        shutil.rmtree(backup_root, ignore_errors=True)
        return ReconcileResult(
            ok=False,
            expected_version=expected_version,
            actual_version=actual,
            steps=tuple(steps),
            error=str(exc),
            rollback_required=projections_started,
        )

    shutil.rmtree(backup_root, ignore_errors=True)
    return ReconcileResult(
        ok=True,
        expected_version=expected_version,
        actual_version=actual,
        steps=tuple(steps),
    )


def _ownership_preflight(workspace_root: Path) -> str | None:
    """Return an actionable error when the runtime user cannot write under ``.dadaia``.

    Bug reconcile-root-owned-agentic: a previous elevated run may leave
    ``.dadaia/agentic`` (or ``.dadaia`` itself) owned by another user (root), so the
    projection step later dies mid-transaction with a bare PermissionError. This
    preflight names the offending path, its owner, and the exact repair command —
    the transaction never starts on a guaranteed failure. Returns ``None`` when every
    checked path is writable by the current effective uid (or ownership cannot be
    determined, e.g. non-POSIX platforms such as Windows, where ``pwd``/``geteuid``
    do not exist).
    """
    import os

    if not hasattr(os, "geteuid"):
        return None  # Non-POSIX platform: ownership semantics do not apply.
    try:
        import pwd
    except ImportError:  # pragma: no cover — Windows has no account database
        pwd = None  # type: ignore[assignment]

    def _check(path: Path) -> str | None:
        if not path.exists():
            return None
        try:
            st = path.stat()
        except OSError:
            return None
        if st.st_uid != os.geteuid():
            owner: str
            if pwd is not None:
                try:
                    owner = pwd.getpwuid(st.st_uid).pw_name
                except KeyError:
                    owner = str(st.st_uid)
            else:
                owner = str(st.st_uid)
            return (
                f"{path} is owned by '{owner}' (uid {st.st_uid}), not by the current user "
                f"(uid {os.geteuid()}) — reconcile cannot write projections there. "
                f"Repair with: sudo chown -R {os.geteuid()}:{os.getegid()} "
                f"{workspace_root / '.dadaia'} (or fix the elevated process that created it)."
            )
        if not os.access(path, os.W_OK):
            return (
                f"{path} is not writable by the current user (mode {oct(st.st_mode & 0o777)}) — "
                "reconcile cannot write projections there."
            )
        return None

    dadaia_dir = workspace_root / ".dadaia"
    for candidate in (dadaia_dir, dadaia_dir / "agentic"):
        problem = _check(candidate)
        if problem is not None:
            return problem
    return None
