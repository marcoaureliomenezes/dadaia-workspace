"""Unit tests for GET /api/kanban.

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
    )


def test_kanban_schema_all_four_columns_present(tmp_path: Path) -> None:
    """Response has swimlanes, generated_at, and all four canonical §7 column lists."""
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
    for key in ("backlog", "release_def", "impl_review", "closure"):
        assert key in columns, f"Column key {key!r} missing"
        assert isinstance(columns[key], list), f"Column {key!r} is not a list"


def test_kanban_modes_land_in_expected_columns(tmp_path: Path) -> None:
    """Supported session modes land in their canonical §7 kanban columns.

    READ → backlog; SPEC → release_def;
    BOUND_IMPLEMENTATION → impl_review; BOUND_REVIEW → impl_review (combined).
    """
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_read", mode="READ")
    _write_session(sessions_dir, session_id="sess_spec", mode="SPEC")
    _write_session(sessions_dir, session_id="sess_impl", mode="BOUND_IMPLEMENTATION")
    _write_session(sessions_dir, session_id="sess_rev", mode="BOUND_REVIEW")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    columns = data["swimlanes"][0]["columns"]

    # READ → backlog
    assert columns["backlog"][0]["session_id"] == "sess_read"
    assert columns["backlog"][0]["mode"] == "READ"

    # SPEC → release_def
    assert columns["release_def"][0]["session_id"] == "sess_spec"
    assert columns["release_def"][0]["mode"] == "SPEC"

    # BOUND_IMPLEMENTATION and BOUND_REVIEW → impl_review (combined column)
    impl_review_ids = {c["session_id"] for c in columns["impl_review"]}
    assert "sess_impl" in impl_review_ids
    assert "sess_rev" in impl_review_ids
    assert len(columns["impl_review"]) == 2

    # closure column is always present but empty (no session mode maps to it yet)
    assert columns["closure"] == []


def test_kanban_empty_or_missing_sessions_dir_returns_empty_swimlanes(tmp_path: Path) -> None:
    """Missing or empty sessions directories return 200 with empty swimlanes."""
    view = render_api_kanban(tmp_path)
    status, _ct, body = view()
    assert status == 200
    data = json.loads(body)
    assert data["swimlanes"] == []
    assert "generated_at" in data

    sessions_dir = tmp_path / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "ignore.txt").write_text("not json", encoding="utf-8")
    status, _ct, body = view()
    assert status == 200
    assert json.loads(body)["swimlanes"] == []


def test_kanban_stale_and_fresh_sessions_are_flagged(tmp_path: Path) -> None:
    """Cards expose stale state according to last_seen_at and ttl_seconds."""
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
    # READ sessions land in "backlog" column
    cards = {c["session_id"]: c for c in data["swimlanes"][0]["columns"]["backlog"]}
    assert cards["sess_stale"]["is_stale"] is True
    assert cards["sess_fresh"]["is_stale"] is False


def test_kanban_unknown_mode_excluded_or_surfaced(tmp_path: Path) -> None:
    """Unknown mode is handled gracefully and appears in the fail-safe backlog column."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_unknown", mode="SOMETHING_WEIRD")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    # The card must appear somewhere — unknown modes fall back to backlog.
    columns = data["swimlanes"][0]["columns"]
    total_cards = sum(len(v) for v in columns.values())
    assert total_cards == 1, "Unknown-mode card must not be silently dropped"
    assert len(columns["backlog"]) == 1
    assert columns["backlog"][0]["mode"] == "SOMETHING_WEIRD"


def test_kanban_post_not_allowed(tmp_path: Path) -> None:
    """POST /api/kanban returns 405 Method Not Allowed."""
    handler_class = _make_handler(tmp_path)
    status, _body = _dispatch_post(handler_class, "/api/kanban")
    assert status == 405


def test_kanban_invalid_session_files_skipped(tmp_path: Path) -> None:
    """Corrupt files and files missing required fields are skipped."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    (sessions_dir / "corrupt.json").write_text("{not valid json", encoding="utf-8")
    (sessions_dir / "sess_bad.json").write_text(
        json.dumps({"session_id": "sess_bad", "mode": "READ"}),
        encoding="utf-8",
    )
    _write_session(sessions_dir, session_id="sess_valid", mode="READ")

    view = render_api_kanban(tmp_path)
    status, _ct, body = view()

    assert status == 200
    data = json.loads(body)
    assert len(data["swimlanes"]) == 1
    columns = data["swimlanes"][0]["columns"]
    # READ → backlog
    assert len(columns["backlog"]) == 1
    assert columns["backlog"][0]["session_id"] == "sess_valid"


def test_kanban_auth_enforced(tmp_path: Path) -> None:
    """Auth is required: tokenless ⇒ 401, valid Bearer ⇒ 200 (no loopback bypass)."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_auth", mode="READ")

    handler_class = _make_handler(tmp_path, token=_TEST_TOKEN)

    # Tokenless request → 401 even on loopback (sec F-3).
    status, body = _dispatch_get(handler_class, "/api/kanban")
    assert status == 401
    assert b"unauthorized" in body

    # Valid Bearer token → 200.
    status, body = _dispatch_get(handler_class, "/api/kanban", token=_TEST_TOKEN)
    assert status == 200
    data = json.loads(body)
    assert "swimlanes" in data


def test_kanban_session_card_shape(tmp_path: Path) -> None:
    """SessionCard must have all required fields with correct types.

    BOUND_IMPLEMENTATION lands in the combined impl_review column.
    """
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
    # BOUND_IMPLEMENTATION → impl_review (combined column)
    card = data["swimlanes"][0]["columns"]["impl_review"][0]

    assert card["session_id"] == "sess_shape"
    assert card["mode"] == "BOUND_IMPLEMENTATION"
    assert card["release"] == "rel-v1"
    assert card["runtime"] == "claude-code"
    assert card["pid"] == 99999
    assert card["last_seen_at"] == "2026-05-31T10:00:00Z"
    assert isinstance(card["is_stale"], bool)


def test_kanban_multiple_contexts_sorted(tmp_path: Path) -> None:
    """Multiple contexts produce multiple swimlanes sorted alphabetically.

    Also verifies correct column placement per the new §7 lifecycle mapping.
    """
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

    # Verify column placement for each swimlane
    lanes_by_ctx = {s["context"]: s["columns"] for s in data["swimlanes"]}
    assert len(lanes_by_ctx["z-project"]["backlog"]) == 1  # READ → backlog
    assert len(lanes_by_ctx["a-project"]["release_def"]) == 1  # SPEC → release_def
    assert len(lanes_by_ctx["m-project"]["impl_review"]) == 1  # BOUND_REVIEW → impl_review


def test_kanban_cards_sorted_by_session_id(tmp_path: Path) -> None:
    """Cards within a column are sorted by session_id for deterministic output."""
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    for sid in ("sess_ccc", "sess_aaa", "sess_bbb"):
        _write_session(sessions_dir, session_id=sid, context="same-ctx", mode="READ")

    view = render_api_kanban(tmp_path)
    _status, _ct, body = view()

    data = json.loads(body)
    # READ → backlog
    cards = data["swimlanes"][0]["columns"]["backlog"]
    ids = [c["session_id"] for c in cards]
    assert ids == sorted(ids), "Cards must be sorted by session_id"


def test_kanban_closure_column_always_present_and_empty(tmp_path: Path) -> None:
    """Closure column is always present in all swimlanes but always empty.

    No session mode currently maps to the closure phase, so the column is
    present-but-empty (correct design: the column is available, ready for future
    closure-phase session modes).
    """
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    # Write sessions for all known modes.
    _write_session(sessions_dir, session_id="sess_r", mode="READ")
    _write_session(sessions_dir, session_id="sess_s", mode="SPEC")
    _write_session(sessions_dir, session_id="sess_i", mode="BOUND_IMPLEMENTATION")
    _write_session(sessions_dir, session_id="sess_v", mode="BOUND_REVIEW")

    view = render_api_kanban(tmp_path)
    _status, _ct, body = view()

    data = json.loads(body)
    columns = data["swimlanes"][0]["columns"]

    assert "closure" in columns, "Closure column must always be present"
    assert columns["closure"] == [], "Closure column must always be empty (no mode maps to it)"


def test_kanban_impl_and_review_share_combined_column(tmp_path: Path) -> None:
    """BOUND_IMPLEMENTATION and BOUND_REVIEW both appear in the impl_review column.

    The XOR-lock dimming logic is retired; both modes share one combined column.
    """
    sessions_dir = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions_dir, session_id="sess_impl", mode="BOUND_IMPLEMENTATION")
    _write_session(sessions_dir, session_id="sess_rev", mode="BOUND_REVIEW")

    view = render_api_kanban(tmp_path)
    _status, _ct, body = view()

    data = json.loads(body)
    columns = data["swimlanes"][0]["columns"]

    # Both in impl_review
    impl_review_ids = {c["session_id"] for c in columns["impl_review"]}
    assert "sess_impl" in impl_review_ids
    assert "sess_rev" in impl_review_ids

    # All other columns empty
    assert columns["backlog"] == []
    assert columns["release_def"] == []
    assert columns["closure"] == []
