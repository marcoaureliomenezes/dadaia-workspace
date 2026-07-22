"""The CLI entry point surfaces failures without creating legacy bug state."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dadaia_workspace.cli import main as cli_main
from dadaia_workspace.core.exceptions import DadaiaError, TasksMarkerStateError

pytestmark = pytest.mark.unit


def test_safe_app_propagates_unexpected_failure() -> None:
    from dadaia_workspace.cli.main import _safe_app

    with (
        patch("dadaia_workspace.cli.main.app", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        _safe_app()


def test_safe_app_renders_tasks_marker_error_as_one_clean_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bug implementation-reviews-no-task-markers-traceback (CLI contract pin): the
    marker gate raises TasksMarkerStateError(DadaiaError) — through the real console
    entry point that surfaces as ONE stderr line + exit 1, never a raw traceback."""
    assert issubclass(TasksMarkerStateError, DadaiaError)

    def _boom() -> None:
        raise TasksMarkerStateError("no recognizable task markers at implementation start")

    monkeypatch.setattr(cli_main, "app", _boom)
    with pytest.raises(SystemExit) as exc:
        cli_main._safe_app()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert err.count("\n") <= 1
    assert "no recognizable task markers" in err
