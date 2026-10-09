"""Post-install transaction for state, projections, doctors, and capabilities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.provider_version import provider_version


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


def reconcile_workspace(
    workspace_root: Path,
    *,
    context_store: JsonContextStore | None = None,
    version: Callable[[], str] = lambda: provider_version() or "0+source",
    migration_plan: Callable[[JsonContextStore], Any] | None = None,
    migrate: Callable[[JsonContextStore, Path], None] | None = None,
    expected_version: str,
    public_service: Any,
    doctor_service: Any,
    actual_version: str | None = None,
) -> ReconcileResult:
    """Converge a workspace after an exact candidate wheel has been installed."""
    actual = actual_version or version()
    if actual != expected_version:
        return ReconcileResult(
            ok=False,
            expected_version=expected_version,
            actual_version=actual,
            steps=(),
            error=f"provider version mismatch: expected {expected_version}, found {actual}",
            rollback_required=False,
        )
    if context_store is None or migration_plan is None or migrate is None:
        return ReconcileResult(False, expected_version, actual, (), "dependencies not composed")

    steps: list[str] = ["provider-version"]
    registry_snapshot = context_store.snapshot()
    primary = context_store.states_dir / "primary_context.json"
    primary_snapshot = primary.read_bytes() if primary.is_file() else None
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

        plan = migration_plan(context_store)
        if not plan.already_v2:
            migrate(context_store, workspace_root)
        steps.append("state-schema-v2")

        public_service.stage(workspace_root)
        steps.append("public-stage")
        projections_started = True
        public_service.install(
            workspace_root,
            force=True,
        )
        steps.append("public-install")

        public_report = public_service.doctor(workspace_root)
        blocking = [line.render() for line in public_report.lines if line.status.blocking]
        if blocking:
            raise RuntimeError("public doctor failed: " + "; ".join(blocking[:8]))
        steps.append("public-doctor")

        # Context invariants only: operator slop never blocks an upgrade; `certify` and
        # `dadaia doctor` judge the whole workspace (DEC-13 a).
        broken = doctor_service.check()
        if broken:
            summary = "; ".join(f"{issue.code}: {issue.message}" for issue in broken[:8])
            raise RuntimeError("context invariants failed: " + summary)
        steps.append("context-invariants")

        if version() != expected_version:
            raise RuntimeError("capability canary does not identify the expected provider")
        steps.append("capability-canary")
    except Exception as exc:  # noqa: BLE001 - transaction boundary returns structured failure.
        context_store.restore(registry_snapshot)
        atomic_write(primary, primary_snapshot)
        return ReconcileResult(
            ok=False,
            expected_version=expected_version,
            actual_version=actual,
            steps=tuple(steps),
            error=str(exc),
            rollback_required=projections_started,
        )

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
