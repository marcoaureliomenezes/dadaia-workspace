"""TelemetryAggregator — SQL queries that build the API-shaped dataclasses.

The aggregator reads from the telemetry SQLite store via the DAO's connection
and the DAO's own read helpers, then constructs frozen dataclasses for the
HTTP handler in P7.

Design decisions implemented here:
    D-AM-09   — cwd → context resolved at query time (architect D9)
    D-AM-11   — lazy on-request; this class is stateless (cache lives in Service)
    D-AM-19   — suspect_count surfaced per agent
    D-AM-12   — window_days default 180

Privacy invariant (T1): no content fields are read or returned.
"""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    AgentSummary,
    ContextBreakdown,
    RecentSession,
    SessionDetail,
    SessionListResult,
    SessionRow,
    TokenTotals,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _micro_to_usd(micro: int) -> float:
    return micro / 1_000_000


# ---------------------------------------------------------------------------
# Main aggregator class
# ---------------------------------------------------------------------------


class TelemetryAggregator:
    """Query engine that aggregates raw telemetry rows into API shapes.

    Parameters
    ----------
    dao:
        A TelemetryDao instance (provides the sqlite3.Connection).
    spec_context_service:
        Any object exposing ``list_all() -> list`` where each item has
        ``.name`` (str), ``.repo_slug`` (str), and the workspace root is
        resolved via ``workspace_root / "repos" / repo_slug``.
        A simpler duck-typed stub used in tests just returns objects with
        ``slug`` and ``repo_root`` attributes.
    pricing_module:
        The ``dadaia_workspace.features.telemetry.pricing`` module (or a
        compatible stub).  Must expose ``pricing_age_days(models, when)``
        and ``PRICING_TABLE``.
    workspace_root:
        pathlib.Path for the workspace root.  Used to build repo paths when
        resolving cwd → context via SpecContextService.
    """

    def __init__(
        self,
        dao: Any,
        spec_context_service: Any,
        pricing_module: Any,
        workspace_root: Any = None,
    ) -> None:
        self._dao = dao
        self._scs = spec_context_service
        self._pricing = pricing_module
        self._workspace_root = workspace_root

    # ------------------------------------------------------------------
    # Context resolution helpers
    # ------------------------------------------------------------------

    def _build_context_map(self) -> dict[str, tuple[str, str]]:
        """Return a map of repo_root_path (str) → (slug, display_name).

        Accepts two stub shapes used in tests:
        - Objects with .slug and .repo_root attrs (simple stub).
        - SpecContextProject with .name, .repo_slug, and workspace_root
          being used to resolve the full path.
        """
        mapping: dict[str, tuple[str, str]] = {}
        contexts = self._scs.list_all()
        for ctx in contexts:
            # Duck-typed: prefer explicit .repo_root if present (test stub),
            # else derive from workspace_root + repo_slug (real SCS).
            if hasattr(ctx, "repo_root"):
                root = str(ctx.repo_root).rstrip("/")
                slug = ctx.slug
                name = getattr(ctx, "name", slug)
            else:
                # Real SpecContextProject: .repo_slug + workspace_root
                if self._workspace_root is None:
                    continue
                root = str(self._workspace_root / "repos" / ctx.repo_slug).rstrip("/")
                slug = ctx.repo_slug
                name = ctx.name
            mapping[root] = (slug, name)
        return mapping

    def _resolve_context(
        self, cwd: str | None, ctx_map: dict[str, tuple[str, str]]
    ) -> tuple[str | None, str]:
        """Map a session cwd to (context_slug, context_name).

        Returns (None, "unassigned") when no registered context matches.
        """
        if cwd is None:
            return (None, "unassigned")
        cwd_norm = cwd.rstrip("/")
        # Longest-prefix match wins (handles nested paths correctly).
        best: tuple[str | None, str] = (None, "unassigned")
        best_len = -1
        for root, (slug, display) in ctx_map.items():
            if (cwd_norm == root or cwd_norm.startswith(root + "/")) and len(root) > best_len:
                best = (slug, display)
                best_len = len(root)
        return best

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_agents(
        self,
        window_days: int = 180,
        context_slug: str | None = None,
        limit: int = 50,
    ) -> AgentListResult:
        """Return AgentListResult with per-agent aggregated metrics.

        Steps:
        1. Collect all sessions in the window, resolved to context buckets.
        2. Group events by agent_name within the window.
        3. Aggregate tokens, cost, suspect_count.
        4. Build context_breakdown and recent_sessions for each agent.
        5. Sort by total_cost_usd DESC NULLS LAST, then session_count DESC.
        6. Filter by context_slug (post-grouping) if set.
        7. Apply limit.
        8. Compute pricing_age_days across all models seen.
        """
        conn: sqlite3.Connection = self._dao._conn
        conn.row_factory = sqlite3.Row

        # ------------------------------------------------------------------
        # Build context lookup map once.
        # ------------------------------------------------------------------
        ctx_map = self._build_context_map()

        # ------------------------------------------------------------------
        # Query: sessions in window, with their cwd.
        # We use a cutoff timestamp derived from window_days.
        # ------------------------------------------------------------------
        now_dt = datetime.now(tz=UTC)
        datetime(
            now_dt.year,
            now_dt.month,
            now_dt.day,
            now_dt.hour,
            now_dt.minute,
            now_dt.second,
            tzinfo=UTC,
        )
        # Simple ISO string comparison works for UTC timestamps stored as ISO.
        from datetime import timedelta

        cutoff = (now_dt - timedelta(days=window_days)).isoformat()

        # sessions in window: keyed by session_id → (agent_name, cwd, entrypoint, git_branch, last_event_at, is_sidechain, provider)
        session_rows = conn.execute(
            """
            SELECT session_id, agent_name, cwd, entrypoint, git_branch,
                   last_event_at, is_sidechain, provider
            FROM sessions
            WHERE last_event_at >= ?
            """,
            (cutoff,),
        ).fetchall()

        # Build a dict: session_id → row dict
        session_info: dict[str, dict[str, Any]] = {}
        for r in session_rows:
            session_info[r["session_id"]] = {
                "agent_name": r["agent_name"],
                "cwd": r["cwd"],
                "entrypoint": r["entrypoint"],
                "git_branch": r["git_branch"],
                "last_event_at": r["last_event_at"],
                "is_sidechain": r["is_sidechain"],
                "provider": r["provider"],
            }

        session_ids_in_window = list(session_info.keys())
        if not session_ids_in_window:
            return AgentListResult(
                generated_at=_now_iso(),
                window_days=window_days,
                pricing_age_days=None,
                pricing_model_date=None,
                agents=[],
            )

        # ------------------------------------------------------------------
        # Query: events for those sessions.
        # We use a parameterised IN clause (sqlite3 doesn't support list bind
        # directly, so we build a placeholder string).
        # ------------------------------------------------------------------
        placeholders = ",".join("?" * len(session_ids_in_window))
        event_rows = conn.execute(
            f"""
            SELECT event_id, session_id, agent_name, model, occurred_at,
                   tokens_input, tokens_cache_read, tokens_cache_create,
                   tokens_output, cost_micro_usd, suspect
            FROM events
            WHERE session_id IN ({placeholders})
              AND occurred_at >= ?
            """,
            (*session_ids_in_window, cutoff),
        ).fetchall()

        # ------------------------------------------------------------------
        # Aggregate per agent.
        # ------------------------------------------------------------------
        # agent_name → accumulated data
        agent_tokens: dict[str, dict[str, int]] = defaultdict(
            lambda: {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}
        )
        agent_cost_sum: dict[str, int] = defaultdict(int)
        agent_cost_null_count: dict[str, int] = defaultdict(int)
        agent_cost_total_count: dict[str, int] = defaultdict(int)
        agent_models: dict[str, list[str]] = defaultdict(list)
        agent_suspect: dict[str, int] = defaultdict(int)
        agent_sessions: dict[str, set[str]] = defaultdict(set)
        agent_last_activity: dict[str, str] = {}

        for ev in event_rows:
            a_name: str = ev["agent_name"]
            agent_tokens[a_name]["input"] += ev["tokens_input"]
            agent_tokens[a_name]["cache_creation"] += ev["tokens_cache_create"]
            agent_tokens[a_name]["cache_read"] += ev["tokens_cache_read"]
            agent_tokens[a_name]["output"] += ev["tokens_output"]

            agent_cost_total_count[a_name] += 1
            if ev["cost_micro_usd"] is None:
                agent_cost_null_count[a_name] += 1
            else:
                agent_cost_sum[a_name] += ev["cost_micro_usd"]

            agent_models[a_name].append(ev["model"])
            if ev["suspect"]:
                agent_suspect[a_name] += 1

            sid = ev["session_id"]
            agent_sessions[a_name].add(sid)

            occ = ev["occurred_at"]
            if a_name not in agent_last_activity or occ > agent_last_activity[a_name]:
                agent_last_activity[a_name] = occ

        # Also account for sessions that have no events (edge case: session
        # in window but 0 assistant events — still counts for session_count).
        # Derive agent name from session record for sessions without events.
        session_agent_map: dict[str, str] = {}
        for sid, info in session_info.items():
            a = info["agent_name"] or f"{info['provider']} (main)"
            session_agent_map[sid] = a
            agent_sessions[a].add(sid)

        # Collect all agent names that have sessions in window.
        all_agent_names: set[str] = set(agent_sessions.keys())

        # Provider list per agent (from sessions in window).
        agent_providers: dict[str, set[str]] = defaultdict(set)
        for sid, info in session_info.items():
            a = session_agent_map[sid]
            agent_providers[a].add(info["provider"])

        # is_subagent: True if any session for agent has is_sidechain=1.
        agent_is_subagent: dict[str, bool] = defaultdict(bool)
        for sid, info in session_info.items():
            a = session_agent_map[sid]
            if info["is_sidechain"]:
                agent_is_subagent[a] = True

        # ------------------------------------------------------------------
        # Context breakdown per agent.
        # ------------------------------------------------------------------
        # agent → context_key → {session_count, cost_micro_sum, cost_null_count}
        agent_ctx_sessions: dict[str, dict[tuple[str | None, str], list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        agent_ctx_cost_sum: dict[str, dict[tuple[str | None, str], int]] = defaultdict(
            lambda: defaultdict(int)
        )
        agent_ctx_cost_null: dict[str, dict[tuple[str | None, str], int]] = defaultdict(
            lambda: defaultdict(int)
        )
        # Resolve each session to a context bucket.
        session_ctx: dict[str, tuple[str | None, str]] = {}
        for sid, info in session_info.items():
            ctx_key = self._resolve_context(info["cwd"], ctx_map)
            session_ctx[sid] = ctx_key
            a = session_agent_map[sid]
            agent_ctx_sessions[a][ctx_key].append(sid)

        # Accumulate cost per (agent, context) from events.
        for ev in event_rows:
            a_name = ev["agent_name"]
            sid = ev["session_id"]
            ctx_key = session_ctx.get(sid, (None, "unassigned"))
            if ev["cost_micro_usd"] is None:
                agent_ctx_cost_null[a_name][ctx_key] += 1
            else:
                agent_ctx_cost_sum[a_name][ctx_key] += ev["cost_micro_usd"]
                # also track null for cost_known per bucket
            agent_ctx_cost_null[a_name][ctx_key]  # ensure key exists

        # ------------------------------------------------------------------
        # Build per-agent recent sessions list (up to 10, most recent first).
        # ------------------------------------------------------------------
        # For each session: sum costs from events.
        session_cost: dict[str, int | None] = {}
        session_tokens: dict[str, dict[str, int]] = defaultdict(
            lambda: {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0}
        )
        session_has_null: dict[str, int] = defaultdict(int)
        session_event_count: dict[str, int] = defaultdict(int)

        for ev in event_rows:
            sid = ev["session_id"]
            session_event_count[sid] += 1
            session_tokens[sid]["input"] += ev["tokens_input"]
            session_tokens[sid]["cache_creation"] += ev["tokens_cache_create"]
            session_tokens[sid]["cache_read"] += ev["tokens_cache_read"]
            session_tokens[sid]["output"] += ev["tokens_output"]
            if ev["cost_micro_usd"] is None:
                session_has_null[sid] += 1
            else:
                session_cost[sid] = session_cost.get(sid, 0)
                session_cost[sid] = (session_cost.get(sid) or 0) + ev["cost_micro_usd"]

        # Finalise session cost: None if ALL events for session have NULL cost.
        for sid in session_ids_in_window:
            total_ev = session_event_count[sid]
            null_ev = session_has_null[sid]
            if total_ev == 0 or null_ev == total_ev:
                session_cost[sid] = None
            elif sid not in session_cost:
                session_cost[sid] = 0

        # Sort sessions per agent by last_event_at DESC.
        agent_sorted_sessions: dict[str, list[str]] = {}
        for a_name in all_agent_names:
            sids = list(agent_sessions[a_name])
            sids.sort(
                key=lambda s: session_info[s]["last_event_at"] if s in session_info else "",
                reverse=True,
            )
            agent_sorted_sessions[a_name] = sids

        # ------------------------------------------------------------------
        # Assemble all models used (for pricing_age_days computation).
        # ------------------------------------------------------------------
        all_models_used: list[str] = []
        for models in agent_models.values():
            all_models_used.extend(models)
        distinct_models = list(set(all_models_used))

        age_days = self._pricing.pricing_age_days(distinct_models)
        pricing_model_date: str | None = None
        if distinct_models:
            # Find newest effective_from across used models.
            import datetime as _dt

            newest: _dt.date | None = None
            table = getattr(self._pricing, "PRICING_TABLE", {})
            for m in distinct_models:
                rows = table.get(m)
                if rows:
                    md = max(rows, key=lambda r: r.effective_from).effective_from
                    if newest is None or md > newest:
                        newest = md
            if newest is not None:
                pricing_model_date = newest.isoformat()

        # ------------------------------------------------------------------
        # Build AgentSummary objects.
        # ------------------------------------------------------------------
        summaries: list[AgentSummary] = []

        for a_name in all_agent_names:
            tok = agent_tokens[a_name]
            total_micro = agent_cost_sum.get(a_name, 0)
            null_count = agent_cost_null_count.get(a_name, 0)
            agent_cost_total_count.get(a_name, 0)

            cost_known = null_count == 0
            total_cost_usd: float | None = _micro_to_usd(total_micro) if cost_known else None
            # When some (but not all) events have NULL cost, still report
            # what we know but mark cost_known=False.
            if not cost_known and total_micro > 0:
                total_cost_usd = None  # mixed — can't trust partial sum

            # Dominant model: most common in events for this agent.
            models_list = agent_models.get(a_name, [])
            dominant_model: str | None = None
            if models_list:
                dominant_model = Counter(models_list).most_common(1)[0][0]

            # last_activity: max over sessions' last_event_at or events.
            last_ev = agent_last_activity.get(a_name)
            if not last_ev:
                # Fall back to sessions' last_event_at.
                for sid in agent_sessions[a_name]:
                    if sid in session_info:
                        t = session_info[sid]["last_event_at"]
                        if not last_ev or t > last_ev:
                            last_ev = t
            if not last_ev:
                last_ev = _now_iso()

            # Providers.
            providers = sorted(agent_providers.get(a_name, {"claude"}))

            # Session count.
            sess_count = len(agent_sessions[a_name])

            # Context breakdown.
            breakdown: list[ContextBreakdown] = []
            ctx_sessions_map = agent_ctx_sessions.get(a_name, {})
            for ctx_key, ctx_sids in ctx_sessions_map.items():
                ctx_slug, ctx_display = ctx_key
                # Sum costs for events in this ctx.
                ctx_micro = agent_ctx_cost_sum.get(a_name, {}).get(ctx_key, 0)
                ctx_null = agent_ctx_cost_null.get(a_name, {}).get(ctx_key, 0)
                ctx_ev_count = sum(session_event_count.get(s, 0) for s in ctx_sids)
                ctx_cost_usd: float | None
                if ctx_ev_count > 0 and ctx_null == ctx_ev_count:
                    ctx_cost_usd = None
                else:
                    ctx_cost_usd = _micro_to_usd(ctx_micro)

                breakdown.append(
                    ContextBreakdown(
                        context_slug=ctx_slug,
                        context_name=ctx_display,
                        session_count=len(ctx_sids),
                        cost_usd=ctx_cost_usd,
                        cost_fraction=None,  # filled below
                    )
                )

            # Compute cost_fraction (0..1) for breakdown entries.
            total_breakdown_cost = sum(cb.cost_usd for cb in breakdown if cb.cost_usd is not None)
            rebuilt_breakdown: list[ContextBreakdown] = []
            for cb in breakdown:
                frac: float | None = None
                if total_breakdown_cost and total_breakdown_cost > 0 and cb.cost_usd is not None:
                    frac = cb.cost_usd / total_breakdown_cost
                rebuilt_breakdown.append(
                    ContextBreakdown(
                        context_slug=cb.context_slug,
                        context_name=cb.context_name,
                        session_count=cb.session_count,
                        cost_usd=cb.cost_usd,
                        cost_fraction=frac,
                    )
                )

            # Recent sessions (up to 10).
            recent: list[RecentSession] = []
            for sid in agent_sorted_sessions.get(a_name, [])[:10]:
                sess_info = session_info.get(sid)
                if sess_info is None:
                    continue
                info = sess_info
                s_cost_micro = session_cost.get(sid)
                s_cost_usd: float | None = (
                    _micro_to_usd(s_cost_micro) if s_cost_micro is not None else None
                )
                s_tok = session_tokens[sid]
                ctx_key = session_ctx.get(sid, (None, "unassigned"))
                s_ctx_slug = ctx_key[0]

                # Date from last_event_at (first 10 chars = YYYY-MM-DD).
                ts = info["last_event_at"]
                s_date = ts[:10] if ts else ""

                recent.append(
                    RecentSession(
                        session_id_prefix=sid[:8],
                        date=s_date,
                        cost_usd=s_cost_usd,
                        entrypoint=info["entrypoint"],
                        git_branch=info["git_branch"],
                        context_slug=s_ctx_slug,
                        token_counts=TokenTotals(
                            input=s_tok["input"],
                            cache_creation=s_tok["cache_creation"],
                            cache_read=s_tok["cache_read"],
                            output=s_tok["output"],
                        ),
                    )
                )

            summaries.append(
                AgentSummary(
                    agent_id=a_name,
                    display_name=a_name,
                    providers=providers,
                    dominant_model=dominant_model,
                    is_subagent=agent_is_subagent.get(a_name, False),
                    session_count=sess_count,
                    total_cost_usd=total_cost_usd,
                    cost_known=cost_known,
                    last_activity_at=last_ev,
                    token_totals=TokenTotals(
                        input=tok["input"],
                        cache_creation=tok["cache_creation"],
                        cache_read=tok["cache_read"],
                        output=tok["output"],
                    ),
                    context_breakdown=rebuilt_breakdown,
                    recent_sessions=recent,
                    suspect_count=agent_suspect.get(a_name, 0),
                )
            )

        # ------------------------------------------------------------------
        # Sort: total_cost_usd DESC NULLS LAST, then session_count DESC.
        # ------------------------------------------------------------------
        def _sort_key(s: AgentSummary) -> tuple[float, int]:
            # Use a large negative number for None so nulls sort last.
            cost_key = s.total_cost_usd if s.total_cost_usd is not None else -1.0
            return (-cost_key, -s.session_count)

        summaries.sort(key=_sort_key)

        # ------------------------------------------------------------------
        # Filter by context_slug (post-grouping).
        # ------------------------------------------------------------------
        if context_slug is not None:
            summaries = [
                s
                for s in summaries
                if any(cb.context_slug == context_slug for cb in s.context_breakdown)
            ]

        # Apply limit.
        summaries = summaries[:limit]

        return AgentListResult(
            generated_at=_now_iso(),
            window_days=window_days,
            pricing_age_days=age_days,
            pricing_model_date=pricing_model_date,
            agents=summaries,
        )

    # ------------------------------------------------------------------

    def list_sessions_by_agent(
        self,
        agent_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RecentSession]:
        """Return paginated RecentSession list for a specific agent.

        Used by P7 endpoint ``/api/agents/{id}/sessions``.
        """
        conn: sqlite3.Connection = self._dao._conn
        conn.row_factory = sqlite3.Row

        # Sessions for agent, most recent first.
        session_rows = conn.execute(
            """
            SELECT session_id, cwd, entrypoint, git_branch, last_event_at, provider
            FROM sessions
            WHERE agent_name = ?
            ORDER BY last_event_at DESC
            LIMIT ? OFFSET ?
            """,
            (agent_id, limit, offset),
        ).fetchall()

        if not session_rows:
            return []

        # Build context map once.
        ctx_map = self._build_context_map()

        result: list[RecentSession] = []
        for sr in session_rows:
            sid = sr["session_id"]

            # Sum event tokens + cost for this session.
            ev_rows = conn.execute(
                """
                SELECT tokens_input, tokens_cache_read, tokens_cache_create,
                       tokens_output, cost_micro_usd
                FROM events
                WHERE session_id = ?
                """,
                (sid,),
            ).fetchall()

            tok_in = tok_cc = tok_cr = tok_out = 0
            cost_sum = 0
            null_count = 0
            for ev in ev_rows:
                tok_in += ev["tokens_input"]
                tok_cc += ev["tokens_cache_create"]
                tok_cr += ev["tokens_cache_read"]
                tok_out += ev["tokens_output"]
                if ev["cost_micro_usd"] is None:
                    null_count += 1
                else:
                    cost_sum += ev["cost_micro_usd"]

            ev_count = len(ev_rows)
            session_cost_usd: float | None = (
                None if ev_count == 0 or null_count == ev_count else _micro_to_usd(cost_sum)
            )

            ctx_slug, _ = self._resolve_context(sr["cwd"], ctx_map)
            ts = sr["last_event_at"]
            s_date = ts[:10] if ts else ""

            result.append(
                RecentSession(
                    session_id_prefix=sid[:8],
                    date=s_date,
                    cost_usd=session_cost_usd,
                    entrypoint=sr["entrypoint"],
                    git_branch=sr["git_branch"],
                    context_slug=ctx_slug,
                    token_counts=TokenTotals(
                        input=tok_in,
                        cache_creation=tok_cc,
                        cache_read=tok_cr,
                        output=tok_out,
                    ),
                )
            )

        return result

    # ------------------------------------------------------------------
    # Session-level queries (panel-r5-v1 FR1)
    # ------------------------------------------------------------------

    def list_sessions(
        self,
        runtime: str,
        project: str | None = None,
        limit: int | None = None,
    ) -> SessionListResult:
        """Return SessionListResult for the requested runtime.

        Filters:
        - runtime: matched against sessions.provider.
        - project: optional sub_slug filter (sessions.sub_slug = project).
        - limit: caps the number of rows returned.

        Ordered by sessions.last_event_at DESC.

        For each session the most recent assistant event supplies:
        - model
        - context_size_tokens = input + cache_creation + cache_read of that event
        - message_count = COUNT(events) for the session

        Status is stored in sessions.status (values may be 'closed', 'active', etc.)
        and mapped to the API Literal: closed → ended, active → active; any other
        value → idle.  The RuntimeAdapter (PR5-A3) may override this at call time.
        """
        conn: sqlite3.Connection = self._dao._conn
        conn.row_factory = sqlite3.Row

        # Build session query with optional project filter.
        # NOTE: 'project' maps to sessions.sub_slug (the nearest project slug).
        where_clauses = ["s.provider = ?"]
        params: list[Any] = [runtime]

        if project is not None:
            where_clauses.append("s.sub_slug = ?")
            params.append(project)

        where_sql = " AND ".join(where_clauses)

        session_rows = conn.execute(
            f"""
            SELECT s.session_id, s.provider, s.agent_name, s.ai_title,
                   s.cwd, s.sub_slug, s.first_event_at, s.last_event_at, s.status
            FROM sessions s
            WHERE {where_sql}
            ORDER BY s.last_event_at DESC
            """,
            params,
        ).fetchall()

        total_count = len(session_rows)

        # Apply limit after counting total.
        if limit is not None:
            session_rows = session_rows[:limit]

        if not session_rows:
            return SessionListResult(
                sessions=[],
                runtime=runtime,
                project=project,
                limit=limit,
                generated_at=_now_iso(),
                total_count=total_count,
            )

        session_ids = [r["session_id"] for r in session_rows]
        placeholders = ",".join("?" * len(session_ids))

        # Per-session: message_count and most-recent event metrics.
        # One query: aggregate + most-recent event via subquery.
        event_stats = conn.execute(
            f"""
            SELECT
                e.session_id,
                COUNT(*) AS message_count,
                SUM(e.tokens_input + e.tokens_cache_create + e.tokens_cache_read) AS context_tokens_sum,
                SUM(e.cost_micro_usd) AS cost_sum,
                SUM(CASE WHEN e.cost_micro_usd IS NULL THEN 1 ELSE 0 END) AS null_cost_count
            FROM events e
            WHERE e.session_id IN ({placeholders})
            GROUP BY e.session_id
            """,
            session_ids,
        ).fetchall()

        stat_by_session: dict[str, dict[str, Any]] = {}
        for row in event_stats:
            stat_by_session[row["session_id"]] = {
                "message_count": row["message_count"],
                "context_tokens_sum": row["context_tokens_sum"] or 0,
                "cost_sum": row["cost_sum"],
                "null_cost_count": row["null_cost_count"],
            }

        # Most recent event per session for model + context_size_tokens formula.
        # context_size_tokens = input + cache_creation + cache_read of MOST RECENT event.
        recent_events = conn.execute(
            f"""
            SELECT e.session_id, e.model,
                   e.tokens_input + e.tokens_cache_create + e.tokens_cache_read AS context_size_tokens
            FROM events e
            INNER JOIN (
                SELECT session_id, MAX(occurred_at) AS max_occ
                FROM events
                WHERE session_id IN ({placeholders})
                GROUP BY session_id
            ) latest ON e.session_id = latest.session_id AND e.occurred_at = latest.max_occ
            WHERE e.session_id IN ({placeholders})
            """,
            session_ids + session_ids,
        ).fetchall()

        recent_by_session: dict[str, dict[str, Any]] = {}
        for row in recent_events:
            recent_by_session[row["session_id"]] = {
                "model": row["model"],
                "context_size_tokens": row["context_size_tokens"] or 0,
            }

        result_rows: list[SessionRow] = []
        for sr in session_rows:
            sid = sr["session_id"]
            stats = stat_by_session.get(sid, {})
            recent = recent_by_session.get(sid, {})

            msg_count = stats.get("message_count", 0)
            ctx_tokens = recent.get("context_size_tokens", 0)
            model = recent.get("model", None)

            cost_sum = stats.get("cost_sum")
            null_cost_count = stats.get("null_cost_count", 0)
            total_events = msg_count

            if total_events == 0 or null_cost_count == total_events:
                cumulative_cost_usd: float | None = None
                cost_known = total_events == 0  # no events → unknown; all null → False
            elif cost_sum is not None:
                cumulative_cost_usd = _micro_to_usd(cost_sum)
                cost_known = null_cost_count == 0
            else:
                cumulative_cost_usd = None
                cost_known = False

            # Status mapping: sessions.status is 'closed'/'active'/etc.
            raw_status = sr["status"] or "closed"
            if raw_status == "active":
                status: str = "active"
            elif raw_status == "closed":
                status = "ended"
            else:
                status = "idle"

            result_rows.append(
                SessionRow(
                    session_id=sid,
                    runtime=sr["provider"],
                    project=sr["sub_slug"],
                    cwd=sr["cwd"],
                    model=model,
                    started_at=sr["first_event_at"],
                    last_activity_at=sr["last_event_at"],
                    message_count=msg_count,
                    context_size_tokens=ctx_tokens,
                    cumulative_cost_usd=cumulative_cost_usd,
                    cost_known=cost_known,
                    status=status,  # type: ignore[arg-type]
                    agent_name=sr["agent_name"],
                    ai_title=sr["ai_title"],
                )
            )

        return SessionListResult(
            sessions=result_rows,
            runtime=runtime,
            project=project,
            limit=limit,
            generated_at=_now_iso(),
            total_count=total_count,
        )

    def get_session(
        self,
        runtime: str,
        session_id: str,
    ) -> SessionDetail | None:
        """Return enriched SessionDetail for a single session, or None on miss.

        The runtime discriminator is applied: if the stored provider does not
        match runtime, the method returns None (not found for that runtime).
        """
        conn: sqlite3.Connection = self._dao._conn
        conn.row_factory = sqlite3.Row

        sr = conn.execute(
            """
            SELECT session_id, provider, agent_name, ai_title, cwd, sub_slug,
                   first_event_at, last_event_at, status
            FROM sessions
            WHERE session_id = ? AND provider = ?
            """,
            (session_id, runtime),
        ).fetchone()

        if sr is None:
            return None

        # All events for this session.
        ev_rows = conn.execute(
            """
            SELECT occurred_at, model,
                   tokens_input, tokens_cache_create, tokens_cache_read,
                   cost_micro_usd
            FROM events
            WHERE session_id = ?
            ORDER BY occurred_at ASC
            """,
            (session_id,),
        ).fetchall()

        msg_count = len(ev_rows)
        event_timestamps: tuple[str, ...] = tuple(r["occurred_at"] for r in ev_rows)

        # Most-recent event for model + context_size_tokens.
        if ev_rows:
            last_ev = ev_rows[-1]
            model: str | None = last_ev["model"]
            ctx_tokens = (
                last_ev["tokens_input"]
                + last_ev["tokens_cache_create"]
                + last_ev["tokens_cache_read"]
            )
        else:
            model = None
            ctx_tokens = 0

        # Cumulative cost.
        null_count = sum(1 for r in ev_rows if r["cost_micro_usd"] is None)
        cost_sum = sum(r["cost_micro_usd"] for r in ev_rows if r["cost_micro_usd"] is not None)

        if msg_count == 0 or null_count == msg_count:
            cumulative_cost_usd: float | None = None
            cost_known = msg_count == 0
        else:
            cumulative_cost_usd = _micro_to_usd(cost_sum)
            cost_known = null_count == 0

        raw_status = sr["status"] or "closed"
        if raw_status == "active":
            status: str = "active"
        elif raw_status == "closed":
            status = "ended"
        else:
            status = "idle"

        return SessionDetail(
            session_id=sr["session_id"],
            runtime=sr["provider"],
            project=sr["sub_slug"],
            cwd=sr["cwd"],
            model=model,
            started_at=sr["first_event_at"],
            last_activity_at=sr["last_event_at"],
            message_count=msg_count,
            context_size_tokens=ctx_tokens,
            cumulative_cost_usd=cumulative_cost_usd,
            cost_known=cost_known,
            status=status,  # type: ignore[arg-type]
            agent_name=sr["agent_name"],
            ai_title=sr["ai_title"],
            event_timestamps=event_timestamps,
        )
