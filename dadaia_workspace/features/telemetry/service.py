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

from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.core.protocols.platform_services import FilePermissionSetter
from dadaia_workspace.core.protocols.telemetry_lock import TelemetryRefreshLock
from dadaia_workspace.features.telemetry import budget as _budget
from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    RecentSession,
    SessionDetail,
    SessionListResult,
    WorkflowListResult,
)

logger = logging.getLogger(__name__)

_DEFAULT_STATE_DIR = pathlib.Path("~/.dadaia/state/telemetry").expanduser()
_DEFAULT_SQLITE_FILENAME = "telemetry.sqlite"
_DEFAULT_CODEX_PATH = pathlib.Path("~/.codex/state_5.sqlite").expanduser()
_CLAUDE_PROJECTS_DIR = pathlib.Path("~/.claude/projects").expanduser()


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
        Callable returning a 2-tuple (claude_reader_module, codex_reader_module).
        Each module must expose its read function
        (read_session_file, read_codex_db respectively).
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
        reader_factory: Callable[[], tuple[Any, Any]],
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
        # We create parents first, then restrict the leaf dir to 0o700 so that the
        # telemetry state is only readable by the owning user.
        # Tier-2: if the permission setter raises PlatformSecurityError, log INFO and
        # continue — the panel starts but telemetry degraded (unlike panel auth token
        # which is Tier-1 fail-loud).
        self._state_dir.mkdir(parents=True, exist_ok=True)
        if self._permission_setter is not None:
            try:
                self._permission_setter.restrict_dir_to_owner(self._state_dir)
            except Exception as _perm_exc:  # noqa: BLE001
                from dadaia_workspace.core.exceptions import PlatformSecurityError

                if isinstance(_perm_exc, PlatformSecurityError):
                    logger.info(
                        "TelemetryService: cannot restrict state_dir permissions "
                        "(%s) — telemetry continues in degraded mode.",
                        _perm_exc,
                    )
                else:
                    raise
        else:
            os.chmod(self._state_dir, 0o700)

        # Verify the panel auth token file (written by auth.py) has 0o600 perms.
        # If permissions have drifted (e.g. umask misconfiguration), log a warning
        # but do not abort — the operator can remediate without restarting.
        # Guard with PLATFORM.has_posix_chmod: on Windows chmod is a no-op (CWE-732),
        # so this drift check would always fire a false alarm (SPEC §5 DEAD-PATTERN REMOVAL).
        if PLATFORM.has_posix_chmod:
            _token_path = self._state_dir.parent / "panel.token"
            if _token_path.exists():
                actual_mode = _token_path.stat().st_mode & 0o777
                if actual_mode != 0o600:
                    logger.warning(
                        "TelemetryService: auth token file %s has mode 0o%o "
                        "(expected 0o600). Run: chmod 600 %s",
                        _token_path,
                        actual_mode,
                        _token_path,
                    )

        self._degraded = False

        self._last_refresh: float = 0.0  # monotonic seconds of last successful refresh

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
        # --- Integrity check on existing DB (T-AM-21 / devops T10) ---
        # Open a temporary connection to check the existing file BEFORE
        # the DAO factory opens it (which would apply migrations).
        db_path = self._state_dir / _DEFAULT_SQLITE_FILENAME
        if db_path.exists():
            try:
                _check_conn = sqlite3.connect(str(db_path))
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

        dao = self._dao_factory()

        # Apply migrations (idempotent).
        from dadaia_workspace.features.telemetry.store.schema import apply_migrations

        apply_migrations(dao._conn)

        # Harden SQLite file permissions to 0o600 (owner read/write only).
        # This is done after every refresh since the DAO may create the file on
        # first connection. os.chmod is idempotent and cheap. (T-AM-20 / devops T2)
        if db_path.exists():
            os.chmod(db_path, 0o600)

        claude_reader, codex_reader = self._reader_factory()
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
                        logger.warning("TelemetryService: error reading %s: %s", jsonl_file, exc)

        # --- Codex reader ---
        codex_path_env = os.environ.get("DADAIA_CODEX_DB_PATH")
        codex_path = pathlib.Path(codex_path_env) if codex_path_env else _DEFAULT_CODEX_PATH
        try:
            codex_reader.read_codex_db(codex_path, dao, now_iso)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TelemetryService: codex reader error: %s", exc)

        # --- Cost backfill ---
        self._backfill_costs(dao, now_iso)

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

    def list_workflows(self) -> WorkflowListResult:
        """Return workflow list. Triggers lazy refresh."""
        self.refresh()
        return cast(WorkflowListResult, self._aggregator.list_workflows())

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

    def list_sessions(
        self,
        runtime: str,
        project: str | None = None,
        limit: int | None = None,
    ) -> SessionListResult:
        """Return sessions for the given runtime. Triggers lazy refresh."""
        self.refresh()
        return cast(
            SessionListResult,
            self._aggregator.list_sessions(runtime=runtime, project=project, limit=limit),
        )

    def get_session(self, runtime: str, session_id: str) -> SessionDetail | None:
        """Return detail for a single session, or None on miss. Triggers lazy refresh."""
        self.refresh()
        return cast(
            "SessionDetail | None",
            self._aggregator.get_session(runtime=runtime, session_id=session_id),
        )
