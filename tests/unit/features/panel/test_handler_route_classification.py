"""Unit tests for T-016-P05 — Auth route unification.

Two survivors:
  1. Table invariants: every route has an explicit AuthClass, no duplicate names,
     convenience sets exactly equal their AuthClass filter of _ROUTE_TABLE, and the
     DELETE /important-before-catchall ordering (both structural position AND
     resolution behavior — /important resolves to mark_important, the bare path to
     delete).
  2. Classification table param: health/index/static PUBLIC, agents/sessions
     TELEMETRY, reports/memory BEARER/SECOND_LOOP, the fragment route (+ capture),
     session-detail removed.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.panel.handler import (
    _BEARER_ONLY_ROUTE_NAMES,
    _COMPILED_DELETE_ROUTE_TABLE,
    _DELETE_ROUTE_TABLE,
    _ROUTE_TABLE,
    _SECOND_LOOP_AUTH_ROUTE_NAMES,
    _TELEMETRY_ROUTE_NAMES,
    AuthClass,
)

pytestmark = pytest.mark.unit


def _get_auth(route_name: str) -> AuthClass | None:
    for _, name, auth in _ROUTE_TABLE:
        if name == route_name:
            return auth
    return None


def _delete_match(path: str) -> str | None:
    for pattern, name in _COMPILED_DELETE_ROUTE_TABLE:
        if pattern.match(path):
            return name
    return None


# ---------------------------------------------------------------------------
# 1. Table invariants
# ---------------------------------------------------------------------------


def test_route_table_invariants() -> None:
    # Every route has an explicit AuthClass — no unclassified routes.
    for _pat, name, auth in _ROUTE_TABLE:
        assert isinstance(auth, AuthClass), (
            f"Route '{name}' has no AuthClass — add an explicit auth_class to _ROUTE_TABLE."
        )

    # No route name appears more than once.
    names = [name for _, name, _ in _ROUTE_TABLE]
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in names:
        if name in seen:
            duplicates.append(name)
        seen.add(name)
    assert not duplicates, f"Duplicate route names in _ROUTE_TABLE: {duplicates}"

    # Convenience sets are consistent with _ROUTE_TABLE (exact filter equality).
    expected_bearer = frozenset(name for _, name, auth in _ROUTE_TABLE if auth == AuthClass.BEARER)
    assert expected_bearer == _BEARER_ONLY_ROUTE_NAMES

    expected_second_loop = frozenset(
        name for _, name, auth in _ROUTE_TABLE if auth == AuthClass.BEARER_SECOND_LOOP
    )
    assert expected_second_loop == _SECOND_LOOP_AUTH_ROUTE_NAMES

    expected_telemetry = frozenset(
        name for _, name, auth in _ROUTE_TABLE if auth == AuthClass.BEARER_TELEMETRY
    )
    assert expected_telemetry == _TELEMETRY_ROUTE_NAMES

    # DELETE /important-before-catchall ordering: structural position...
    names_in_order = [name for _, name in _DELETE_ROUTE_TABLE]
    assert "api_report_mark_important" in names_in_order
    assert "api_report_delete" in names_in_order
    idx_mark = names_in_order.index("api_report_mark_important")
    idx_delete = names_in_order.index("api_report_delete")
    assert idx_mark < idx_delete, (
        f"'api_report_mark_important' (pos {idx_mark}) must come before "
        f"'api_report_delete' (pos {idx_delete}) in _DELETE_ROUTE_TABLE."
    )

    # ...AND actual resolution behavior against real paths.
    important_path = (
        "/api/reports/dadaia-workspace/software-engineer/2026-01-01T000000Z-task.html/important"
    )
    assert _delete_match(important_path) == "api_report_mark_important", (
        f"DELETE {important_path!r} must resolve to 'api_report_mark_important' — check that "
        "the /important pattern comes BEFORE the catch-all in _DELETE_ROUTE_TABLE."
    )
    bare_path = "/api/reports/dadaia-workspace/software-engineer/2026-01-01T000000Z-task.html"
    assert _delete_match(bare_path) == "api_report_delete"


# ---------------------------------------------------------------------------
# 2. Classification table param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("route_name", "expected_auth"),
    [
        pytest.param("health", AuthClass.PUBLIC, id="health-public"),
        pytest.param("index", AuthClass.PUBLIC, id="index-public"),
        pytest.param("static", AuthClass.PUBLIC, id="static-public"),
        pytest.param("api_agents", AuthClass.BEARER_TELEMETRY, id="api-agents-telemetry"),
        pytest.param("api_sessions", AuthClass.BEARER_TELEMETRY, id="api-sessions-telemetry"),
        pytest.param(
            "api_agent_sessions", AuthClass.BEARER_TELEMETRY, id="api-agent-sessions-telemetry"
        ),
        pytest.param(
            "api_panel_status", AuthClass.BEARER_SECOND_LOOP, id="api-panel-status-second-loop"
        ),
        pytest.param("api_contexts", AuthClass.BEARER_SECOND_LOOP, id="api-contexts-second-loop"),
        pytest.param("memory", AuthClass.BEARER_SECOND_LOOP, id="memory-second-loop"),
        pytest.param("memory_view", AuthClass.BEARER_SECOND_LOOP, id="memory-view-second-loop"),
        pytest.param("reports_serve", AuthClass.BEARER_SECOND_LOOP, id="reports-serve-second-loop"),
        pytest.param("api_reports", AuthClass.BEARER, id="api-reports-bearer"),
        pytest.param("api_report_delete", AuthClass.BEARER, id="api-report-delete-bearer"),
        pytest.param(
            "api_report_mark_important", AuthClass.BEARER, id="api-report-mark-important-bearer"
        ),
        pytest.param("api_session_detail", None, id="api-session-detail-removed-v0152"),
    ],
)
def test_route_classification_table(route_name: str, expected_auth: AuthClass | None) -> None:
    assert _get_auth(route_name) == expected_auth
