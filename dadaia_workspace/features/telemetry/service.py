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
    3. Open DAO + apply schema migrations.
    4. Walk ~/.claude/projects/*/*.jsonl — call claude reader for each.
    5. Run codex reader on ~/.codex/state_5.sqlite (or env override).
    6. Run workflows reader against workspace_root.
    7. Backfill costs: UPDATE events WHERE cost_micro_usd IS NULL AND model known.
    8. Update last_refresh timestamp.
    9. Release lock.
"""

from __future__ import annotations

import datetime
import logging
import os
import pathlib
import sqlite3
import sys
import time
from collections.abc import Callable
from typing import Any, cast

from dadaia_workspace.core.exceptions import PlatformSecurityError
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.protocols.platform_services import FilePermissionSetter
from dadaia_workspace.core.protocols.telemetry_lock import TelemetryRefreshLock
from dadaia_workspace.features.telemetry import budget as _budget
from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    RecentSession,
    SessionAggregate,
)

logger = logging.getLogger(__name__)

_DEFAULT_STATE_DIR = pathlib.Path("~/.dadaia/state/telemetry").expanduser()
_DEFAULT_SQLITE_FILENAME = "telemetry.sqlite"
_DEFAULT_CODEX_PATH = pathlib.Path("~/.codex/state_5.sqlite").expanduser()
_CLAUDE_PROJECTS_DIR = pathlib.Path("~/.claude/projects").expanduser()
_DEFAULT_PI_SESSIONS_DIR = pathlib.Path("~/.pi/agent/sessions").expanduser()


def _default_refresh_lock() -> TelemetryRefreshLock:
    """Return the platform-appropriate TelemetryRefreshLock implementation.

    Interim sys.platform guard.
    # TODO: Replace with PLATFORM.has_fcntl once WS-1 lands
    """
    if sys.platform == "win32":  # TODO: Replace with PLATFORM.has_fcntl once WS-1 lands
        from dadaia_workspace.infrastructure.telemetry_lock_windows import (
            WindowsTelemetryRefreshLock,
        )

        return WindowsTelemetryRefreshLock()
    from dadaia_workspace.infrastructure.telemetry_lock_posix import PosixTelemetryRefreshLock

    return PosixTelemetryRefreshLock()


class TelemetryService:
    """Aggregate entry-point for telemetry: ingest, cache, and query.

    Dependencies are injected at construction time so each can be swapped
    with a fake in tests (no mocks required).

    Parameters
    ----------
    dao_factory:
        Callable[[], TelemetryDao] — called inside refresh() to open a
        DAO over the SQLite connection.
    aggregator:
        TelemetryAggregator instance (features/telemetry/aggregator/queries.py).
    reader_factory:
        Callable returning a tuple of reader modules. The first two elements are
        (claude_reader_module, codex_reader_module); an optional third element is
        the PI reader module (WS-PI-6). Each module must expose its read function
        (read_session_file, read_codex_db, read_pi_sessions respectively). A legacy
        2-tuple is still accepted — PI ingestion is skipped when no third element
        is present.
        Workflow ingestion is no longer performed here — workflows are read
        directly from the canonical store (PR3-18 cleanup).
    pricing_module:
        The features/telemetry/pricing module (or compatible stub).  Must
        expose compute_cost() and PRICING_TABLE.
    workspace_root:
        pathlib.Path to the dadaia workspace root (used by workflows reader).
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
    _now_fn:
        Injectable for tests: returns float (monotonic seconds).
    _getuid_fn:
        Injectable for tests: returns int (current uid).
    """

    def __init__(
        self,
        dao_factory: Callable[[], Any],
        aggregator: Any,
        reader_factory: Callable[[], tuple[Any, ...]],
        pricing_module: Any,
        workspace_root: pathlib.Path,
        state_dir: pathlib.Path = _DEFAULT_STATE_DIR,
        spec_context_service: Any = None,
        refresh_lock: TelemetryRefreshLock | None = None,
        permission_setter: FilePermissionSetter | None = None,
        _now_fn: Callable[[], float] | None = None,
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

        self._dao_factory = dao_factory
        self._aggregator = aggregator
        self._reader_factory = reader_factory
        self._pricing = pricing_module
        self._workspace_root = workspace_root
        self._state_dir = state_dir
        self._scs = spec_context_service
        self._now_fn: Callable[[], float] = _now_fn or time.monotonic
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
            now = self._now_fn()
            if now - self._last_refresh < _budget.CACHE_TTL_SECONDS:
                logger.debug("TelemetryService: cache hit; skipping refresh.")
                return

            self._do_refresh()
            self._last_refresh = self._now_fn()

        finally:
            self._refresh_lock.release()

    # ------------------------------------------------------------------
    # Integrity check (T-AM-21)
    # ------------------------------------------------------------------

    @staticmethod
    def _integrity_check(conn: sqlite3.Connection) -> bool:
        """Run PRAGMA integrity_check; return True if the database is intact.

        SQLite's integrity_check returns a single row with the text 'ok' when
        the file is not corrupt.  Any other result (or an OperationalError) means
        the database is damaged and should be quarantined.
        """
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            return result is not None and result[0] == "ok"
        except sqlite3.OperationalError:
            return False

    def _quarantine_db(self) -> None:
        """Rename the corrupt DB to telemetry.sqlite.corrupt.<utc_ts>.

        Does not raise; only logs.  The service continues in degraded mode.
        """
        db_path = self._state_dir / _DEFAULT_SQLITE_FILENAME
        ts = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        quarantine_path = self._state_dir / f"telemetry.sqlite.corrupt.{ts}"
        try:
            os.replace(db_path, quarantine_path)
            # A WAL store is three files (telemetry.sqlite + -wal + -shm). Move
            # the siblings WITH the corrupt main DB so a fresh writer never
            # picks up phantom WAL frames stranded next to a clean file
            # (v0.1.52 FR3).
            for suffix in ("-wal", "-shm"):
                sibling = self._state_dir / f"{_DEFAULT_SQLITE_FILENAME}{suffix}"
                if sibling.exists():
                    os.replace(sibling, self._state_dir / f"{quarantine_path.name}{suffix}")
            logger.warning(
                "TelemetryService: corrupt database quarantined as %s. "
                "Service is now in degraded mode. "
                "Investigate and then run: shred -u %s",
                quarantine_path,
                quarantine_path,
            )
        except OSError as exc:
            logger.error(
                "TelemetryService: could not quarantine corrupt DB %s → %s: %s",
                db_path,
                quarantine_path,
                exc,
            )

    def _do_refresh(self) -> None:
        """Inner refresh: open DAO, run readers, backfill costs."""
        from dadaia_workspace.features.telemetry.store.schema import (
            apply_migrations,
            open_connection,
        )

        # --- Integrity check on existing DB (T-AM-21 / devops T10) ---
        # Open a temporary READ-ONLY connection to check the existing file
        # BEFORE the DAO factory opens it (which would apply migrations). The
        # probe routes through the pragma'd factory in read-only mode — an
        # integrity check is a read; it must never flip the corrupt file into
        # WAL (v0.1.52 FR3).
        db_path = self._state_dir / _DEFAULT_SQLITE_FILENAME
        if db_path.exists():
            try:
                _check_conn = open_connection(db_path, read_only=True)
                try:
                    intact = self._integrity_check(_check_conn)
                finally:
                    _check_conn.close()
            except sqlite3.DatabaseError:
                intact = False

            if not intact:
                self._quarantine_db()
                self._degraded = True
                return  # Skip all readers — service stays alive in degraded mode.

        # The write DAO is opened per refresh and MUST be closed in finally so
        # its connection (and any WAL/-shm handles) never leaks across refreshes
        # (v0.1.52 FR3).
        dao = self._dao_factory()
        try:
            # Apply migrations (idempotent).
            apply_migrations(dao._conn)

            # Harden SQLite file permissions to owner-only (0o600). This is done after
            # every refresh since the DAO may create the file on first connection. Routed
            # through the same injected-setter + posix-guard path as the state dir so a
            # Windows host applies an ACL (or degrades) instead of silently no-op'ing an
            # os.chmod (CWE-732). See _restrict_owner_only.
            if db_path.exists():
                self._restrict_owner_only(db_path, is_dir=False)

            # The reader factory returns (claude, codex) historically, or
            # (claude, codex, pi) once the PI reader is wired (WS-PI-6). Unpack
            # tolerantly so legacy 2-tuple callers keep working unchanged.
            readers = self._reader_factory()
            claude_reader, codex_reader = readers[0], readers[1]
            pi_reader = readers[2] if len(readers) > 2 else None
            now_iso = datetime.datetime.now(tz=datetime.UTC).isoformat()

            # --- Claude reader ---
            claude_projects = _CLAUDE_PROJECTS_DIR
            if claude_projects.is_dir():
                for project_dir in claude_projects.iterdir():
                    if not project_dir.is_dir():
                        continue
                    for jsonl_file in project_dir.glob("*.jsonl"):
                        try:
                            claude_reader.read_session_file(jsonl_file, dao, now_iso)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "TelemetryService: error reading %s: %s", jsonl_file, exc
                            )

            # --- Codex reader ---
            codex_path_env = os.environ.get("DADAIA_CODEX_DB_PATH")
            codex_path = pathlib.Path(codex_path_env) if codex_path_env else _DEFAULT_CODEX_PATH
            try:
                codex_reader.read_codex_db(codex_path, dao, now_iso)
            except Exception as exc:  # noqa: BLE001
                logger.warning("TelemetryService: codex reader error: %s", exc)

            # --- PI reader (WS-PI-6) ---
            # Ingests PI session metadata from ~/.pi/agent/sessions/ (env
            # override: DADAIA_PI_SESSIONS_DIR). Degrades to a no-op when the dir
            # is absent or any IO/parse failure occurs (the reader is graceful).
            if pi_reader is not None:
                pi_dir_env = os.environ.get("DADAIA_PI_SESSIONS_DIR")
                pi_dir = pathlib.Path(pi_dir_env) if pi_dir_env else _DEFAULT_PI_SESSIONS_DIR
                try:
                    pi_reader.read_pi_sessions(pi_dir, dao, now_iso)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("TelemetryService: pi reader error: %s", exc)

            # --- Cost backfill ---
            self._backfill_costs(dao, now_iso)
        finally:
            dao._conn.close()

    def _backfill_costs(self, dao: Any, now_iso: str) -> None:
        """Fill cost_micro_usd for events where it is NULL and model is known."""
        import datetime as _dt

        conn = dao._conn
        conn.row_factory = __import__("sqlite3").Row

        rows = conn.execute(
            """
            SELECT event_id, model, occurred_at,
                   tokens_input, tokens_cache_read, tokens_cache_create, tokens_output
            FROM events
            WHERE cost_micro_usd IS NULL
            """
        ).fetchall()

        updated = 0
        for row in rows:
            model = row["model"]
            try:
                when = _dt.date.fromisoformat(row["occurred_at"][:10])
            except Exception:
                when = _dt.date.today()

            usage = {
                "input_tokens": row["tokens_input"],
                "output_tokens": row["tokens_output"],
                "cache_creation_input_tokens": row["tokens_cache_create"],
                "cache_read_input_tokens": row["tokens_cache_read"],
            }

            cost = self._pricing.compute_cost(usage, model, when)
            if cost is None:
                continue  # model unknown — leave NULL

            # Determine pricing_version (effective_from of selected row).
            pricing_version: str | None = None
            table = getattr(self._pricing, "PRICING_TABLE", {})
            model_rows = table.get(model)
            if model_rows:
                applicable = [r for r in model_rows if r.effective_from <= when]
                if applicable:
                    pricing_version = max(
                        applicable, key=lambda r: r.effective_from
                    ).effective_from.isoformat()

            conn.execute(
                "UPDATE events SET cost_micro_usd = ?, pricing_version = ? WHERE event_id = ?",
                (cost, pricing_version, row["event_id"]),
            )
            updated += 1

        if updated:
            conn.commit()
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
        return cast(
            AgentListResult,
            self._aggregator.list_agents(
                window_days=window_days,
                context_slug=context_slug,
                limit=limit,
            ),
        )

    def list_sessions_by_agent(
        self,
        agent_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RecentSession]:
        """Return paginated sessions for an agent. Triggers lazy refresh."""
        self.refresh()
        return cast(
            "list[RecentSession]",
            self._aggregator.list_sessions_by_agent(
                agent_id=agent_id,
                limit=limit,
                offset=offset,
            ),
        )

    def aggregate_sessions(self, runtime: str) -> SessionAggregate:
        """Return the server-side aggregate cost summary. Triggers lazy refresh."""
        self.refresh()
        return cast(
            SessionAggregate,
            self._aggregator.aggregate_sessions(runtime=runtime),
        )
