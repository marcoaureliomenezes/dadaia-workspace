"""Service-level test for PI ingestion wiring (T-30-B-04 / A12).

Proves TelemetryService._do_refresh calls the PI reader (3rd tuple element) with
the resolved sessions dir; that a legacy 2-tuple reader factory still works
(PI ingestion skipped, no crash — back-compat); and that a PI reader raising an
error degrades gracefully (never crashes refresh()).
"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import Any

import pytest

from dadaia_workspace.features.telemetry.service import TelemetryService
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations


class _NoopClaude:
    def read_session_file(self, *_a: Any, **_k: Any) -> None:
        return None


class _NoopCodex:
    def read_codex_db(self, *_a: Any, **_k: Any) -> None:
        return None


class _RecordingPi:
    def __init__(self) -> None:
        self.calls: list[pathlib.Path] = []

    def read_pi_sessions(self, sessions_dir: pathlib.Path, _dao: Any, _now_iso: str) -> None:
        self.calls.append(sessions_dir)


class _BoomPi:
    def read_pi_sessions(self, *_a: Any, **_k: Any) -> None:
        raise OSError("boom")


class _FakeAggregator:
    pass


class _FakeSCS:
    pass


def _build(reader_factory: Any, state_dir: pathlib.Path, ws: pathlib.Path) -> TelemetryService:
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    dao = TelemetryDao(conn)

    return TelemetryService(
        dao_factory=lambda: dao,
        aggregator=_FakeAggregator(),
        reader_factory=reader_factory,
        pricing_module=type("_P", (), {"compute_cost": staticmethod(lambda *_a, **_k: None)})(),
        workspace_root=ws,
        state_dir=state_dir,
        spec_context_service=_FakeSCS(),
        _getuid_fn=lambda: 1000,
    )


def _env_override_reader_factory(pi: _RecordingPi) -> Any:
    return lambda: (_NoopClaude(), _NoopCodex(), pi)


@pytest.mark.parametrize(
    ("case", "reader_factory_fn", "env_setup", "post_assert"),
    [
        pytest.param(
            "env-override-invokes-pi-reader",
            "env-override",
            "pi-sessions",
            "pi-called-with-env-dir",
            id="env-override-invokes-pi-reader",
        ),
        pytest.param(
            "legacy-2-tuple-skips-pi",
            lambda: (_NoopClaude(), _NoopCodex()),
            None,
            None,
            id="legacy-2-tuple-skips-pi",
        ),
        pytest.param(
            "pi-reader-error-degrades",
            lambda: (_NoopClaude(), _NoopCodex(), _BoomPi()),
            "absent",
            None,
            id="pi-reader-error-degrades",
        ),
    ],
)
def test_refresh_never_raises_matrix(  # type: ignore[no-untyped-def]
    tmp_path: pathlib.Path,
    monkeypatch: Any,
    case: str,
    reader_factory_fn,
    env_setup: str | None,
    post_assert: str | None,
) -> None:
    pi = _RecordingPi()
    pi_dir: pathlib.Path | None = None
    if env_setup == "pi-sessions":
        pi_dir = tmp_path / "pi-sessions"
        pi_dir.mkdir()
        monkeypatch.setenv("DADAIA_PI_SESSIONS_DIR", str(pi_dir))
        reader_factory_fn = _env_override_reader_factory(pi)
    elif env_setup == "absent":
        monkeypatch.setenv("DADAIA_PI_SESSIONS_DIR", str(tmp_path / "absent"))

    svc = _build(reader_factory_fn, tmp_path / "state", tmp_path / "ws")
    svc.refresh()  # must not raise

    if post_assert == "pi-called-with-env-dir":
        assert pi.calls == [pi_dir]
