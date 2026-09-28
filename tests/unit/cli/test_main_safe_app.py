"""The CLI entry point is a BOUNDARY: whatever reaches ``_safe_app`` becomes one stderr line
and exit 1; the traceback moves behind ``DADAIA_TRACEBACK=1``; ordinary exits pass through.

Intent: CONTRACT — bugs f22-cli-boundary-is-a-whitelist-not-a-boundary (a bare builtin
exception outside the DadaiaError hierarchy leaked a traceback), r6a-traceback-escape-hatch-suppressed
(the opt-in must cover DadaiaErrors too), implementation-reviews-no-task-markers-traceback.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.cli import main as cli_main
from dadaia_workspace.core.exceptions import DadaiaError

pytestmark = pytest.mark.unit


class TasksMarkerStateError(DadaiaError):
    """A stand-in operator-facing DadaiaError."""


_MARKER = TasksMarkerStateError("no recognizable task markers at implementation start")
_WHEEL = ValueError("DADAIA_BOOTSTRAP_PACKAGE must name an existing local wheel")


# fmt: off
@pytest.mark.parametrize(("raised", "traceback_env", "exit_code", "in_err"), [
    pytest.param(_MARKER, None, 1, ["no recognizable task markers"], id="dadaia-error-one-clean-line"),
    pytest.param(_WHEEL, None, 1, ["must name an existing local wheel", "ValueError", "DADAIA_TRACEBACK=1"], id="f22-builtin-error-named-with-opt-in-hint"),
    *[pytest.param(_WHEEL, v, 1, ["ValueError"], id=f"falsy-opt-in-{v or 'empty'}-stays-off") for v in ("", "0", "false", "no")],
    pytest.param(SystemExit(2), None, 2, [], id="click-systemexit-passes-through"),
    pytest.param(_MARKER, "1", None, [], id="r6a-opt-in-reraises-dadaia-error"),
    pytest.param(_WHEEL, "1", None, [], id="opt-in-reraises-builtin-error"),
    pytest.param(KeyboardInterrupt(), None, None, [], id="ctrl-c-is-not-a-defect"),
])
# fmt: on
def test_safe_app_turns_any_failure_into_one_line_unless_opted_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], raised: BaseException,
    traceback_env: str | None, exit_code: int | None, in_err: list[str],
) -> None:  # fmt: skip
    if traceback_env is None:
        monkeypatch.delenv("DADAIA_TRACEBACK", raising=False)
    else:
        monkeypatch.setenv("DADAIA_TRACEBACK", traceback_env)

    def _boom() -> None:
        raise raised

    monkeypatch.setattr(cli_main, "app", _boom)
    with pytest.raises(SystemExit if exit_code is not None else type(raised)) as caught:
        cli_main._safe_app()
    if exit_code is None:
        assert caught.value is raised
        return
    err = capsys.readouterr().err
    assert caught.value.code == exit_code  # type: ignore[union-attr]
    assert "Traceback (most recent call last)" not in err
    assert err.count("\n") <= (1 if isinstance(raised, DadaiaError) else 2)  # a defect adds the report hint
    assert all(part in err for part in in_err)
