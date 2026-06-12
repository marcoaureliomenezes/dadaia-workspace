"""Unit tests for GET /api/kanban — kanban-v2 (lifecycle-truth board).

kanban-v2 changes the board contract (see views/kanban.py docstring):

- Swimlanes are the ALIVE Spec Context set (injected ``alive_contexts`` provider),
  not "whatever has session files".
- The primary card per lane is the context's active release + phase, read from
  ``repos/<slug>/specs/releases/ACTIVE.md`` and placed in the phase's column.
- Only LIVE sessions render as cards (recorded pid alive via ``pid_probe``, OR a fresh
  heartbeat). Stale/dead session records are dropped.
- The ``backlog`` column is retired; live READ sessions go to an ``observers`` strip.
- Session cards carry mode/release/started_at/last_seen_at/age_seconds — never "unknown".

Tests use ``tmp_path`` as the workspace root and call ``render_api_kanban`` directly.
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
# Helpers
# ---------------------------------------------------------------------------


def _iso_secs_ago(seconds: int) -> str:
    dt = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(seconds=seconds)
    return dt.isoformat().replace("+00:00", "Z")


def _write_session(
    sessions_dir: Path,
    session_id: str = "sess_aabbccdd",
    context: str = "my-project",
    mode: str = "READ",
    *,
    last_seen_at: str | None = None,
    ttl_seconds: int = 300,
    release: str | None = "my-release-v1",
    pid: int = 12345,
    bound_at: str = "2026-05-31T09:55:00Z",
) -> Path:
    """Write a session record JSON. Defaults to a FRESH heartbeat (live)."""
    sessions_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "session_id": session_id,
        "context": context,
        "mode": mode,
        "release": release,
        "runtime": "unknown",
        "pid": pid,
        "last_seen_at": last_seen_at if last_seen_at is not None else _iso_secs_ago(10),
        "ttl_seconds": ttl_seconds,
        "bound_at": bound_at,
    }
    path = sessions_dir / f"{session_id}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _write_active(workspace: Path, slug: str, release: str, phase: str) -> None:
    active = workspace / "repos" / slug / "specs" / "releases" / "ACTIVE.md"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_text(f"---\nrelease: {release}\nphase: {phase}\n---\n", encoding="utf-8")


def _provider(*pairs: tuple[str, str]):
    def _p() -> list[tuple[str, str]]:
        return list(pairs)

    return _p


def _dead_probe(_pid: int) -> bool:
    return False


def _alive_probe(_pid: int) -> bool:
    return True


# ---------------------------------------------------------------------------
# In-process handler driver (for auth/method tests)
# ---------------------------------------------------------------------------


class _FakeSocket:
    def __init__(self, request_bytes: bytes) -> None:
        self._rfile = io.BytesIO(request_bytes)
        self._wfile = io.BytesIO()

    def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
        return self._rfile if "r" in mode else self._wfile

    def getsockname(self) -> tuple[str, int]:
        return ("127.0.0.1", 4999)

    def getpeername(self) -> tuple[str, int]:
        return ("127.0.0.1", 12345)

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)

    def recv(self, n: int) -> bytes:
        return self._rfile.read(n)


def _dispatch(
    handler_class: type[BaseHTTPRequestHandler], method: str, path: str
) -> tuple[int, bytes]:
    raw = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode()
    sock = _FakeSocket(raw)
    handler_class(sock, ("127.0.0.1", 12345), None)  # type: ignore[arg-type]
    response = sock._wfile.getvalue()
    status = int(response.split(b"\r\n", 1)[0].split(b" ")[1])
    body = response.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in response else b""
    return status, body


@dataclass
class _StubView:
    name: str
    status: int = 200
    content_type: str = "application/json"
    body: bytes = b"{}"
    call_count: int = 0
    last_kwargs: dict[str, object] = field(default_factory=dict)

    def __call__(self, **kwargs: object) -> tuple[int, str, bytes]:
        self.call_count += 1
        self.last_kwargs = dict(kwargs)
        return (self.status, self.content_type, self.body)


def _make_handler(tmp_path: Path) -> type[BaseHTTPRequestHandler]:
    views: dict[str, object] = {
        "index": _StubView(name="index", content_type="text/html", body=b"<html/>"),
        "api_panel_status": _StubView(name="api_panel_status"),
        "api_contexts": _StubView(name="api_contexts"),
        "health": _StubView(name="health"),
        "memory": _StubView(name="memory", content_type="text/html", body=b"<html/>"),
        "memory_view": _StubView(name="memory_view", content_type="text/html", body=b"<html/>"),
        "static": _StubView(name="static"),
        "api_kanban": render_api_kanban(tmp_path),
    }
    return make_handler_class(views, telemetry=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_kanban_schema_v2_columns_and_observers(tmp_path: Path) -> None:
    """Response is kanban-v2: 3 lifecycle columns + observers strip per lane."""
    _write_session(tmp_path / ".dadaia" / "sessions", session_id="sess_001", context="my-project")
    view = render_api_kanban(tmp_path, alive_contexts=_provider(("my-project", "my-project")))
    status, ct, body = view()

    assert status == 200
    assert "application/json" in ct
    data = json.loads(body)
    assert data["schema"] == "kanban-v2"
    assert "generated_at" in data
    assert len(data["swimlanes"]) == 1
    lane = data["swimlanes"][0]
    for key in ("release_def", "impl_review", "closure"):
        assert key in lane["columns"]
        assert isinstance(lane["columns"][key], list)
    assert "backlog" not in lane["columns"], "backlog column is retired in v2"
    assert isinstance(lane["observers"], list)


def test_swimlanes_are_alive_contexts_even_with_no_sessions(tmp_path: Path) -> None:
    """Every ALIVE context gets a lane even with zero sessions (idle project visible)."""
    view = render_api_kanban(
        tmp_path,
        alive_contexts=_provider(("alpha", "alpha"), ("beta", "beta")),
    )
    _status, _ct, body = view()
    data = json.loads(body)
    contexts = [s["context"] for s in data["swimlanes"]]
    assert contexts == ["alpha", "beta"]  # sorted
    for lane in data["swimlanes"]:
        total = sum(len(v) for v in lane["columns"].values()) + len(lane["observers"])
        assert total == 0


# ---------------------------------------------------------------------------
# Release cards from ACTIVE.md
# ---------------------------------------------------------------------------


def test_release_card_lands_in_phase_column(tmp_path: Path) -> None:
    """ACTIVE.md phase decides the release card's column."""
    _write_active(tmp_path, "impl-ctx", "v0.1.13", "IMPLEMENTATION")
    _write_active(tmp_path, "def-ctx", "spec-v1", "DEFINITION")
    _write_active(tmp_path, "close-ctx", "rel-v9", "CLOSURE")

    view = render_api_kanban(
        tmp_path,
        alive_contexts=_provider(
            ("impl-ctx", "impl-ctx"), ("def-ctx", "def-ctx"), ("close-ctx", "close-ctx")
        ),
    )
    _status, _ct, body = view()
    lanes = {s["context"]: s for s in json.loads(body)["swimlanes"]}

    impl = lanes["impl-ctx"]["columns"]["impl_review"]
    assert impl[0]["card_kind"] == "release"
    assert impl[0]["release"] == "v0.1.13"
    assert impl[0]["phase"] == "IMPLEMENTATION"

    assert lanes["def-ctx"]["columns"]["release_def"][0]["release"] == "spec-v1"
    assert lanes["close-ctx"]["columns"]["closure"][0]["release"] == "rel-v9"


def test_no_release_card_when_archived_or_none_or_absent(tmp_path: Path) -> None:
    """ARCHIVED / release:none / missing ACTIVE.md produce no release card."""
    _write_active(tmp_path, "arch-ctx", "old-v1", "ARCHIVED")
    _write_active(tmp_path, "none-ctx", "none", "DEFINITION")
    # absent-ctx: no ACTIVE.md at all.

    view = render_api_kanban(
        tmp_path,
        alive_contexts=_provider(
            ("arch-ctx", "arch-ctx"), ("none-ctx", "none-ctx"), ("absent-ctx", "absent-ctx")
        ),
    )
    _status, _ct, body = view()
    for lane in json.loads(body)["swimlanes"]:
        total = sum(len(v) for v in lane["columns"].values())
        assert total == 0, f"{lane['context']} should have no release card"


# ---------------------------------------------------------------------------
# Live-session filtering
# ---------------------------------------------------------------------------


def test_dead_session_dropped_when_pid_dead_and_heartbeat_stale(tmp_path: Path) -> None:
    """A stale-heartbeat session whose pid is dead is NOT rendered (the v1 trash bug)."""
    sessions = tmp_path / ".dadaia" / "sessions"
    _write_session(
        sessions,
        session_id="sess_dead",
        context="my-project",
        mode="BOUND_IMPLEMENTATION",
        last_seen_at=_iso_secs_ago(9 * 3600),  # 9h ago
        ttl_seconds=300,
    )
    view = render_api_kanban(
        tmp_path,
        alive_contexts=_provider(("my-project", "my-project")),
        pid_probe=_dead_probe,
    )
    _status, _ct, body = view()
    lane = json.loads(body)["swimlanes"][0]
    total = sum(len(v) for v in lane["columns"].values()) + len(lane["observers"])
    assert total == 0, "dead+stale session must not appear as a card"


def test_live_session_kept_when_pid_alive_even_if_heartbeat_stale(tmp_path: Path) -> None:
    """A stale-heartbeat session whose pid is alive is kept (pid veto)."""
    sessions = tmp_path / ".dadaia" / "sessions"
    _write_session(
        sessions,
        session_id="sess_pidalive",
        context="my-project",
        mode="BOUND_IMPLEMENTATION",
        last_seen_at=_iso_secs_ago(9 * 3600),
        ttl_seconds=300,
    )
    view = render_api_kanban(
        tmp_path,
        alive_contexts=_provider(("my-project", "my-project")),
        pid_probe=_alive_probe,
    )
    _status, _ct, body = view()
    impl = json.loads(body)["swimlanes"][0]["columns"]["impl_review"]
    assert [c["session_id"] for c in impl if c["card_kind"] == "session"] == ["sess_pidalive"]


def test_fresh_heartbeat_session_kept_without_probe(tmp_path: Path) -> None:
    """A fresh-heartbeat session is live even when no pid_probe is wired."""
    sessions = tmp_path / ".dadaia" / "sessions"
    _write_session(
        sessions,
        session_id="sess_fresh",
        context="my-project",
        mode="BOUND_IMPLEMENTATION",
        last_seen_at=_iso_secs_ago(20),
        ttl_seconds=300,
    )
    view = render_api_kanban(tmp_path, alive_contexts=_provider(("my-project", "my-project")))
    _status, _ct, body = view()
    impl = json.loads(body)["swimlanes"][0]["columns"]["impl_review"]
    assert any(c.get("session_id") == "sess_fresh" for c in impl)


# ---------------------------------------------------------------------------
# Mode → column / observers
# ---------------------------------------------------------------------------


def test_read_session_goes_to_observers_not_backlog(tmp_path: Path) -> None:
    """Live READ sessions land in the observers strip, never a lifecycle column."""
    sessions = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions, session_id="sess_read", context="my-project", mode="READ")
    view = render_api_kanban(tmp_path, alive_contexts=_provider(("my-project", "my-project")))
    _status, _ct, body = view()
    lane = json.loads(body)["swimlanes"][0]
    assert [c["session_id"] for c in lane["observers"]] == ["sess_read"]
    assert lane["observers"][0]["mode"] == "READ"
    assert sum(len(v) for v in lane["columns"].values()) == 0


def test_impl_and_review_share_impl_review_column(tmp_path: Path) -> None:
    sessions = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions, session_id="sess_impl", context="c", mode="BOUND_IMPLEMENTATION")
    _write_session(sessions, session_id="sess_rev", context="c", mode="BOUND_REVIEW")
    view = render_api_kanban(tmp_path, alive_contexts=_provider(("c", "c")))
    _status, _ct, body = view()
    impl = json.loads(body)["swimlanes"][0]["columns"]["impl_review"]
    ids = {c["session_id"] for c in impl if c["card_kind"] == "session"}
    assert ids == {"sess_impl", "sess_rev"}


def test_unknown_mode_goes_to_observers_failsafe(tmp_path: Path) -> None:
    sessions = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions, session_id="sess_weird", context="c", mode="SOMETHING_WEIRD")
    view = render_api_kanban(tmp_path, alive_contexts=_provider(("c", "c")))
    _status, _ct, body = view()
    lane = json.loads(body)["swimlanes"][0]
    assert [c["session_id"] for c in lane["observers"]] == ["sess_weird"]


def test_session_for_non_alive_context_is_dropped(tmp_path: Path) -> None:
    """A live session whose context is not ALIVE in the registry is an orphan → dropped."""
    sessions = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions, session_id="sess_orphan", context="ghost", mode="READ")
    view = render_api_kanban(tmp_path, alive_contexts=_provider(("real", "real")))
    _status, _ct, body = view()
    contexts = [s["context"] for s in json.loads(body)["swimlanes"]]
    assert contexts == ["real"]


# ---------------------------------------------------------------------------
# Card shape — never "unknown"
# ---------------------------------------------------------------------------


def test_session_card_shape_and_no_unknown_string(tmp_path: Path) -> None:
    sessions = tmp_path / ".dadaia" / "sessions"
    _write_session(
        sessions,
        session_id="sess_shape",
        context="ctx-a",
        mode="BOUND_IMPLEMENTATION",
        release="rel-v1",
        last_seen_at=_iso_secs_ago(30),
    )
    view = render_api_kanban(tmp_path, alive_contexts=_provider(("ctx-a", "ctx-a")))
    _status, _ct, body = view()
    raw = body.decode("utf-8")
    assert "unknown" not in raw, "v2 must never emit the literal 'unknown'"
    card = next(
        c
        for c in json.loads(body)["swimlanes"][0]["columns"]["impl_review"]
        if c["card_kind"] == "session"
    )
    assert card["session_id"] == "sess_shape"
    assert card["mode"] == "BOUND_IMPLEMENTATION"
    assert card["release"] == "rel-v1"
    assert card["started_at"] == "2026-05-31T09:55:00Z"
    assert isinstance(card["age_seconds"], int)
    assert "runtime" not in card and "pid" not in card


def test_release_and_session_cards_coexist_release_first(tmp_path: Path) -> None:
    """A lane can show both a release card and a live session card; release sorts first."""
    _write_active(tmp_path, "ctx-a", "v0.1.13", "IMPLEMENTATION")
    _write_session(
        tmp_path / ".dadaia" / "sessions",
        session_id="sess_zzz",
        context="ctx-a",
        mode="BOUND_IMPLEMENTATION",
    )
    view = render_api_kanban(tmp_path, alive_contexts=_provider(("ctx-a", "ctx-a")))
    _status, _ct, body = view()
    impl = json.loads(body)["swimlanes"][0]["columns"]["impl_review"]
    assert impl[0]["card_kind"] == "release"
    assert impl[-1]["card_kind"] == "session"


# ---------------------------------------------------------------------------
# Robustness / back-compat
# ---------------------------------------------------------------------------


def test_invalid_session_files_skipped(tmp_path: Path) -> None:
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / "corrupt.json").write_text("{not valid json", encoding="utf-8")
    (sessions / "sess_bad.json").write_text(
        json.dumps({"session_id": "sess_bad", "mode": "READ"}), encoding="utf-8"
    )
    _write_session(sessions, session_id="sess_valid", context="c", mode="READ")
    view = render_api_kanban(tmp_path, alive_contexts=_provider(("c", "c")))
    _status, _ct, body = view()
    lane = json.loads(body)["swimlanes"][0]
    assert [c["session_id"] for c in lane["observers"]] == ["sess_valid"]


def test_no_provider_falls_back_to_session_derived_lanes(tmp_path: Path) -> None:
    """Without an injected provider the board is session-derived (back-compat)."""
    sessions = tmp_path / ".dadaia" / "sessions"
    _write_session(sessions, session_id="sess_a", context="proj", mode="BOUND_IMPLEMENTATION")
    view = render_api_kanban(tmp_path)  # no alive_contexts, no probe
    _status, _ct, body = view()
    data = json.loads(body)
    assert [s["context"] for s in data["swimlanes"]] == ["proj"]
    impl = data["swimlanes"][0]["columns"]["impl_review"]
    assert any(c.get("session_id") == "sess_a" for c in impl)


def test_empty_returns_empty_swimlanes(tmp_path: Path) -> None:
    view = render_api_kanban(tmp_path)
    status, _ct, body = view()
    assert status == 200
    data = json.loads(body)
    assert data["swimlanes"] == []
    assert data["schema"] == "kanban-v2"


def test_post_not_allowed(tmp_path: Path) -> None:
    handler_class = _make_handler(tmp_path)
    status, _body = _dispatch(handler_class, "POST", "/api/kanban")
    assert status == 405


def test_serves_without_credential(tmp_path: Path) -> None:
    _write_session(tmp_path / ".dadaia" / "sessions", session_id="sess_auth", context="c")
    handler_class = _make_handler(tmp_path)
    status, body = _dispatch(handler_class, "GET", "/api/kanban")
    assert status == 200
    assert "swimlanes" in json.loads(body)
