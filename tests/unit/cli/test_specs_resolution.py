"""Caller-owned ``resolve_context_for_cli`` resolution and its context-NAME allowlist (v0.1.80 FR3).

the seam never borrows a foreign first-ALIVE context; a traversal-shaped
``explicit`` (deliberate input) raises naming the value, a traversal-shaped ``DADAIA_CONTEXT``
(ambient) is treated as unset; sa-bind-has-two-stores#S1, #S2, #S3; T-50-02 rung 3 (the repo
containing cwd) resolves any registered ``repos/<slug>``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.cli._specs_resolution import resolve_context_for_cli
from tests.fixtures.harness_env import scrub_context_resolution_env

pytestmark = pytest.mark.unit


def _mk_workspace(root: Path, contexts: list[str]) -> None:
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": name,
                        "state": "alive",
                        "repo_slug": name,
                        "repo_url": f"https://example.invalid/{name}.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    }
                    for name in contexts
                ],
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def _clean_session_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bug ``specs-resolver-context-tests-flaky-under-xdist-full-suite``: no ambient
    session or context var leaks into these cwd-driven scenarios."""
    scrub_context_resolution_env(monkeypatch)


_REGISTERED = ["alive-ctx", "env-ctx", "valid-ctx", "valid_ctx", "ValidCtx123"]
_TRAVERSAL = [
    "../escape",
    "../../etc/passwd",
    "a/b",
    "ctx/../../x",
    ".",
    "..",
    "ctx name",
    "ctx;rm -rf",
]
_BIND = ValueError("context bind")


# fmt: off
@pytest.mark.usefixtures("_clean_session_env")
@pytest.mark.parametrize(("registered", "in_repo", "explicit", "env", "session", "expected"), [
    pytest.param([], False, None, None, None, _BIND, id="no-contexts-never-first-alive"),
    pytest.param(_REGISTERED, False, None, None, None, _BIND, id="unbound-consumer-never-first-alive"),
    pytest.param(_REGISTERED, False, "explicit-ctx", None, None, "explicit-ctx", id="explicit"),
    pytest.param(_REGISTERED, False, None, "env-ctx", None, "env-ctx", id="S1-S2-registered-env-is-the-bind"),
    pytest.param(_REGISTERED, False, None, "env-ctx", "native-no-record", _BIND, id="S2-native-session-without-record-ignores-env"),
    pytest.param(_REGISTERED, True, None, None, None, "alive-ctx", id="T-50-02-rung3-cwd-repo"),
    pytest.param(_REGISTERED, True, None, "../escape", None, "alive-ctx", id="S3-traversal-env-never-echoes-rung3-wins"),
    pytest.param(_REGISTERED, False, "", "", None, _BIND, id="empty-explicit-and-env-fall-through"),
    *[pytest.param(_REGISTERED, False, n, None, None, ValueError(n), id=f"explicit-traversal-raises-{n}") for n in _TRAVERSAL],
    *[pytest.param(_REGISTERED, False, None, n, None, _BIND, id=f"env-traversal-skipped-{n}") for n in _TRAVERSAL],
    *[pytest.param(_REGISTERED, False, n, None, None, n, id=f"valid-explicit-{n}") for n in _REGISTERED[2:]],
    *[pytest.param(_REGISTERED, False, None, n, None, n, id=f"valid-env-{n}") for n in _REGISTERED[2:]],
])
# fmt: on
def test_resolve_context_for_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, registered: list[str], in_repo: bool,
    explicit: str | None, env: str | None, session: str | None, expected: str | ValueError,
) -> None:  # fmt: skip
    ws = tmp_path / "ws"
    _mk_workspace(ws, registered)
    cwd = ws / "repos" / "alive-ctx" if in_repo else ws
    cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(cwd)
    if env is not None:
        monkeypatch.setenv("DADAIA_CONTEXT", env)
    if session:
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session)
    if isinstance(expected, ValueError):
        with pytest.raises(ValueError) as caught:
            resolve_context_for_cli(explicit)
        assert str(expected.args[0]) in str(caught.value)
    else:
        assert resolve_context_for_cli(explicit) == expected
