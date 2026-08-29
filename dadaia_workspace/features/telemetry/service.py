"""TelemetryService — lazy on-request telemetry orchestrator (T-AM-12).

Design decisions implemented:
    D-AM-11  — Lazy on-request + cache 30 s (no daemon, no cron, no watcher).
    D-AM-15  — SQLite WAL in ~/.dadaia/state/telemetry/telemetry.sqlite.
    T6       — Guard os.getuid() != 0 in constructor.
    Architect D6 — Process lock via TelemetryRefreshLock protocol (T-018-06).

Refresh logic:
    1. Acquire LOCK_EX | LOCK_NB on state_dir/telemetry.lock via TelemetryRefreshLock.
       If another process holds it, skip refresh and return.
    2. If now - last_refresh < CACHE_TTL_SECONDS, return immediately (cache hit).
    3. Integrity-check the existing file; quarantine + degrade if corrupt (T-AM-21).
    4. Open the store's write connection + migrate.
    5. Run every reader in ``readers`` (K8: ``Reader.ingest(store, now)``).
    6. Backfill costs: UPDATE events WHERE cost_micro_usd IS NULL AND model known.
    7. Update last_refresh timestamp.
    8. Release lock.

K8 (0.5.1): the store is now the ONE connection owner — this service never
touches a ``sqlite3.Connection`` or a DAO's private ``_conn`` (see
``features/telemetry/store.py``).
"""

from __future__ import annotations

import datetime
import logging
import os
import pathlib
from collections.abc import Callable, Sequence
from typing import Any, Protocol

from dadaia_workspace.core.exceptions import PlatformSecurityError
from dadaia_workspace.core.models.telemetry import (
    AgentListResult,
    RecentSession,
    SessionAggregate,
)
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.protocols.platform_services import FilePermissionSetter
from dadaia_workspace.core.protocols.telemetry_lock import TelemetryRefreshLock
from dadaia_workspace.features.telemetry import budget as _budget
from dadaia_workspace.features.telemetry.reader.adapters import Reader
from dadaia_workspace.features.telemetry.store import TelemetryStore

logger = logging.getLogger(__name__)

_DEFAULT_STATE_DIR = pathlib.Path("~/.dadaia/state/telemetry").expanduser()


class _Aggregator(Protocol):
    """The read-side surface TelemetryService delegates its query methods to."""

    def list_agents(
        self, *, window_days: int, context_slug: str | None, limit: int
    ) -> AgentListResult: ...

    def list_sessions_by_agent(
        self, *, agent_id: str, limit: int, offset: int
    ) -> list[RecentSession]: ...

    def aggregate_sessions(self, *, runtime: str) -> SessionAggregate: ...


class _PricingModule(Protocol):
    """The features/telemetry/pricing surface the cost-backfill step needs."""

    def compute_cost(
        self, usage: dict[str, Any], model: str, when: datetime.date
    ) -> int | None: ...


def _default_refresh_lock() -> TelemetryRefreshLock:
    """Return the platform-appropriate TelemetryRefreshLock implementation.

    Routes via ``PLATFORM.has_fcntl`` (the sole authorized platform capability flag,
    v0.1.76 T-4 FR6). The ``PLATFORM`` re-import here is deliberate (shadowing the
    module-level binding used elsewhere in this file, e.g. ``has_posix_chmod``): it keeps
    the capability read INSIDE the function body at call time — matching
    ``spec_context.locking``'s and ``container._select_lock_adapter``'s lazy-read pattern
    (module-level platform reads are forbidden per SPEC §4.1) and, practically, keeps this
    seam patchable the same way theirs are
    (``monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", ...)``) — a
    module-level ``from ... import PLATFORM`` binds the object at import time and would
    NOT observe a later patch of the source module's attribute. The adapter-module
    imports stay lazy so importing this module never triggers the Windows adapter's
    module-level guard on Linux/macOS.
    """
    from dadaia_workspace.core.platform import PLATFORM as _platform

    if _platform.has_fcntl:
        from dadaia_workspace.infrastructure.telemetry_lock_posix import (
            PosixTelemetryRefreshLock,
        )

        return PosixTelemetryRefreshLock()
    from dadaia_workspace.infrastructure.telemetry_lock_windows import (
        WindowsTelemetryRefreshLock,
    )

    return WindowsTelemetryRefreshLock()


class TelemetryService:
    """Aggregate entry-point for telemetry: ingest, cache, and query.

    Dependencies are injected at construction time so each can be swapped
    with a fake in tests (no mocks required).

    Parameters
    ----------
    store:
        The single ``TelemetryStore`` this service ingests into and backfills
        costs against (K8 — the one connection owner; this service never opens
        a ``sqlite3.Connection`` itself).
    readers:
        Every ingestion source to run on each refresh — ``Reader.ingest(store, now)``.
    clock:
        Returns float (monotonic seconds) — drives the refresh cache TTL.
    aggregator:
        TelemetryAggregator instance (features/telemetry/aggregator/queries.py).
    pricing_module:
        The features/telemetry/pricing module (or compatible stub).  Must
        expose compute_cost() and (optionally) PRICING_TABLE.
    workspace_root:
        pathlib.Path to the dadaia workspace root.
    state_dir:
        pathlib.Path where the SQLite file and lock file are stored.
        Defaults to ~/.dadaia/state/telemetry/.
    spec_context_service:
        Forwarded to the aggregator (not used directly by the service).
    refresh_lock:
        TelemetryRefreshLock implementation for serializing concurrent refreshes.
        Defaults to a platform-appropriate adapter (POSIX or Windows).
    permission_setter:
        Optional ``FilePermissionSetter`` for restricting the telemetry state
        directory permissions.  When ``None`` (default), falls back to the
        direct ``os.chmod`` call (Tier-2: if a setter is provided and raises
        ``PlatformSecurityError``, telemetry degrades to ``None``; the panel
        starts but telemetry endpoints return 503).
    _getuid_fn:
        Injectable for tests: returns int (current uid).
    """

    def __init__(
        self,
        store: TelemetryStore,
        readers: Sequence[Reader],
        clock: Callable[[], float],
        *,
        aggregator: _Aggregator,
        pricing_module: _PricingModule,
        workspace_root: pathlib.Path,
        state_dir: pathlib.Path = _DEFAULT_STATE_DIR,
        spec_context_service: Any = None,
        refresh_lock: TelemetryRefreshLock | None = None,
        permission_setter: FilePermissionSetter | None = None,
        _getuid_fn: Callable[[], int] | None = None,
    ) -> None:
        # T6: refuse uid=0
        # Use getattr guard for non-POSIX platforms where os.getuid is absent (FR-08).
        def _fallback_uid() -> int:
            return 1000

        _raw_getuid: Any = _getuid_fn or getattr(os, "getuid", _fallback_uid)
        getuid: Callable[[], int] = _raw_getuid
        if getuid() == 0:
            raise PermissionError(
                "TelemetryService must not run as root (uid=0). "
                "This prevents unintended access to other users' ~/.claude/projects/ data."
            )

        self._store = store
        self._readers = readers
        self._clock = clock
        self._aggregator = aggregator
        self._pricing = pricing_module
        self._workspace_root = workspace_root
        self._state_dir = state_dir
        self._scs = spec_context_service
        self._refresh_lock: TelemetryRefreshLock = refresh_lock or _default_refresh_lock()
        self._permission_setter: FilePermissionSetter | None = permission_setter

        # Ensure state directory exists with strict permissions (T-AM-20 / devops T2).
        # We create parents first, then restrict the leaf dir to owner-only (0o700) so that
        # the telemetry state is only readable by the owning user. The restriction is routed
        # through the injected FilePermissionSetter (Windows-aware ACL / POSIX chmod) with a
        # posix-guarded direct-chmod fallback — see _restrict_owner_only.
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._restrict_owner_only(self._state_dir, is_dir=True)

        self._degraded = False

        self._last_refresh: float = 0.0  # monotonic seconds of last successful refresh

    # ------------------------------------------------------------------
    # Permission hardening (single os.chmod home — CWE-732 / Tier-2)
    # ------------------------------------------------------------------

    def _restrict_owner_only(self, path: pathlib.Path, *, is_dir: bool) -> None:
        """Restrict *path* to owner-only access (dir 0o700 / file 0o600).

        This is the ONE place the telemetry service hardens filesystem permissions, so the
        Windows-silent-no-op defect (CWE-732, accepted Tier-2) cannot creep back into a
        second call site:

        * When a ``FilePermissionSetter`` is injected it owns the restriction on every
          platform (POSIX ``chmod`` or a Windows ``icacls`` ACL) and raises
          ``PlatformSecurityError`` on failure. That is caught, logged at INFO, and
          swallowed so telemetry keeps running in a degraded posture (Tier-2 — unlike the
          Tier-1 fail-loud paths).
        * Without an injected setter the only honest fallback is a direct ``os.chmod``, and
          that is applied ONLY where POSIX ``chmod`` actually takes effect
          (``PLATFORM.has_posix_chmod``). On Windows ``os.chmod`` is a silent no-op, so the
          guard SKIPS it rather than pretending the path was hardened.
        """
        mode = 0o700 if is_dir else 0o600
        if self._permission_setter is not None:
            try:
                if is_dir:
                    self._permission_setter.restrict_dir_to_owner(path, mode)
                else:
                    self._permission_setter.restrict_to_owner(path, mode)
            except PlatformSecurityError as perm_exc:
                logger.info(
                    "TelemetryService: cannot restrict %s permissions (%s) — "
                    "telemetry continues in degraded mode.",
                    "directory" if is_dir else "database file",
                    perm_exc,
                )
            return
        if PLATFORM.has_posix_chmod:
            os.chmod(path, mode)

    # ------------------------------------------------------------------
    # Public state
    # ------------------------------------------------------------------

    @property
    def is_degraded(self) -> bool:
        """True when the SQLite database was found corrupt and quarantined.

        While degraded, all telemetry read endpoints return 503.  The service
        itself remains alive so that non-telemetry panel functionality continues.
        To recover: investigate / shred the quarantined file (see
        ``features/panel/views/agents.py`` module docstring), then restart.
        """
        return self._degraded

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Ingest new telemetry data. Idempotent; cached for CACHE_TTL_SECONDS."""
        lock_path = str(self._state_dir / "telemetry.lock")

        # Acquire exclusive non-blocking lock via the injected TelemetryRefreshLock.
        if not self._refresh_lock.try_acquire(lock_path):
            # Another process is refreshing — skip silently (D-AM-11).
            logger.debug("TelemetryService: another process is refreshing; skipping.")
            return

        try:
            # Cache TTL check.
            now = self._clock()
            if now - self._last_refresh < _budget.CACHE_TTL_SECONDS:
                logger.debug("TelemetryService: cache hit; skipping refresh.")
                return

            self._do_refresh()
            self._last_refresh = self._clock()

        finally:
            self._refresh_lock.release()

    def _do_refresh(self) -> None:
        """Inner refresh: integrity-check, open+migrate the store, run readers, backfill."""
        # --- Integrity check on existing DB (T-AM-21 / devops T10) ---
        # A read; must never flip a corrupt file into WAL (v0.1.52 FR3) — the
        # store's integrity_check() opens its own throwaway read-only connection.
        if not self._store.integrity_check():
            quarantine_path = self._store.quarantine()
            if quarantine_path is not None:
                logger.warning(
                    "TelemetryService: corrupt database quarantined as %s. "
                    "Service is now in degraded mode. "
                    "Investigate and then run: shred -u %s",
                    quarantine_path,
                    quarantine_path,
                )
            self._degraded = True
            return  # Skip all readers — service stays alive in degraded mode.

        # The write connection is opened per refresh and MUST be closed in
        # finally so its connection (and any WAL/-shm handles) never leaks
        # across refreshes (v0.1.52 FR3).
        self._store.open_write()
        try:
            self._store.migrate()

            # Harden SQLite file permissions to owner-only (0o600). This is done after
            # every refresh since the store may create the file on first connection. Routed
            # through the same injected-setter + posix-guard path as the state dir so a
            # Windows host applies an ACL (or degrades) instead of silently no-op'ing an
            # os.chmod (CWE-732). See _restrict_owner_only.
            if self._store.db_path.exists():
                self._restrict_owner_only(self._store.db_path, is_dir=False)

            now_iso = datetime.datetime.now(tz=datetime.UTC).isoformat()
            for reader in self._readers:
                reader.ingest(self._store, now_iso)

            self._backfill_costs()
        finally:
            self._store.close()

    def _backfill_costs(self) -> None:
        """Fill cost_micro_usd for events where it is NULL and model is known."""
        updated = 0
        for row in self._store.iter_events_missing_cost():
            try:
                when = datetime.date.fromisoformat(row.occurred_at[:10])
            except Exception:
                when = datetime.date.today()

            usage = {
                "input_tokens": row.tokens_input,
                "output_tokens": row.tokens_output,
                "cache_creation_input_tokens": row.tokens_cache_create,
                "cache_read_input_tokens": row.tokens_cache_read,
            }

            cost = self._pricing.compute_cost(usage, row.model, when)
            if cost is None:
                continue  # model unknown — leave NULL

            # Determine pricing_version (effective_from of selected row).
            pricing_version: str | None = None
            table = getattr(self._pricing, "PRICING_TABLE", {})
            model_rows = table.get(row.model)
            if model_rows:
                applicable = [r for r in model_rows if r.effective_from <= when]
                if applicable:
                    pricing_version = max(
                        applicable, key=lambda r: r.effective_from
                    ).effective_from.isoformat()

            self._store.update_event_cost(row.event_id, cost, pricing_version)
            updated += 1

        if updated:
            self._store.commit()
            logger.debug("TelemetryService: backfilled costs for %d events.", updated)

    # ------------------------------------------------------------------
    # Public query methods (lazy: call refresh first)
    # ------------------------------------------------------------------

    def list_agents(
        self,
        window_days: int = 180,
        context_slug: str | None = None,
        limit: int = 50,
    ) -> AgentListResult:
        """Return aggregated agent list. Triggers lazy refresh."""
        self.refresh()
        return self._aggregator.list_agents(
            window_days=window_days,
            context_slug=context_slug,
            limit=limit,
        )

    def list_sessions_by_agent(
        self,
        agent_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RecentSession]:
        """Return paginated sessions for an agent. Triggers lazy refresh."""
        self.refresh()
        return self._aggregator.list_sessions_by_agent(
            agent_id=agent_id,
            limit=limit,
            offset=offset,
        )

    def aggregate_sessions(self, runtime: str) -> SessionAggregate:
        """Return the server-side aggregate cost summary. Triggers lazy refresh."""
        self.refresh()
        return self._aggregator.aggregate_sessions(runtime=runtime)
