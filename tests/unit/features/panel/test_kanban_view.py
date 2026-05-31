"""Unit tests for GET /api/kanban — AC-1.1 through AC-1.14.

Tests use:
- ``tmp_path`` (pytest fixture) as the workspace root.
- In-process ``_FakeSocket`` / handler dispatch (copied from test_handler.py)
  to exercise auth without spinning a real server.
- Direct calls to ``render_api_kanban`` for schema / data tests.
"""

from __future__ import annotations

import datetime
import io
import json
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.views.kanban import render_api_kanban

# ---------------------------------------------------------------------------
# Helpers — session file writing
# ---------------------------------------------------------------------------

_BASE_SESSION: dict[str, object] = {
    "session_id": "sess_aabbccdd",
    "context": "my-project",
    "mode": "READ",
    "release": "my-release-v1",
    "runtime": "claude-code",
    "pid": 12345,
    "last_seen_at": "2026-05-31T10:00:00Z",
    "ttl_seconds": 300,
    "is_stale": False,
    "bound_at": "2026-05-31T09:55:00Z",
}


def _write_session(
    sessions_dir: Path,
    session_id: str = "sess_aabbccdd",
    context: str = "my-project",
    mode: str = "READ",
    *,
    last_seen_at: str = "2026-05-31T10:00:00Z",
    ttl_seconds: int = 300,
    release: str | None = "my-release-v1",
    runtime: str = "claude-code",
    pid: int = 12345,
) -> Path:
    """Write a minimal valid session JSON file to *sessions_dir*."""
    sessions_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "session_id": session_id,
        "context": context,
        "mode": mode,
        "release": release,
        "runtime": runtime,
        "pid": pid,
        "last_seen_at": last_seen_at,
        "ttl_seconds": ttl_seconds,
        "is_stale": False,
        "bound_at": "2026-05-31T09:55:00Z",
    }
    path = sessions_dir / f"{session_id}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# In-process handler driver (mirrors test_handler.py)
# ---------------------------------------------------------------------------


class _FakeSocket:
    def __init__(self, request_bytes: bytes) -> None:
        self._rfile = io.BytesIO(request_bytes)
        self._wfile = io.BytesIO()

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        if "r" in mode:
            return self._rfile
        return self._wfile

    def getsockname(self) -> tuple[str, int]:
        return ("127.0.0.1", 4999)

    def getpeername(self) -> tuple[str, int]:
        return ("127.0.0.1", 12345)

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)

    def recv(self, n: int) -> bytes:
        return self._rfile.read(n)


def _dispatch_get(
    handler_class: type[BaseHTTPRequestHandler],
    path: str,
    token: str | None = None,
) -> tuple[int, bytes]:
    auth_line = f"Authorization: Bearer {token}\r\n" if token else ""
    raw_request = f"GET {path} HTTP/1.1\r\nHost: localhost\r\n{auth_line}\r\n".encode()
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = fake_sock._wfile.getvalue()
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


def _dispatch_post(
    handler_class: type[BaseHTTPRequestHandler],
    path: str,
    token: str | None = None,
) -> tuple[int, bytes]:
    auth_line = f"Authorization: Bearer {token}\r\n" if token else ""
    raw_request = f"POST {path} HTTP/1.1\r\nHost: localhost\r\n{auth_line}\r\n".encode()
    fake_sock = _FakeSocket(raw_request)
    handler_class(fake_sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = fake_sock._wfile.getvalue()
    status_line = response.split(b"\r\n", 1)[0]
    status_code = int(status_line.split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status_code, body


@dataclass
class _StubView:
    name: str
    call_count: int = 0
    last_kwargs: dict[str, object] = field(default_factory=dict)
    status: int = 200
    content_type: str = "application/json"
    body: bytes = b"{}"

    def __call__(self, **kwargs: object) -> tuple[int, str, bytes]:
        self.call_count += 1
        self.last_kwargs = dict(kwargs)
        return (self.status, self.content_type, self.body)


_TEST_TOKEN = "test-kanban-token"


def _make_handler(
    tmp_path: Path,
    *,
    loopback_bypass: bool = False,
    token: str | None = _TEST_TOKEN,
) -> type[BaseHTTPRequestHandler]:
    """Build a handler class with a real api_kanban view and minimal stubs."""
    kanban_view = render_api_kanban(tmp_path)
    views: dict[str, object] = {
        "index": _StubView(name="index", content_type="text/html", body=b"<html/>"),
        "api_panel_status": _StubView(name="api_panel_status"),
        "api_contexts": _StubView(name="api_contexts"),
        "health": _StubView(name="health"),
        "memory": _StubView(name="memory", content_type="text/html", body=b"<html/>"),
        "memory_view": _StubView(name="memory_view", content_type="text/html", body=b"<html/>"),
        "static": _StubView(name="static"),
        "api_kanban": kanban_view,
    }
    return make_handler_class(  # type: ignore[arg-type]
        views,  # type: ignore[arg-type]
        token=token,
        telemetry=None,
        loopback_bypass=loopback_bypass,
    )


# ---------------------------------------------------------------------------
# AC-1.1 — All four column keys present, each a list
# ---------------------------------------------------------------------------


def test_kanban_schema_all_four_columns_present(tmp_path: Path) -> None:
    """AC-1.1: Response has research, spec, implementation, review keys; each is a list."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_001", mode="READ")

    view = render_api_kanban(tmp_path)
    status, ct, body = view()

    assert status == 200
    assert "application/json" in ct
    data = json.loads(body)
    assert "swimlanes" in data
    assert "generated_at" in data
    # At least one swimlane for the context.
    assert len(data["swimlanes"]) == 1
    columns = data["swimlanes"][0]["columns"]
    for key in ("research", "spec", "implementation", "review"):
        assert key in columns, f"Column key {key!r} missing"
        assert isinstance(columns[key], list), f"Column {key!r} is not a list"


# ---------------------------------------------------------------------------
# AC-1.2 — READ mode → research column
# ---------------------------------------------------------------------------


def test_kanban_read_mode_lands_in_research_column(tmp_path: Path) -> None:
    """AC-1.2: mode='READ' session appears in the research column."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_read", mode="READ")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    columns = data["swimlanes"][0]["columns"]
    assert len(columns["research"]) == 1
    assert columns["research"][0]["session_id"] == "sess_read"
    assert columns["research"][0]["mode"] == "READ"
    for other in ("spec", "implementation", "review"):
        assert columns[other] == []


# ---------------------------------------------------------------------------
# AC-1.3 — SPEC mode → spec column
# ---------------------------------------------------------------------------


def test_kanban_spec_mode_lands_in_spec_column(tmp_path: Path) -> None:
    """AC-1.3: mode='SPEC' session appears in the spec column."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_spec", mode="SPEC")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    columns = data["swimlanes"][0]["columns"]
    assert len(columns["spec"]) == 1
    assert columns["spec"][0]["session_id"] == "sess_spec"


# ---------------------------------------------------------------------------
# AC-1.4 — BOUND_IMPLEMENTATION → implementation column
# ---------------------------------------------------------------------------


def test_kanban_bound_implementation_lands_in_implementation_column(tmp_path: Path) -> None:
    """AC-1.4: mode='BOUND_IMPLEMENTATION' session appears in the implementation column."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_impl", mode="BOUND_IMPLEMENTATION")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    columns = data["swimlanes"][0]["columns"]
    assert len(columns["implementation"]) == 1
    assert columns["implementation"][0]["session_id"] == "sess_impl"


# ---------------------------------------------------------------------------
# AC-1.5 — BOUND_REVIEW → review column
# ---------------------------------------------------------------------------


def test_kanban_bound_review_lands_in_review_column(tmp_path: Path) -> None:
    """AC-1.5: mode='BOUND_REVIEW' session appears in the review column."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_rev", mode="BOUND_REVIEW")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    columns = data["swimlanes"][0]["columns"]
    assert len(columns["review"]) == 1
    assert columns["review"][0]["session_id"] == "sess_rev"


# ---------------------------------------------------------------------------
# AC-1.6 — Missing sessions dir → 200 with empty swimlanes
# ---------------------------------------------------------------------------


def test_kanban_missing_sessions_dir_returns_200_empty(tmp_path: Path) -> None:
    """AC-1.6: No .dadaia/sessions/ directory → 200, swimlanes is empty list."""
    # Do NOT create the sessions directory.
    assert not (tmp_path / ".dadaia" / "sessions").exists()

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    assert data["swimlanes"] == []
    assert "generated_at" in data


# ---------------------------------------------------------------------------
# AC-1.7 — Empty sessions dir → 200 with empty swimlanes
# ---------------------------------------------------------------------------


def test_kanban_empty_sessions_dir_returns_200_empty(tmp_path: Path) -> None:
    """AC-1.7: Sessions directory exists but contains no JSON files → 200, empty swimlanes."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)
    # Write a non-JSON file to confirm only *.json are parsed.
    (sessions_dir / "ignore.txt").write_text("not json", encoding="utf-8")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    assert data["swimlanes"] == []


# ---------------------------------------------------------------------------
# AC-1.8 — Stale session flagged is_stale=True
# ---------------------------------------------------------------------------


def test_kanban_stale_session_flagged_is_stale_true(tmp_path: Path) -> None:
    """AC-1.8: last_seen_at 10 minutes ago, ttl_seconds=180 → is_stale=True."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    ten_min_ago = (
        (datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(minutes=10))
        .isoformat()
        .replace("+00:00", "Z")
    )
    _write_session(
        sessions_dir,
        session_id="sess_stale",
        mode="READ",
        last_seen_at=ten_min_ago,
        ttl_seconds=180,
    )

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    card = data["swimlanes"][0]["columns"]["research"][0]
    assert card["is_stale"] is True


# ---------------------------------------------------------------------------
# AC-1.9 — Fresh session flagged is_stale=False
# ---------------------------------------------------------------------------


def test_kanban_fresh_session_flagged_is_stale_false(tmp_path: Path) -> None:
    """AC-1.9: last_seen_at 30 s ago, ttl_seconds=300 → is_stale=False."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    thirty_sec_ago = (
        (datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(seconds=30))
        .isoformat()
        .replace("+00:00", "Z")
    )
    _write_session(
        sessions_dir,
        session_id="sess_fresh",
        mode="READ",
        last_seen_at=thirty_sec_ago,
        ttl_seconds=300,
    )

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    card = data["swimlanes"][0]["columns"]["research"][0]
    assert card["is_stale"] is False


# ---------------------------------------------------------------------------
# AC-1.10 — Unknown mode → no 500, card in research (fail-safe)
# ---------------------------------------------------------------------------


def test_kanban_unknown_mode_excluded_or_surfaced(tmp_path: Path) -> None:
    """AC-1.10: Unknown mode → graceful (no 500); card placed in research column."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_unknown", mode="SOMETHING_WEIRD")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    # The card must appear somewhere — spec allows research or excluded; we map to research.
    columns = data["swimlanes"][0]["columns"]
    total_cards = sum(len(v) for v in columns.values())
    assert total_cards == 1, "Unknown-mode card must not be silently dropped"
    assert len(columns["research"]) == 1
    assert columns["research"][0]["mode"] == "SOMETHING_WEIRD"


# ---------------------------------------------------------------------------
# AC-1.11 — POST /api/kanban → 405
# ---------------------------------------------------------------------------


def test_kanban_post_not_allowed(tmp_path: Path) -> None:
    """AC-1.11: POST /api/kanban → 405 Method Not Allowed."""
    handler_class = _make_handler(tmp_path, loopback_bypass=True)
    status, _body = _dispatch_post(handler_class, "/api/kanban")
    assert status == 405


# ---------------------------------------------------------------------------
# AC-1.12 — Corrupt JSON file skipped, valid session appears
# ---------------------------------------------------------------------------


def test_kanban_malformed_session_file_skipped(tmp_path: Path) -> None:
    """AC-1.12: Corrupt JSON file is silently skipped; valid session still appears."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Write a corrupt JSON file.
    (sessions_dir / "corrupt.json").write_text("{not valid json", encoding="utf-8")

    # Write a valid session file.
    _write_session(sessions_dir, session_id="sess_valid", mode="READ")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    # Valid session appears; corrupt file is skipped.
    assert len(data["swimlanes"]) == 1
    columns = data["swimlanes"][0]["columns"]
    assert len(columns["research"]) == 1
    assert columns["research"][0]["session_id"] == "sess_valid"


# ---------------------------------------------------------------------------
# AC-1.13 — loopback_bypass=False, no token → 401
# ---------------------------------------------------------------------------


def test_kanban_requires_auth_non_loopback(tmp_path: Path) -> None:
    """AC-1.13: loopback_bypass=False, no Authorization header → 401."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_auth", mode="READ")

    handler_class = _make_handler(tmp_path, loopback_bypass=False, token=_TEST_TOKEN)

    # No token supplied.
    status, body = _dispatch_get(handler_class, "/api/kanban")

    assert status == 401
    assert b"unauthorized" in body


# ---------------------------------------------------------------------------
# AC-1.14 — loopback_bypass=True → 200 without Authorization header
# ---------------------------------------------------------------------------


def test_kanban_no_auth_required_loopback_bind(tmp_path: Path) -> None:
    """AC-1.14: loopback_bypass=True → 200 without Authorization header."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_loop", mode="READ")

    handler_class = _make_handler(tmp_path, loopback_bypass=True, token=_TEST_TOKEN)

    # No token supplied.
    status, body = _dispatch_get(handler_class, "/api/kanban")

    assert status == 200
    data = json.loads(body)
    assert "swimlanes" in data


# ---------------------------------------------------------------------------
# Extra: SessionCard shape validation
# ---------------------------------------------------------------------------


def test_kanban_session_card_shape(tmp_path: Path) -> None:
    """SessionCard must have all required fields with correct types."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(
        sessions_dir,
        session_id="sess_shape",
        context="ctx-a",
        mode="BOUND_IMPLEMENTATION",
        last_seen_at="2026-05-31T10:00:00Z",
        ttl_seconds=300,
        release="rel-v1",
        runtime="claude-code",
        pid=99999,
    )

    view = render_api_kanban(tmp_path)
    _status, _ct, body = view()

    data = json.loads(body)
    card = data["swimlanes"][0]["columns"]["implementation"][0]

    assert card["session_id"] == "sess_shape"
    assert card["mode"] == "BOUND_IMPLEMENTATION"
    assert card["release"] == "rel-v1"
    assert card["runtime"] == "claude-code"
    assert card["pid"] == 99999
    assert card["last_seen_at"] == "2026-05-31T10:00:00Z"
    assert isinstance(card["is_stale"], bool)


# ---------------------------------------------------------------------------
# Extra: Multiple contexts → multiple swimlanes sorted by context name
# ---------------------------------------------------------------------------


def test_kanban_multiple_contexts_sorted(tmp_path: Path) -> None:
    """Multiple contexts produce multiple swimlanes sorted alphabetically."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_z", context="z-project", mode="READ")
    _write_session(sessions_dir, session_id="sess_a", context="a-project", mode="SPEC")
    _write_session(sessions_dir, session_id="sess_m", context="m-project", mode="BOUND_REVIEW")

    view = render_api_kanban(tmp_path)
    _status, _ct, body = view()

    data = json.loads(body)
    contexts = [s["context"] for s in data["swimlanes"]]
    assert contexts == sorted(contexts), "Swimlanes must be sorted by context name"
    assert contexts[0] == "a-project"
    assert contexts[-1] == "z-project"


# ---------------------------------------------------------------------------
# Extra: Cards within a column sorted by session_id
# ---------------------------------------------------------------------------


def test_kanban_cards_sorted_by_session_id(tmp_path: Path) -> None:
    """Cards within a column are sorted by session_id for deterministic output."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    for sid in ("sess_ccc", "sess_aaa", "sess_bbb"):
        _write_session(sessions_dir, session_id=sid, context="same-ctx", mode="READ")

    view = render_api_kanban(tmp_path)
    _status, _ct, body = view()

    data = json.loads(body)
    cards = data["swimlanes"][0]["columns"]["research"]
    ids = [c["session_id"] for c in cards]
    assert ids == sorted(ids), "Cards must be sorted by session_id"


# ---------------------------------------------------------------------------
# Extra: Missing required field → session skipped
# ---------------------------------------------------------------------------


def test_kanban_session_missing_required_field_skipped(tmp_path: Path) -> None:
    """A session file missing a required field (context) is silently skipped."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # File missing the 'context' field.
    bad = {"session_id": "sess_bad", "mode": "READ"}
    (sessions_dir / "sess_bad.json").write_text(json.dumps(bad), encoding="utf-8")

    # Write a valid session alongside.
    _write_session(sessions_dir, session_id="sess_good", mode="READ")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    # Only the valid session is in the output.
    all_cards = [c for lane in data["swimlanes"] for col in lane["columns"].values() for c in col]
    ids = [c["session_id"] for c in all_cards]
    assert "sess_good" in ids
    assert "sess_bad" not in ids
