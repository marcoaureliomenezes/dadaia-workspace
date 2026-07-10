"""Connection-isolation regression for the panel telemetry query path (v0.1.52 FR3).

The panel serves telemetry aggregates from a ``ThreadingHTTPServer`` — every
request runs on its own worker thread.  The pre-v0.1.52 wiring handed the
``TelemetryAggregator`` a *single* live ``sqlite3.Connection`` (opened once with
``check_same_thread=False`` in ``cli/commands/panel.py``) that was then shared by
every concurrent request.  That shared connection is the root of the
``panel-telemetry-sqlite-corrupts-under-concurrent-access`` chain.

The fix routes the aggregator through a *connection factory*: each public query
opens its own pragma'd read-only connection and closes it in ``finally``. This
module is the deterministic, structural regression for that change: a
``threading.Barrier(2)``-synchronised assertion that two concurrent
``aggregate_sessions`` calls each open their OWN ``sqlite3.Connection``. It FAILS
by construction against the shared-connection design (the aggregator holds one
connection; no per-call factory seam exists) and PASSES once the aggregator opens
per call — the real SQLite corruption fix.

No real ``telemetry.sqlite`` is read: every store is seeded under ``tmp_path``.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dadaia_workspace.features.telemetry.aggregator.queries import TelemetryAggregator
from dadaia_workspace.features.telemetry.store.schema import apply_migrations, open_connection

_NOW = datetime.now(tz=UTC)
_T1 = (_NOW - timedelta(hours=2)).isoformat()
_T2 = (_NOW - timedelta(hours=1)).isoformat()


class _FakeSCS:
    def list_all(self) -> list[object]:
        return []


class _FakePricing:
    PRICING_TABLE: dict[str, list[object]] = {}

    @staticmethod
    def pricing_age_days(models_used: list[str], when: object = None) -> None:
        return None


def _seed(db_path: Path, *, sessions: int = 3) -> None:
    """Create + migrate a real on-disk store and seed a few claude sessions."""
    conn = open_connection(db_path)
    try:
        apply_migrations(conn)
        conn.execute(
            "INSERT OR IGNORE INTO agents (name, provider, is_subagent, first_seen_at, last_seen_at)"
            " VALUES (?,?,?,?,?)",
            ("agent-a", "claude", 0, _T1, _T1),
        )
        for i in range(sessions):
            sid = f"s{i}"
            conn.execute(
                "INSERT OR REPLACE INTO sessions"
                " (session_id, provider, agent_name, ai_title, entrypoint, cwd, git_branch,"
                "  is_sidechain, sub_slug, first_event_at, last_event_at, status)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (sid, "claude", "agent-a", None, "cli", "/ws", "main", 0, None, _T1, _T2, "closed"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO events"
                " (event_id, session_id, agent_name, model, occurred_at,"
                "  tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,"
                "  cost_micro_usd, pricing_version, suspect)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"e{i}", sid, "agent-a", "claude-sonnet-4-6", _T2, 10, 0, 0, 5, 1000, None, 0),
            )
        conn.commit()
    finally:
        conn.close()


def test_two_concurrent_aggregate_calls_open_distinct_connections(tmp_path: Path) -> None:
    """Two concurrent panel query calls MUST observe distinct connections.

    Structural + deterministic: the factory records every connection it hands
    out, tagged by the opening thread.  Under the shared-connection design the
    aggregator never consults a factory (there is no such seam) — this test
    fails by construction.  Under the per-call design each concurrent call opens
    exactly one connection, so two threads yield two distinct connection objects.
    """
    db_path = tmp_path / "telemetry.sqlite"
    _seed(db_path)

    produced: list[tuple[int, sqlite3.Connection]] = []
    plock = threading.Lock()

    def _connection_factory() -> sqlite3.Connection:
        conn = open_connection(db_path, read_only=True)
        with plock:
            produced.append((threading.get_ident(), conn))
        return conn

    aggregator = TelemetryAggregator(
        connection_factory=_connection_factory,
        spec_context_service=_FakeSCS(),
        pricing_module=_FakePricing(),
    )

    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def _worker() -> None:
        try:
            barrier.wait(timeout=10)
            aggregator.aggregate_sessions(runtime="claude")
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=_worker)
    t2 = threading.Thread(target=_worker)
    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)

    assert not errors, f"concurrent aggregate_sessions raised: {errors!r}"
    assert len(produced) == 2, (
        "each concurrent panel query must open its OWN connection per call; "
        f"observed {len(produced)} factory opens (a shared/cached connection opens 0-1)."
    )
    idents = {ident for ident, _ in produced}
    conns = [conn for _, conn in produced]
    assert len(idents) == 2, f"the two opens must come from two distinct threads, got {idents!r}"
    assert conns[0] is not conns[1], (
        "the two concurrent panel query calls observed the SAME sqlite3.Connection "
        "object — the shared-connection design leaks a single connection across "
        "ThreadingHTTPServer worker threads."
    )
