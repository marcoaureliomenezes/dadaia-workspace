"""W1-8 (T-47-17): persisted-bind fallback in ``core.specs_resolver``.

A workspace shell that ran ``dadaia context bind <ctx>`` exports no env, but the bind wrote
``.dadaia/states/bind_epoch/<ctx>`` recording the invoking harness pid (W1-7). The resolver
runs inside a ``dadaia`` CLI child of that SAME shell, so ``os.getppid()`` equals the
recorded pid and the bound context resolves with no ``--specs-dir`` / no env.

These tests exercise the resolver in-process, so ``os.getppid()`` at stamp time and at
resolve time are the SAME real value — the exact same-shell attribution production relies
on. Foreign-pid, legacy-empty, ambiguous, and no-marker cases all fall through to the
unchanged cwd/error path.

CRIT-adjacent (session/bind attribution). Ambiguous-two-markers and foreign-pid rows must
survive — they prevent cross-session context attribution. The refusal-message redaction
assert (no absolute path echoed) is kept standalone.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import typer

from dadaia_workspace.core import specs_resolver


def _mk_ws(tmp_path: Path, *, slug: str = "ctx") -> Path:
    """Build a minimal initialized workspace with a context repo tree (no venv)."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": [{"repo_slug": slug, "state": "alive"}]}),
        encoding="utf-8",
    )
    (states / "bind_epoch").mkdir()
    (tmp_path / "repos" / slug / "specs").mkdir(parents=True)
    return tmp_path


def _stamp(
    tmp_path: Path, slug: str, *, pid: int | None = None, chain: list[int] | None = None
) -> None:
    """Write a bind-epoch marker for ``slug``.

    ``chain`` writes a nearest-first multi-line ancestry chain [shell, harness, …]; ``pid``
    writes a single-line (legacy) marker; both ``None`` writes a legacy EMPTY marker.
    """
    marker = tmp_path / ".dadaia" / "states" / "bind_epoch" / slug
    if chain is not None:
        marker.write_text("".join(f"{p}\n" for p in chain), encoding="utf-8")
    else:
        marker.write_text("" if pid is None else f"{pid}\n", encoding="utf-8")


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)


# --- _persisted_bind_context: RESOLVES cases -----------------------------------


@pytest.mark.parametrize(
    ("name", "setup_fn", "ancestry"),
    [
        (
            "single_attributed_marker",
            lambda ws: _stamp(ws, "ctx", pid=os.getppid()),
            "unset",  # call with no ancestry_pids arg at all
        ),
        (
            # (c) ancestry_pids=None ⇒ degraded single-getppid equality on a legacy
            # single-line marker.
            "legacy_single_line_degraded_equal_none",
            lambda ws: _stamp(ws, "ctx", pid=os.getppid()),
            None,
        ),
        (
            "legacy_single_line_degraded_equal_explicit",
            lambda ws: _stamp(ws, "ctx", pid=os.getppid()),
            "self",  # frozenset({os.getppid()})
        ),
        (
            # (b) A supplied ancestry set sharing ONE pid with the marker chain ⇒
            # resolves.
            "ancestry_membership",
            lambda ws: _stamp(ws, "ctx", chain=[111, 222, 333]),
            frozenset({999, 222, 444}),
        ),
    ],
)
def test_persisted_bind_context_resolves_table(
    tmp_path: Path, name: str, setup_fn: object, ancestry: object
) -> None:
    ws = _mk_ws(tmp_path)
    setup_fn(ws)  # type: ignore[operator]
    if ancestry == "unset":
        assert specs_resolver._persisted_bind_context(ws) == "ctx"
    elif ancestry == "self":
        assert specs_resolver._persisted_bind_context(ws, frozenset({os.getppid()})) == "ctx"
    else:
        assert specs_resolver._persisted_bind_context(ws, ancestry) == "ctx"  # type: ignore[arg-type]


# --- _persisted_bind_context: NONE (unattributable) cases -----------------------


def _setup_ambiguous_two_markers(ws: Path) -> None:
    (ws / "repos" / "other" / "specs").mkdir(parents=True)
    _stamp(ws, "ctx", pid=os.getppid())
    _stamp(ws, "other", pid=os.getppid())


@pytest.mark.parametrize(
    ("name", "setup_fn", "ancestry"),
    [
        ("dir_absent", lambda ws: None, "unset"),
        ("no_markers", lambda ws: None, "unset"),
        (
            "legacy_empty_marker",
            lambda ws: _stamp(ws, "ctx", pid=None),
            "unset",
        ),
        (
            "foreign_pid_marker",
            lambda ws: _stamp(ws, "ctx", pid=os.getppid() + 999),
            "unset",
        ),
        (
            # Two attributable markers ⇒ ambiguous — CRIT: prevents cross-session
            # attribution.
            "ambiguous_two_markers",
            _setup_ambiguous_two_markers,
            "unset",
        ),
        (
            "non_integer_content",
            lambda ws: (ws / ".dadaia" / "states" / "bind_epoch" / "ctx").write_text(
                "garbage", encoding="utf-8"
            ),
            "unset",
        ),
        (
            # (b) A supplied ancestry set disjoint from the marker chain ⇒
            # unattributable.
            "ancestry_disjoint",
            lambda ws: _stamp(ws, "ctx", chain=[111, 222, 333]),
            frozenset({444, 555}),
        ),
        (
            # (d) An empty marker is unattributable regardless of the ancestry set
            # supplied.
            "empty_marker_with_ancestry",
            lambda ws: _stamp(ws, "ctx", pid=None),
            frozenset({0, 1234}),  # os.getppid() substituted below
        ),
    ],
)
def test_persisted_bind_context_none_table(
    tmp_path: Path, name: str, setup_fn: object, ancestry: object
) -> None:
    ws = _mk_ws(tmp_path)
    if name == "dir_absent":
        # A workspace with no bind_epoch dir at all must not raise.
        states = ws / ".dadaia" / "states"
        states.mkdir(parents=True, exist_ok=True)
        (states / "spec_contexts.json").write_text('{"contexts": []}', encoding="utf-8")
        assert specs_resolver._persisted_bind_context(ws) is None
        return
    setup_fn(ws)  # type: ignore[operator]
    if name == "empty_marker_with_ancestry":
        ancestry = frozenset({os.getppid(), 1234})
    if ancestry == "unset":
        assert specs_resolver._persisted_bind_context(ws) is None
    else:
        assert specs_resolver._persisted_bind_context(ws, ancestry) is None  # type: ignore[arg-type]


def test_two_markers_disjoint_chains_never_cross_attribute(tmp_path: Path) -> None:
    """(ii) Two bind-epoch markers with disjoint chains; the ancestry matches EXACTLY one
    ⇒ that one resolves and the other is never cross-attributed (concurrent-session
    safety, CRIT no-cross-steal)."""
    ws = _mk_ws(tmp_path, slug="ctxa")
    (ws / "repos" / "ctxb" / "specs").mkdir(parents=True)
    _stamp(ws, "ctxa", chain=[90001, 90002])
    _stamp(ws, "ctxb", chain=[91001, 91002])
    # Ancestry shares a pid with ctxa's chain ONLY.
    assert specs_resolver._persisted_bind_context(ws, frozenset({12345, 90002})) == "ctxa"
    # Ancestry disjoint from both ⇒ neither is attributed (no blind fallback).
    assert specs_resolver._persisted_bind_context(ws, frozenset({999, 998})) is None


# --- resolve_specs_dir: end-to-end persisted-bind resolution ------------------


@pytest.mark.parametrize(
    ("name", "chain_or_pid_fn", "resolve_ancestry"),
    [
        (
            "persisted_bind_from_workspace_root",
            lambda ws: _stamp(ws, "proj", pid=os.getppid()),
            None,
        ),
        (
            # End-to-end: ancestry_pids sharing a pid with the marker chain resolves
            # the specs dir.
            "ancestry_membership_resolves",
            lambda ws: _stamp(ws, "proj", chain=[111, 424242, 333]),
            frozenset({999, 424242}),
        ),
    ],
)
def test_resolve_specs_dir_bind_resolves_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    chain_or_pid_fn: object,
    resolve_ancestry: object,
) -> None:
    ws = _mk_ws(tmp_path, slug="proj")
    chain_or_pid_fn(ws)  # type: ignore[operator]
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    kwargs = {"ancestry_pids": resolve_ancestry} if resolve_ancestry is not None else {}
    resolved = specs_resolver.resolve_specs_dir(None, **kwargs)  # type: ignore[arg-type]
    assert resolved == (ws / "repos" / "proj" / "specs").resolve()


@pytest.mark.parametrize(
    ("name", "setup_fn", "resolve_ancestry"),
    [
        (
            # No workspace in sight ⇒ a local ./specs still wins (plain repo layout).
            "unbound_falls_through_to_cwd_specs",
            lambda tp: None,  # handled specially below (uses a non-workspace dir)
            None,
        ),
        (
            # No marker, no env, no ./specs ⇒ the current BadParameter error is
            # unchanged.
            "unbound_no_specs_raises_unchanged",
            lambda ws: None,
            None,
        ),
        (
            # Disjoint ancestry_pids ⇒ unattributable ⇒ the unchanged cwd/error path
            # (no ./specs).
            "ancestry_disjoint_falls_through_to_error",
            lambda ws: _stamp(ws, "proj", chain=[111, 222, 333]),
            frozenset({444, 555}),
        ),
    ],
)
def test_resolve_specs_dir_no_bind_table(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    setup_fn: object,
    resolve_ancestry: object,
) -> None:
    _clean_env(monkeypatch)
    if name == "unbound_falls_through_to_cwd_specs":
        repo = tmp_path / "plain-repo"  # NOT a workspace root — no .dadaia/states
        local_specs = repo / "specs"
        local_specs.mkdir(parents=True)
        monkeypatch.chdir(repo)
        resolved = specs_resolver.resolve_specs_dir(None)
        assert resolved == local_specs.resolve()
        return

    ws = _mk_ws(tmp_path, slug="proj")
    setup_fn(ws)  # type: ignore[operator]
    monkeypatch.chdir(ws)
    kwargs = {"ancestry_pids": resolve_ancestry} if resolve_ancestry is not None else {}
    with pytest.raises(typer.BadParameter):
        specs_resolver.resolve_specs_dir(None, **kwargs)  # type: ignore[arg-type]


def test_resolve_specs_dir_refuses_workspace_root_specs_and_explicit_still_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.1.50 FR4: a specs/ AT the workspace root violates the root law ⇒ refuse.

    This exact shape was the disposed bug's landing zone
    (bugs-append-bound-session-falls-through-to-cwd-specs); the refusal message is
    actionable and redaction-safe (no absolute path echoed). An explicit
    --specs-dir bypasses the persisted-bind fallback entirely.
    """
    ws = _mk_ws(tmp_path, slug="proj")  # a real workspace root, no bind marker
    (ws / "specs").mkdir()
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    with pytest.raises(typer.BadParameter) as exc_info:
        specs_resolver.resolve_specs_dir(None)
    assert "Workspace Root" in str(exc_info.value)
    assert str(ws) not in str(exc_info.value)

    ws2 = _mk_ws(tmp_path.parent / (tmp_path.name + "-explicit"), slug="proj")
    _stamp(ws2, "proj", pid=os.getppid())
    monkeypatch.chdir(ws2)
    explicit = ws2 / "elsewhere"
    explicit.mkdir()
    assert specs_resolver.resolve_specs_dir(str(explicit)) == explicit.resolve()


# --- bug ancestry-attribution-cross-session-ambiguity (kimi live repro) --------


def test_shared_host_ancestor_pids_do_not_shadow_the_own_session_marker(
    tmp_path: Path,
) -> None:
    """Live repro (kimi session, 2026-07-22): the OWN bind's marker chain contains the
    caller's harness pid (shallow, session-unique); a FOREIGN session's marker chain
    shares only deep host-level pids (tmux/sshd ancestors present in EVERY chain on the
    host). With an ORDERED caller chain, depth attribution resolves the own bind — the
    old any-membership set rule collapsed to ambiguity-None whenever >=2 live markers
    shared those deep pids."""
    ws = _mk_ws(tmp_path, slug="dadaia-workspace")
    (ws / "repos" / "dd-chain-capture" / "specs").mkdir(parents=True)
    _stamp(ws, "dadaia-workspace", chain=[2106163, 2084177, 2084140, 2064281, 2063868])
    _stamp(ws, "dd-chain-capture", chain=[2067019, 2066011, 2064281, 2063868])
    caller_chain = (2109665, 2084177, 2084140, 2064281, 2063868, 2063864)

    assert specs_resolver._persisted_bind_context(ws, caller_chain) == "dadaia-workspace"  # type: ignore[arg-type]


def test_ordered_depth_tie_stays_ambiguous(tmp_path: Path) -> None:
    """No cross-session steal: two markers whose best shared pid sits at the SAME caller
    depth (e.g. two binds from the SAME harness to different contexts) stay ambiguous —
    never a newest/mtime guess. Matches the pre-existing frozenset behavior."""
    ws = _mk_ws(tmp_path, slug="ctxa")
    (ws / "repos" / "ctxb" / "specs").mkdir(parents=True)
    _stamp(ws, "ctxa", chain=[111, 2084177, 333])
    _stamp(ws, "ctxb", chain=[222, 2084177, 444])
    caller_chain = (999, 2084177, 555)

    assert specs_resolver._persisted_bind_context(ws, caller_chain) is None  # type: ignore[arg-type]


def test_frozenset_degraded_mode_keeps_exactly_one_membership_rule(tmp_path: Path) -> None:
    """Degraded (unordered) input keeps today's semantics byte-identically: exactly one
    matching marker resolves; two matches are ambiguous."""
    ws = _mk_ws(tmp_path, slug="ctxa")
    (ws / "repos" / "ctxb" / "specs").mkdir(parents=True)
    _stamp(ws, "ctxa", chain=[111, 222])
    _stamp(ws, "ctxb", chain=[222, 333])
    assert specs_resolver._persisted_bind_context(ws, frozenset({222})) is None
    _stamp(ws, "ctxb", chain=[444, 555])
    assert specs_resolver._persisted_bind_context(ws, frozenset({222})) == "ctxa"
