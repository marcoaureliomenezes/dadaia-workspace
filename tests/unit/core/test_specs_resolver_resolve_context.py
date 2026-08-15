"""T-50-01 (SPEC v0.5.0 FR1): the single context-resolution authority.

RED-first law tests for the two functions this task adds to ``core.specs_resolver`` —
``resolve_context`` and its slug->name inverse ``context_name_for_repo_slug``. Purely
additive: these tests never touch the five existing ladders (A/B/D/E/F) and none of the
existing pinning suites (``test_specs_resolver.py``, ``test_specs_resolver_harness_bind.py``,
``test_specs_resolver_delete_bind.py``) is modified.

``resolve_context`` implements ``DADAIA.md`` §3 verbatim, plus rung 0 (the caller's own
explicit input, which the law has always allowed a verb to pass):

    rung 0  ``explicit``, or the context derived from an explicit write TARGET
            (``target_path``) under ``<ws>/repos/<slug>/``
    rung 1  ``DADAIA_CONTEXT``
    rung 2  this session's own LIVE session record, keyed by the harness-native session id
            (``core.session_env.harness_session_id`` — NOT the ``DADAIA_SESSION_ID`` eval
            flow, which the SPEC does not name as a rung here)
    rung 3  the repo containing the current working directory

Rung 0's ``target_path`` and rung 3's cwd both resolve a repo **slug** first, then map it
to the context **NAME** via ``context_name_for_repo_slug`` — the registry inverse of
``repo_slug_for_context`` — because a context's name and its repo directory can differ.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core import specs_resolver
from tests.fixtures.harness_env import CONTEXT_RESOLUTION_ENV_VARS, scrub_context_resolution_env

_ENV_VARS_TO_CLEAR = CONTEXT_RESOLUTION_ENV_VARS


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize every rung-0/1/2 env var so each test sets exactly what it needs.

    ``CLAUDE_CODE_SESSION_ID`` is inherited from the live Claude Code session running
    these tests and would otherwise silently satisfy rung 2 in every test.
    ``WORKSPACE_ROOT`` (bug ``specs-resolver-context-tests-flaky-under-xdist-full-suite``):
    ``_authority_workspace_root()`` honours it UNCONDITIONALLY, ahead of and regardless
    of any ``monkeypatch.chdir()`` below -- an ambient value (inherited from the shell
    that launched pytest, or left behind by a concurrent ``dadaia context bind``/
    ``context show`` sharing the real ``.dadaia/sessions/`` tree) silently overrides
    every synthetic ``tmp_path`` workspace these tests build, unless scrubbed here too.
    """
    scrub_context_resolution_env(monkeypatch)


def _mk_ws(tmp_path: Path, *, slug: str = "proj", name: str | None = None) -> Path:
    """Build a minimal initialized workspace with one registered ALIVE context.

    ``name`` defaults to ``slug`` (the common case). Pass a different ``name`` to exercise
    the slug->name registry inversion.
    """
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [{"name": name or slug, "repo_slug": slug, "state": "alive"}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "repos" / slug / "specs").mkdir(parents=True)
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    return tmp_path


def _register_context(ws: Path, *, slug: str, name: str | None = None) -> None:
    """Add a second registered context to an existing workspace, and its repo dir."""
    registry = ws / ".dadaia" / "states" / "spec_contexts.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["contexts"].append({"name": name or slug, "repo_slug": slug, "state": "alive"})
    registry.write_text(json.dumps(data), encoding="utf-8")
    (ws / "repos" / slug / "specs").mkdir(parents=True, exist_ok=True)


def _write_harness_record(
    ws: Path, harness_id: str, context: str, *, age_seconds: int = 0, ttl: int = 300
) -> None:
    """Seed ``sessions/<harness_id>.json`` as ``bind`` would, with a controllable heartbeat age."""
    last_seen = (datetime.now(tz=UTC) - timedelta(seconds=age_seconds)).isoformat()
    (ws / ".dadaia" / "sessions" / f"{harness_id}.json").write_text(
        json.dumps(
            {
                "session_id": harness_id,
                "context": context,
                "mode": "READ",
                "last_seen_at": last_seen,
                "ttl_seconds": ttl,
                "pid": 424242,
            }
        ),
        encoding="utf-8",
    )


_HARNESS_ID = "claude-sess-t5001"


# --- rung 0: caller-supplied input ---------------------------------------------------


def test_rung0_explicit_wins_over_target_path_env_and_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _mk_ws(tmp_path, slug="x")
    _register_context(ws, slug="y")
    monkeypatch.setenv("DADAIA_CONTEXT", "y")
    monkeypatch.chdir(ws)
    target = ws / "repos" / "x" / "specs" / "TASKS.md"

    assert specs_resolver.resolve_context("explicit-ctx", target_path=target) == "explicit-ctx"


def test_rung0_target_path_under_repo_wins_over_dadaia_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The FR1 acceptance case named by name in the SPEC and the TASKS.md done-criterion:
    a write target under ``repos/x/`` resolves ``x`` even while ``DADAIA_CONTEXT=y``."""
    ws = _mk_ws(tmp_path, slug="x")
    _register_context(ws, slug="y")
    monkeypatch.setenv("DADAIA_CONTEXT", "y")
    monkeypatch.chdir(ws)
    target = ws / "repos" / "x" / "specs" / "releases" / "v1" / "TASKS.md"

    assert specs_resolver.resolve_context(target_path=target) == "x"


def test_rung0_target_path_maps_slug_to_context_name_via_registry_inverse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A context whose name differs from its repo directory (``repo_slug``): the write
    target resolves the DIRECTORY slug, and rung 0 maps it to the context NAME."""
    ws = _mk_ws(tmp_path, slug="beta-repo", name="alpha-context")
    monkeypatch.chdir(ws)
    target = ws / "repos" / "beta-repo" / "specs" / "SPEC.md"

    assert specs_resolver.resolve_context(target_path=target) == "alpha-context"


def test_rung0_target_path_outside_any_repo_falls_through_to_rung1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A target under no ``repos/<slug>/`` is not explicit input for ANY context — the
    ladder falls through to rung 1, matching the gate's existing path-first semantics."""
    ws = _mk_ws(tmp_path, slug="x")
    monkeypatch.setenv("DADAIA_CONTEXT", "y")
    monkeypatch.chdir(ws)
    target = ws / "specs" / "bugs" / "bugs.jsonl"

    assert specs_resolver.resolve_context(target_path=target) == "y"


def test_rung0_no_workspace_root_falls_through_to_rung1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``target_path`` supplied outside any initialized workspace never raises — it
    fails soft and falls through to the next rung."""
    monkeypatch.setenv("DADAIA_CONTEXT", "y")
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "repos" / "x" / "specs" / "SPEC.md"

    assert specs_resolver.resolve_context(target_path=target) == "y"


# --- rung 1: DADAIA_CONTEXT -----------------------------------------------------------


def test_rung1_dadaia_context_alone_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _mk_ws(tmp_path, slug="proj")
    monkeypatch.setenv("DADAIA_CONTEXT", "proj")
    monkeypatch.chdir(ws)

    assert specs_resolver.resolve_context() == "proj"


def test_rung1_wins_over_live_session_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _mk_ws(tmp_path, slug="proj")
    _register_context(ws, slug="other")
    _write_harness_record(ws, _HARNESS_ID, "other", age_seconds=0)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", _HARNESS_ID)
    monkeypatch.setenv("DADAIA_CONTEXT", "proj")
    monkeypatch.chdir(ws)

    assert specs_resolver.resolve_context() == "proj"


# --- rung 2: this session's own LIVE record, keyed by harness_session_id --------------


def test_rung2_live_session_record_resolves_ahead_of_cwd_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Isolates rung 2 from rung 3: the session is bound to ``proj`` but the cwd sits
    inside a DIFFERENT registered repo (``other``) — rung 2 must still win, proving it is
    consulted, and consulted before rung 3."""
    ws = _mk_ws(tmp_path, slug="proj")
    _register_context(ws, slug="other")
    _write_harness_record(ws, _HARNESS_ID, "proj", age_seconds=0)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", _HARNESS_ID)
    monkeypatch.chdir(ws / "repos" / "other")

    assert specs_resolver.resolve_context() == "proj"


def test_rung2_stale_record_falls_through_to_rung3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The FR4 liveness gate: a heartbeat-stale harness-keyed record must not resolve —
    the ladder falls through past it to rung 3 (the repo containing cwd)."""
    ws = _mk_ws(tmp_path, slug="proj")
    _register_context(ws, slug="other")
    _write_harness_record(ws, _HARNESS_ID, "proj", age_seconds=4000, ttl=300)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", _HARNESS_ID)
    monkeypatch.chdir(ws / "repos" / "other")

    assert specs_resolver.resolve_context() == "other"


def test_rung2_absent_record_falls_through_to_rung3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A harness id whose session record was never written (never bound) falls through,
    it never raises."""
    ws = _mk_ws(tmp_path, slug="proj")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "claude-never-bound")
    monkeypatch.chdir(ws / "repos" / "proj")

    assert specs_resolver.resolve_context() == "proj"


def test_rung2_deleted_context_guard_falls_through_to_rung3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """context-delete-leaves-stale-session-bind law: a LIVE record pointing at a context
    that no longer exists in the registry never resolves — the ladder falls through
    rather than returning a stale pointer."""
    ws = _mk_ws(tmp_path, slug="other")
    _write_harness_record(ws, _HARNESS_ID, "deleted-ctx", age_seconds=0)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", _HARNESS_ID)
    monkeypatch.chdir(ws / "repos" / "other")

    assert specs_resolver.resolve_context() == "other"


def test_rung2_eval_flow_dadaia_session_id_is_not_consulted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The FR1 contract names ``core.session_env.harness_session_id`` only — the legacy
    ``DADAIA_SESSION_ID`` eval-flow channel (rung A/B's own ladder) is a DIFFERENT,
    untouched mechanism and must not be consulted by the new authority."""
    ws = _mk_ws(tmp_path, slug="other")
    (ws / ".dadaia" / "sessions" / "sess-eval01.json").write_text(
        json.dumps({"session_id": "sess-eval01", "context": "other"}), encoding="utf-8"
    )
    monkeypatch.setenv("DADAIA_SESSION_ID", "sess-eval01")
    monkeypatch.chdir(ws / "repos" / "other")

    # No harness-native id set at all -> rung 2 yields nothing -> falls to rung 3, which
    # happens to agree with the eval-flow record here ONLY because cwd sits in "other" too.
    assert specs_resolver.resolve_context() == "other"


# --- rung 3: the repo containing the current working directory -----------------------


def test_rung3_cwd_repo_resolves_with_no_env_at_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _mk_ws(tmp_path, slug="proj")
    monkeypatch.chdir(ws / "repos" / "proj" / "specs")

    assert specs_resolver.resolve_context() == "proj"


def test_rung3_maps_slug_to_context_name_via_registry_inverse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _mk_ws(tmp_path, slug="beta-repo", name="alpha-context")
    monkeypatch.chdir(ws / "repos" / "beta-repo" / "specs")

    assert specs_resolver.resolve_context() == "alpha-context"


def test_rung3_cwd_outside_any_repo_resolves_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _mk_ws(tmp_path, slug="proj")
    monkeypatch.chdir(ws)

    assert specs_resolver.resolve_context() is None


def test_nothing_resolves_returns_none_no_workspace_no_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plain = tmp_path / "not-a-workspace"
    plain.mkdir()
    monkeypatch.chdir(plain)

    assert specs_resolver.resolve_context() is None


# --- context_name_for_repo_slug: the registry inverse of repo_slug_for_context --------


def test_context_name_for_repo_slug_resolves_matching_entry(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path, slug="beta-repo", name="alpha-context")

    assert specs_resolver.context_name_for_repo_slug(ws, "beta-repo") == "alpha-context"


def test_context_name_for_repo_slug_falls_back_to_slug_when_unmatched(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path, slug="proj")

    assert specs_resolver.context_name_for_repo_slug(ws, "no-such-slug") == "no-such-slug"


def test_context_name_for_repo_slug_falls_back_to_slug_when_registry_missing(
    tmp_path: Path,
) -> None:
    assert specs_resolver.context_name_for_repo_slug(tmp_path, "proj") == "proj"


def test_context_name_for_repo_slug_falls_back_to_slug_when_registry_corrupt(
    tmp_path: Path,
) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text("{not json", encoding="utf-8")

    assert specs_resolver.context_name_for_repo_slug(tmp_path, "proj") == "proj"


def test_context_name_for_repo_slug_accepts_legacy_repo_field(tmp_path: Path) -> None:
    """Mirrors ``repo_slug_for_context``'s own ``repo_slug`` OR ``repo`` fallback."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {"schema_version": "2", "contexts": [{"name": "alpha-context", "repo": "beta-repo"}]}
        ),
        encoding="utf-8",
    )

    assert specs_resolver.context_name_for_repo_slug(tmp_path, "beta-repo") == "alpha-context"


# --- ambient-isolation regression --------------------------------------------------
#
# Bug specs-resolver-context-tests-flaky-under-xdist-full-suite: a context/session
# resolution unit test whose isolation fixture scrubs only the harness session-id vars
# is not, in fact, isolated. ``_authority_workspace_root()`` honours ``WORKSPACE_ROOT``
# UNCONDITIONALLY (hook-transport channel, by design) -- ahead of, and regardless of,
# any ``monkeypatch.chdir()`` a test performs. Reproduced deterministically (no xdist,
# no timing) by planting exactly the ambient condition the bug names: a real-looking
# "concurrent session" workspace with its own live session record, standing in for
# whatever a parallel ``dadaia context bind``/``context show`` invocation (or a
# WORKSPACE_ROOT inherited from the shell that launched pytest) leaves on disk /  in
# the environment while this suite runs -- then proving ``scrub_context_resolution_env``
# (the fixture helper the fix wires into every context/session-resolution test file)
# neutralizes it.


def test_scrub_context_resolution_env_neutralizes_ambient_workspace_root_and_session_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Intent: CONTRACT -- bug specs-resolver-context-tests-flaky-under-xdist-full-suite.

    Direct reproduction (empirically confirmed before this fix landed): with
    ``WORKSPACE_ROOT`` pointing at an unrelated, fully-live "ambient" workspace, a plain
    rung-3 (cwd-only) scenario mis-resolves -- ``resolve_context()`` returns ``None``
    instead of the test's own synthetic workspace's context, because the ambient
    ``WORKSPACE_ROOT`` wins over ``Path.cwd()`` and the synthetic workspace's repo is
    not reachable under it. ``scrub_context_resolution_env`` is the fix: call it after
    planting the leak and rung 3 resolves correctly again.
    """
    # The "ambient" state: a real-looking workspace + a LIVE session record for a
    # harness id, standing in for whatever a concurrent session/hook process left on
    # disk (and in the environment) while this suite was running.
    ambient_ws = _mk_ws(tmp_path / "ambient-concurrent-session", slug="ambient-ctx")
    _write_harness_record(ambient_ws, _HARNESS_ID, "ambient-ctx", age_seconds=0)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ambient_ws))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", _HARNESS_ID)
    monkeypatch.setenv("DADAIA_CONTEXT", "ambient-ctx")

    scrub_context_resolution_env(monkeypatch)

    ws = _mk_ws(tmp_path / "isolated", slug="proj")
    monkeypatch.chdir(ws / "repos" / "proj")

    assert specs_resolver.resolve_context() == "proj"
