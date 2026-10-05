"""rc-9 AC3.1: the suite's whole env is one pure function — the operator's session out, the
temp home and the suite keys in (bugs outside-tmp-home-pin-coupled-to-session-hooks,
operator-env-scrub-row-leaves-stale-pinned-home)."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

_HOME = "/tmp/h"


# fmt: off
@pytest.mark.parametrize(("parent", "expected"), [
    pytest.param(
        {"PATH": "/bin", "HOME": "/op", "XDG_CACHE_HOME": "/op/.cache",
         "DADAIA_CONTEXT": "ghost", "DADAIA_SESSION_ID": "s", "DADAIA_PERSONA": "p",
         "CLAUDE_CODE_SESSION_ID": "c", "CODEX_SESSION_ID": "x", "CODEX_THREAD_ID": "t",
         "CLAUDE_AGENT_PERSONA": "a", "CODEX_AGENT_PERSONA": "b",
         "DADAIA_FENCED_ROOTS": "/fence", "DADAIA_REQUIRE_UVX": "1"},
        {"PATH": "/bin", "HOME": _HOME, "USERPROFILE": _HOME, "XDG_CACHE_HOME": f"{_HOME}/.cache",
         "LOCALAPPDATA": f"{_HOME}/AppData/Local", "KIMI_CODE_HOME": f"{_HOME}/.kimi-code",
         "PYTHONDONTWRITEBYTECODE": "1", "DADAIA_FENCED_ROOTS": "/fence", "DADAIA_REQUIRE_UVX": "1"},
        id="operator-out-temp-home-in",
    ),
])
# fmt: on
@pytest.mark.xfail(strict=True, reason="RED until J3.S2.T1")
def test_suite_env(parent: dict[str, str], expected: dict[str, str]) -> None:
    from tests.fixtures.harness_env import suite_env

    assert suite_env(parent, PurePosixPath(_HOME)) == expected
