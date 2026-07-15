"""Direct unit pin of caller-owned ``resolve_context_for_cli`` resolution
and its context-NAME allowlist guard (v0.1.80 FR3).

The seam never borrows a foreign first-ALIVE context. Consumer workspaces must bind
or pass a context explicitly; only the recognizable source checkout gets the
self-hosting slug fallback.

v0.1.80 FR3 (backlog ``20260711-context-name-allowlist-at-resolution-rungs``, P4,
security-review INFO defense-in-depth): both the ``explicit`` and ``DADAIA_CONTEXT``
env rungs feed a ``repos/<name>/specs`` path join further downstream, unvalidated.
Applies the existing ``[A-Za-z0-9_-]+`` allowlist (mirrored from
``core.specs_resolver._CONTEXT_NAME_RE`` / ``features.spec_context.presence._valid_name``)
at the seam, BEFORE any path join:

- a traversal-shaped ``explicit`` argument is INTENTIONAL operator input — reject it
  loudly with an actionable ``ValueError`` (this module is not typer-bound, so callers
  surface the message themselves);
- a traversal-shaped ``DADAIA_CONTEXT`` env value is AMBIENT (not a deliberate call-site
  argument) — treat it as unset and fall through to the next resolution rung, never
  crash a CLI invocation over inherited/stale environment.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.cli._specs_resolution import resolve_context_for_cli

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
    for var in (
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.usefixtures("_clean_session_env")
@pytest.mark.parametrize("contexts", [[], ["consumer-only-context"]])
def test_unbound_consumer_never_selects_first_alive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    contexts: list[str],
) -> None:
    ws = tmp_path / "ws"
    _mk_workspace(ws, contexts)
    monkeypatch.chdir(ws)
    with pytest.raises(ValueError, match="context bind"):
        resolve_context_for_cli(None)


@pytest.mark.usefixtures("_clean_session_env")
def test_explicit_and_env_resolve_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "ws"
    _mk_workspace(ws, ["alive-ctx"])
    monkeypatch.chdir(ws)
    assert resolve_context_for_cli("explicit-ctx") == "explicit-ctx"
    monkeypatch.setenv("DADAIA_CONTEXT", "env-ctx")
    assert resolve_context_for_cli(None) == "env-ctx"


# --- FR3: context-name allowlist at the explicit/env resolution rungs ----------------


#: Non-empty traversal/injection-shaped names. Excludes the empty string deliberately:
#: ``""`` is FALSY, so it already falls through BOTH rungs' pre-existing ``if value:``
#: truthiness checks before reaching the allowlist guard at all (identical to "not
#: provided") — it is never a validation case, at either rung.
_TRAVERSAL_SHAPED_NAMES = [
    pytest.param("../escape", id="parent-traversal"),
    pytest.param("../../etc/passwd", id="deep-parent-traversal"),
    pytest.param("a/b", id="embedded-slash"),
    pytest.param("ctx/../../x", id="mixed-traversal"),
    pytest.param(".", id="dot"),
    pytest.param("..", id="dotdot"),
    pytest.param("ctx name", id="embedded-space"),
    pytest.param("ctx;rm -rf", id="shell-metacharacter"),
]


@pytest.mark.usefixtures("_clean_session_env")
@pytest.mark.parametrize("name", _TRAVERSAL_SHAPED_NAMES)
def test_traversal_shaped_explicit_raises_actionable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """A traversal-shaped ``explicit`` argument is deliberate operator input — the seam
    rejects it loudly, before any ``repos/<name>/specs`` path join, with a message that
    names the offending value and the allowlist it violates."""
    ws = tmp_path / "ws"
    _mk_workspace(ws, ["alive-ctx"])
    monkeypatch.chdir(ws)
    with pytest.raises(ValueError, match="context") as exc_info:
        resolve_context_for_cli(name)
    # Actionable: the message names the rejected value so an operator can see what was
    # typed/passed, not just "invalid context".
    assert repr(name) in str(exc_info.value) or name in str(exc_info.value)


@pytest.mark.usefixtures("_clean_session_env")
@pytest.mark.parametrize("name", _TRAVERSAL_SHAPED_NAMES)
def test_traversal_shaped_env_is_skipped_not_crashed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """A traversal-shaped ``DADAIA_CONTEXT`` env value is AMBIENT (inherited shell state,
    not a deliberate call-site argument) — the seam treats it as unset and falls through
    to the next resolution rung (first-ALIVE here) rather than raising."""
    ws = tmp_path / "ws"
    _mk_workspace(ws, ["alive-ctx"])
    monkeypatch.chdir(ws)
    monkeypatch.setenv("DADAIA_CONTEXT", name)
    with pytest.raises(ValueError, match="context bind"):
        resolve_context_for_cli(None)


@pytest.mark.usefixtures("_clean_session_env")
def test_empty_string_explicit_and_env_fall_through_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pins pre-existing behavior (regression guard, not new FR3 behavior): an empty
    string is FALSY at both rungs' own ``if value:`` checks, so it is treated exactly
    like "not provided" and falls through to the next rung — it never reaches the
    allowlist guard, and the guard must not change this."""
    ws = tmp_path / "ws"
    _mk_workspace(ws, ["alive-ctx"])
    monkeypatch.chdir(ws)
    with pytest.raises(ValueError, match="context bind"):
        resolve_context_for_cli("")
    monkeypatch.setenv("DADAIA_CONTEXT", "")
    with pytest.raises(ValueError, match="context bind"):
        resolve_context_for_cli(None)


@pytest.mark.usefixtures("_clean_session_env")
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("valid-ctx", id="hyphenated"),
        pytest.param("valid_ctx", id="underscored"),
        pytest.param("ValidCtx123", id="mixed-case-alnum"),
    ],
)
def test_valid_names_unchanged_at_explicit_and_env_rungs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """The allowlist guard must not regress any name matching ``[A-Za-z0-9_-]+`` — the
    exact behavior at HEAD (no exception, value passed through) is preserved."""
    ws = tmp_path / "ws"
    _mk_workspace(ws, ["alive-ctx"])
    monkeypatch.chdir(ws)
    assert resolve_context_for_cli(name) == name
    monkeypatch.setenv("DADAIA_CONTEXT", name)
    assert resolve_context_for_cli(None) == name
