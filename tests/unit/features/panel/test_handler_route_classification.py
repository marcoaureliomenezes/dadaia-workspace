"""Unit tests for T-016-P05 — Auth route unification.

Invariants tested:
  1. Every route in _ROUTE_TABLE has an explicit AuthClass (no unclassified routes).
  2. No route name appears more than once in _ROUTE_TABLE (no duplicate registrations).
  3. DELETE /api/reports/<path>/important resolves to "api_report_mark_important"
     (the unmark action), NOT to "api_report_delete".
  4. DELETE /api/reports/<path> (without /important) resolves to "api_report_delete".
  5. _DELETE_ROUTE_TABLE has /important BEFORE the catch-all (structural ordering).
  6. The convenience sets (_BEARER_ONLY_ROUTE_NAMES, _SECOND_LOOP_AUTH_ROUTE_NAMES,
     _TELEMETRY_ROUTE_NAMES) are consistent with _ROUTE_TABLE.
  7. health route is PUBLIC (no auth required for monitoring probes).
  8. index route is PUBLIC.
  9. /api/agents requires BEARER_TELEMETRY.
  10. /api/panel-status requires BEARER_SECOND_LOOP.
"""

from __future__ import annotations

from dadaia_workspace.features.panel.handler import (
    _BEARER_ONLY_ROUTE_NAMES,
    _COMPILED_DELETE_ROUTE_TABLE,
    _DELETE_ROUTE_TABLE,
    _ROUTE_TABLE,
    _SECOND_LOOP_AUTH_ROUTE_NAMES,
    _TELEMETRY_ROUTE_NAMES,
    AuthClass,
)

# ---------------------------------------------------------------------------
# 1. Every route has an explicit AuthClass
# ---------------------------------------------------------------------------


def test_every_route_has_explicit_auth_class() -> None:
    """_ROUTE_TABLE must not contain any route without an explicit AuthClass."""
    for _pat, name, auth in _ROUTE_TABLE:
        assert isinstance(auth, AuthClass), (
            f"Route '{name}' has no AuthClass — add an explicit auth_class to _ROUTE_TABLE."
        )


# ---------------------------------------------------------------------------
# 2. No duplicate route names
# ---------------------------------------------------------------------------


def test_no_duplicate_route_names() -> None:
    """Each route name must appear exactly once in _ROUTE_TABLE."""
    names = [name for _, name, _ in _ROUTE_TABLE]
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in names:
        if name in seen:
            duplicates.append(name)
        seen.add(name)
    assert not duplicates, f"Duplicate route names in _ROUTE_TABLE: {duplicates}"


# ---------------------------------------------------------------------------
# 3 & 4. DELETE route ordering — /important before catch-all
# ---------------------------------------------------------------------------


def test_delete_important_resolves_to_mark_important_not_delete() -> None:
    """DELETE /api/reports/ctx/agent/report.html/important → api_report_mark_important."""
    test_path = (
        "/api/reports/dadaia-workspace/software-engineer/2026-01-01T000000Z-task.html/important"
    )
    matched_name: str | None = None
    for pattern, name in _COMPILED_DELETE_ROUTE_TABLE:
        if pattern.match(test_path):
            matched_name = name
            break
    assert matched_name == "api_report_mark_important", (
        f"DELETE {test_path!r} resolved to {matched_name!r}, expected 'api_report_mark_important'. "
        "Check that the /important pattern comes BEFORE the catch-all in _DELETE_ROUTE_TABLE."
    )


def test_delete_catchall_resolves_to_report_delete() -> None:
    """DELETE /api/reports/<path> (no /important) → api_report_delete."""
    test_path = "/api/reports/dadaia-workspace/software-engineer/2026-01-01T000000Z-task.html"
    matched_name: str | None = None
    for pattern, name in _COMPILED_DELETE_ROUTE_TABLE:
        if pattern.match(test_path):
            matched_name = name
            break
    assert matched_name == "api_report_delete", (
        f"DELETE {test_path!r} resolved to {matched_name!r}, expected 'api_report_delete'."
    )


# ---------------------------------------------------------------------------
# 5. _DELETE_ROUTE_TABLE structural ordering
# ---------------------------------------------------------------------------


def test_delete_route_table_important_before_catchall() -> None:
    """The /important entry must come before the catch-all in _DELETE_ROUTE_TABLE."""
    names_in_order = [name for _, name in _DELETE_ROUTE_TABLE]
    assert "api_report_mark_important" in names_in_order, (
        "_DELETE_ROUTE_TABLE must contain 'api_report_mark_important'."
    )
    assert "api_report_delete" in names_in_order, (
        "_DELETE_ROUTE_TABLE must contain 'api_report_delete'."
    )
    idx_mark = names_in_order.index("api_report_mark_important")
    idx_delete = names_in_order.index("api_report_delete")
    assert idx_mark < idx_delete, (
        f"'api_report_mark_important' (pos {idx_mark}) must come before "
        f"'api_report_delete' (pos {idx_delete}) in _DELETE_ROUTE_TABLE."
    )


# ---------------------------------------------------------------------------
# 6. Convenience sets consistent with _ROUTE_TABLE
# ---------------------------------------------------------------------------


def test_bearer_only_set_matches_route_table() -> None:
    """_BEARER_ONLY_ROUTE_NAMES must exactly equal routes with AuthClass.BEARER."""
    expected = frozenset(name for _, name, auth in _ROUTE_TABLE if auth == AuthClass.BEARER)
    assert expected == _BEARER_ONLY_ROUTE_NAMES, (
        f"_BEARER_ONLY_ROUTE_NAMES {_BEARER_ONLY_ROUTE_NAMES!r} does not match "
        f"BEARER routes in _ROUTE_TABLE {expected!r}."
    )


def test_second_loop_set_matches_route_table() -> None:
    """_SECOND_LOOP_AUTH_ROUTE_NAMES must exactly equal BEARER_SECOND_LOOP routes."""
    expected = frozenset(
        name for _, name, auth in _ROUTE_TABLE if auth == AuthClass.BEARER_SECOND_LOOP
    )
    assert expected == _SECOND_LOOP_AUTH_ROUTE_NAMES, (
        f"_SECOND_LOOP_AUTH_ROUTE_NAMES {_SECOND_LOOP_AUTH_ROUTE_NAMES!r} does not match "
        f"BEARER_SECOND_LOOP routes in _ROUTE_TABLE {expected!r}."
    )


def test_telemetry_set_matches_route_table() -> None:
    """_TELEMETRY_ROUTE_NAMES must exactly equal BEARER_TELEMETRY routes."""
    expected = frozenset(
        name for _, name, auth in _ROUTE_TABLE if auth == AuthClass.BEARER_TELEMETRY
    )
    assert expected == _TELEMETRY_ROUTE_NAMES, (
        f"_TELEMETRY_ROUTE_NAMES {_TELEMETRY_ROUTE_NAMES!r} does not match "
        f"BEARER_TELEMETRY routes in _ROUTE_TABLE {expected!r}."
    )


# ---------------------------------------------------------------------------
# 7–10. Specific route classifications
# ---------------------------------------------------------------------------


def _get_auth(route_name: str) -> AuthClass | None:
    for _, name, auth in _ROUTE_TABLE:
        if name == route_name:
            return auth
    return None


def test_health_is_public() -> None:
    """health route must be PUBLIC (no auth required for monitoring probes)."""
    assert _get_auth("health") == AuthClass.PUBLIC


def test_index_is_public() -> None:
    """index route must be PUBLIC."""
    assert _get_auth("index") == AuthClass.PUBLIC


def test_static_is_public() -> None:
    """static route must be PUBLIC (assets served without auth)."""
    assert _get_auth("static") == AuthClass.PUBLIC


def test_api_agents_requires_bearer_telemetry() -> None:
    """api_agents must require BEARER_TELEMETRY."""
    assert _get_auth("api_agents") == AuthClass.BEARER_TELEMETRY


def test_api_panel_status_requires_second_loop_auth() -> None:
    """api_panel_status must require BEARER_SECOND_LOOP (workspace-sensitive data)."""
    assert _get_auth("api_panel_status") == AuthClass.BEARER_SECOND_LOOP


def test_api_contexts_requires_second_loop_auth() -> None:
    """api_contexts must require BEARER_SECOND_LOOP (repo filesystem paths)."""
    assert _get_auth("api_contexts") == AuthClass.BEARER_SECOND_LOOP


def test_api_kanban_requires_bearer() -> None:
    """api_kanban must require BEARER (no telemetry needed)."""
    assert _get_auth("api_kanban") == AuthClass.BEARER


def test_api_reports_requires_bearer() -> None:
    """api_reports must require BEARER."""
    assert _get_auth("api_reports") == AuthClass.BEARER


def test_api_report_delete_requires_bearer() -> None:
    """api_report_delete must require BEARER."""
    assert _get_auth("api_report_delete") == AuthClass.BEARER


def test_api_report_mark_important_requires_bearer() -> None:
    """api_report_mark_important must require BEARER."""
    assert _get_auth("api_report_mark_important") == AuthClass.BEARER


def test_memory_requires_second_loop_auth() -> None:
    """memory route must require BEARER_SECOND_LOOP (serves workspace file content)."""
    assert _get_auth("memory") == AuthClass.BEARER_SECOND_LOOP


def test_memory_view_requires_second_loop_auth() -> None:
    """memory_view route must require BEARER_SECOND_LOOP."""
    assert _get_auth("memory_view") == AuthClass.BEARER_SECOND_LOOP


def test_reports_serve_requires_second_loop_auth() -> None:
    """reports_serve must require BEARER_SECOND_LOOP (serves HTML report files)."""
    assert _get_auth("reports_serve") == AuthClass.BEARER_SECOND_LOOP


def test_api_sessions_requires_bearer_telemetry() -> None:
    """api_sessions must require BEARER_TELEMETRY."""
    assert _get_auth("api_sessions") == AuthClass.BEARER_TELEMETRY


def test_api_session_detail_requires_bearer_telemetry() -> None:
    """api_session_detail must require BEARER_TELEMETRY."""
    assert _get_auth("api_session_detail") == AuthClass.BEARER_TELEMETRY


def test_api_agent_sessions_requires_bearer_telemetry() -> None:
    """api_agent_sessions must require BEARER_TELEMETRY."""
    assert _get_auth("api_agent_sessions") == AuthClass.BEARER_TELEMETRY
