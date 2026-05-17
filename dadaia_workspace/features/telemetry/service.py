"""TelemetryService — lazy on-request telemetry orchestrator (T-AM-12).

Design decisions implemented:
    D-AM-11  — Lazy on-request + cache 30 s (no daemon, no cron, no watcher).
    D-AM-15  — SQLite WAL in ~/.dadaia/state/telemetry/telemetry.sqlite.
    T6       — Guard os.getuid() != 0 in constructor.
    Architect D6 — Process lock via fcntl.flock on telemetry.lock.

Refresh logic:
    1. Acquire LOCK_EX | LOCK_NB on state_dir/telemetry.lock.
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

import fcntl
import logging
import os
import pathlib
import time
from typing import Any, Callable

from dadaia_workspace.features.telemetry import budget as _budget
from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    RecentSession,
    WorkflowListResult,
)

logger = logging.getLogger(__name__)

_DEFAULT_STATE_DIR = pathlib.Path("~/.dadaia/state/telemetry").expanduser()
_DEFAULT_SQLITE_FILENAME = "telemetry.sqlite"
_DEFAULT_CODEX_PATH = pathlib.Path("~/.codex/state_5.sqlite").expanduser()
_CLAUDE_PROJECTS_DIR = pathlib.Path("~/.claude/projects").expanduser()


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
        Callable returning a 3-tuple (claude_reader_module, codex_reader_module,
        workflows_reader_module).  Each module must expose its read function
        (read_session_file, read_sessions, read_workflows respectively).
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
    _now_fn:
        Injectable for tests: returns float (monotonic seconds).
    _getuid_fn:
        Injectable for tests: returns int (current uid).
    """

    def __init__(
        self,
        dao_factory: Callable[[], Any],
        aggregator: Any,
        reader_factory: Callable[[], tuple[Any, Any, Any]],
        pricing_module: Any,
        workspace_root: pathlib.Path,
        state_dir: pathlib.Path = _DEFAULT_STATE_DIR,
        spec_context_service: Any = None,
        _now_fn: Callable[[], float] | None = None,
        _getuid_fn: Callable[[], int] | None = None,
    ) -> None:
        # T6: refuse uid=0
        getuid = _getuid_fn or os.getuid
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

        # Ensure state directory exists with restricted permissions.
        # Full permission hardening (chmod 0o700) is done in T-AM-20.
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._last_refresh: float = 0.0  # monotonic seconds of last successful refresh

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Ingest new telemetry data. Idempotent; cached for CACHE_TTL_SECONDS."""
        lock_path = self._state_dir / "telemetry.lock"

        # Acquire exclusive non-blocking lock.
        try:
            lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_WRONLY, 0o600)
        except OSError as exc:
            logger.warning("TelemetryService: cannot open lock file: %s", exc)
            return

        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Another process is refreshing — skip silently (D-AM-11).
            logger.debug("TelemetryService: another process is refreshing; skipping.")
            os.close(lock_fd)
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
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    def _do_refresh(self) -> None:
        """Inner refresh: open DAO, run readers, backfill costs."""
        import datetime as _dt

        dao = self._dao_factory()

        # Apply migrations (idempotent).
        from dadaia_workspace.features.telemetry.store.schema import apply_migrations
        apply_migrations(dao._conn)

        claude_reader, codex_reader, workflows_reader = self._reader_factory()
        now_iso = _dt.datetime.now(tz=_dt.timezone.utc).isoformat()

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
        codex_path = (
            pathlib.Path(codex_path_env) if codex_path_env else _DEFAULT_CODEX_PATH
        )
        try:
            codex_reader.read_sessions(codex_path, dao, now_iso)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TelemetryService: codex reader error: %s", exc)

        # --- Workflows reader ---
        try:
            known_agents = [a.name for a in dao.list_agents()]
            workflows_reader.read_workflows(self._workspace_root, dao, known_agents, now_iso)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TelemetryService: workflows reader error: %s", exc)

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
        return self._aggregator.list_agents(
            window_days=window_days,
            context_slug=context_slug,
            limit=limit,
        )

    def list_workflows(self) -> WorkflowListResult:
        """Return workflow list. Triggers lazy refresh."""
        self.refresh()
        return self._aggregator.list_workflows()

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
