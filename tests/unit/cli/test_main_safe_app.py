"""The CLI entry point surfaces failures without creating legacy bug state."""

from __future__ import annotations

import pytest

from dadaia_workspace.cli import main as cli_main
from dadaia_workspace.core.exceptions import DadaiaError, TasksMarkerStateError

pytestmark = pytest.mark.unit


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


# ---------------------------------------------------------------------------
# Bug f22-cli-boundary-is-a-whitelist-not-a-boundary.
#
# F-22 ("no raw traceback from any CLI verb") used to hold only for exceptions inside the
# DadaiaError hierarchy, because ``_safe_app`` caught exactly that. The package raises
# ~138 bare builtin exceptions, so the contract was a whitelist maintained by discipline
# and it kept leaking one verb at a time (the WorkspaceVenvBootstrapError escape, then the
# dangling-DADAIA_BOOTSTRAP_PACKAGE escape). These tests pin it as a BOUNDARY: whatever
# reaches the entry point becomes one line, and the traceback moves behind an opt-in.
# ---------------------------------------------------------------------------


def test_unexpected_exception_is_one_clean_line_not_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A bare builtin exception — outside the DadaiaError hierarchy — must not traceback."""
    monkeypatch.delenv("DADAIA_TRACEBACK", raising=False)

    def _boom() -> None:
        raise ValueError("DADAIA_BOOTSTRAP_PACKAGE must name an existing local wheel")

    monkeypatch.setattr(cli_main, "app", _boom)
    with pytest.raises(SystemExit) as exc:
        cli_main._safe_app()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "must name an existing local wheel" in err
    # The type is named: an unexpected error is a defect, and the reader needs to know
    # which one to report without asking for a traceback.
    assert "ValueError" in err
    # The reader is told how to get the traceback rather than being handed one.
    assert "DADAIA_TRACEBACK=1" in err


def test_traceback_opt_in_applies_to_dadaia_errors_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bug r6a-traceback-escape-hatch-suppressed (validator-reported).

    The opt-in was honoured only for *unexpected* exceptions, so it silently stopped
    working for any failure that was moved into the DadaiaError hierarchy — the developer
    debugging that very error is the one who loses the traceback.
    """
    monkeypatch.setenv("DADAIA_TRACEBACK", "1")

    def _boom() -> None:
        raise TasksMarkerStateError("marker gate")

    monkeypatch.setattr(cli_main, "app", _boom)
    with pytest.raises(TasksMarkerStateError, match="marker gate"):
        cli_main._safe_app()


def test_traceback_stays_available_behind_an_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Debuggability is preserved: ``DADAIA_TRACEBACK=1`` re-raises untouched.

    Without this the boundary would trade one bad failure mode (traceback in an operator's
    face) for another (no way to debug a real defect).
    """
    monkeypatch.setenv("DADAIA_TRACEBACK", "1")

    def _boom() -> None:
        raise ValueError("boom")

    monkeypatch.setattr(cli_main, "app", _boom)
    with pytest.raises(ValueError, match="boom"):
        cli_main._safe_app()


@pytest.mark.parametrize("value", ["", "0", "false", "no"])
def test_falsy_traceback_values_do_not_enable_the_opt_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], value: str
) -> None:
    """An exported-but-off variable must not silently turn tracebacks back on."""
    monkeypatch.setenv("DADAIA_TRACEBACK", value)

    def _boom() -> None:
        raise ValueError("boom")

    monkeypatch.setattr(cli_main, "app", _boom)
    with pytest.raises(SystemExit):
        cli_main._safe_app()
    assert "Traceback" not in capsys.readouterr().err


def test_systemexit_from_click_passes_through_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normal CLI exits must not be swallowed or rewritten by the boundary.

    Click/Typer signal every ordinary outcome — including ``--help`` and usage errors —
    by raising ``SystemExit``. A boundary that caught those would break exit codes for
    every verb, which is worse than the bug it fixes.
    """

    def _exit_two() -> None:
        raise SystemExit(2)

    monkeypatch.setattr(cli_main, "app", _exit_two)
    with pytest.raises(SystemExit) as exc:
        cli_main._safe_app()
    assert exc.value.code == 2


def test_keyboard_interrupt_is_not_reported_as_a_defect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ctrl-C is an operator action, not a dadaia defect — it must not be relabeled."""

    def _interrupt() -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_main, "app", _interrupt)
    with pytest.raises(KeyboardInterrupt):
        cli_main._safe_app()
