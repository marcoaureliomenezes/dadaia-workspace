"""Post-install transaction for state, projections, doctors, and capabilities."""

from __future__ import annotations

import shutil
import uuid
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

from dadaia_workspace.features.capabilities import build_capabilities
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
        states_dir = workspace_root / ".dadaia" / "states"
        plan = plan_migration(states_dir)
        if not plan.already_v2:
            execute_migration(states_dir, workspace_root)
        steps.append("state-schema-v2")

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

        public_reports = public_service.doctor(workspace_root)
        drift = [
            item
            for item in public_reports
            if item.startswith("[missing]") or item.startswith("[drift]")
        ]
        if drift:
            raise RuntimeError("public doctor failed: " + "; ".join(drift[:8]))
        steps.append("public-doctor")

        workspace_issues = doctor_service.check()
        if workspace_issues:
            summary = "; ".join(
                f"{issue.code}: {issue.description}" for issue in workspace_issues[:8]
            )
            raise RuntimeError("workspace doctor failed: " + summary)
        steps.append("workspace-doctor")

        capabilities = build_capabilities()
        if capabilities.get("schema_version") != "dadaia-capabilities-v1":
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
