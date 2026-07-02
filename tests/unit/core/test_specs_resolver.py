"""W1-8 (T-47-17): persisted-bind fallback in ``core.specs_resolver``.

A workspace shell that ran ``dadaia context bind <ctx>`` exports no env, but the bind wrote
``.dadaia/states/bind_epoch/<ctx>`` recording the invoking harness pid (W1-7). The resolver
runs inside a ``dadaia`` CLI child of that SAME shell, so ``os.getppid()`` equals the
recorded pid and the bound context resolves with no ``--specs-dir`` / no env.

These tests exercise the resolver in-process, so ``os.getppid()`` at stamp time and at
resolve time are the SAME real value — the exact same-shell attribution production relies
on. Foreign-pid, legacy-empty, ambiguous, and no-marker cases all fall through to the
unchanged cwd/error path.
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


# --- _persisted_bind_context: attribution semantics ---------------------------


def test_persisted_bind_context_resolves_single_attributed_marker(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path)
    _stamp(ws, "ctx", pid=os.getppid())  # attributed to this session's harness ancestry
    assert specs_resolver._persisted_bind_context(ws) == "ctx"


def test_persisted_bind_context_none_when_no_markers(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path)
    assert specs_resolver._persisted_bind_context(ws) is None


def test_persisted_bind_context_ignores_legacy_empty_marker(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path)
    _stamp(ws, "ctx", pid=None)  # legacy/empty ⇒ unattributable
    assert specs_resolver._persisted_bind_context(ws) is None


def test_persisted_bind_context_ignores_foreign_pid_marker(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path)
    _stamp(ws, "ctx", pid=os.getppid() + 999)  # a different session's bind
    assert specs_resolver._persisted_bind_context(ws) is None


def test_persisted_bind_context_none_when_ambiguous(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path)
    (ws / "repos" / "other" / "specs").mkdir(parents=True)
    _stamp(ws, "ctx", pid=os.getppid())
    _stamp(ws, "other", pid=os.getppid())  # two attributable markers ⇒ ambiguous
    assert specs_resolver._persisted_bind_context(ws) is None


def test_persisted_bind_context_ignores_non_integer_content(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path)
    (ws / ".dadaia" / "states" / "bind_epoch" / "ctx").write_text("garbage", encoding="utf-8")
    assert specs_resolver._persisted_bind_context(ws) is None


def test_persisted_bind_context_none_when_dir_absent(tmp_path: Path) -> None:
    # A workspace with no bind_epoch dir at all must not raise.
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text('{"contexts": []}', encoding="utf-8")
    assert specs_resolver._persisted_bind_context(tmp_path) is None


# --- W1-8 (v0.1.47): ancestry-chain MEMBERSHIP attribution --------------------


def test_persisted_bind_context_resolves_via_ancestry_membership(tmp_path: Path) -> None:
    """(b) A supplied ancestry set sharing ONE pid with the marker chain ⇒ resolves."""
    ws = _mk_ws(tmp_path)
    # Marker chain [dead shell, harness, grandparent]; the resolver's ancestry chain shares
    # only the harness pid (222) — different ephemeral shells, same long-lived harness.
    _stamp(ws, "ctx", chain=[111, 222, 333])
    resolved = specs_resolver._persisted_bind_context(ws, frozenset({999, 222, 444}))
    assert resolved == "ctx"


def test_persisted_bind_context_none_when_ancestry_disjoint(tmp_path: Path) -> None:
    """(b) A supplied ancestry set disjoint from the marker chain ⇒ unattributable."""
    ws = _mk_ws(tmp_path)
    _stamp(ws, "ctx", chain=[111, 222, 333])
    assert specs_resolver._persisted_bind_context(ws, frozenset({444, 555})) is None


def test_persisted_bind_context_legacy_single_line_degraded_equal(tmp_path: Path) -> None:
    """(c) ancestry_pids=None ⇒ degraded single-getppid equality on a legacy single-line marker."""
    ws = _mk_ws(tmp_path)
    _stamp(ws, "ctx", pid=os.getppid())  # legacy one-line marker
    # No ancestry set supplied ⇒ effective = {os.getppid()} ⇒ equality holds.
    assert specs_resolver._persisted_bind_context(ws, None) == "ctx"
    # An explicit ancestry set carrying getppid also resolves the legacy marker.
    assert specs_resolver._persisted_bind_context(ws, frozenset({os.getppid()})) == "ctx"


def test_persisted_bind_context_empty_marker_never_attributable_with_ancestry(
    tmp_path: Path,
) -> None:
    """(d) An empty marker is unattributable regardless of the ancestry set supplied."""
    ws = _mk_ws(tmp_path)
    _stamp(ws, "ctx", pid=None)  # empty marker
    assert specs_resolver._persisted_bind_context(ws, frozenset({os.getppid(), 1234})) is None


def test_resolve_specs_dir_ancestry_membership_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: ancestry_pids sharing a pid with the marker chain resolves the specs dir."""
    ws = _mk_ws(tmp_path, slug="proj")
    _stamp(ws, "proj", chain=[111, 424242, 333])  # 424242 == the shared harness pid
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    resolved = specs_resolver.resolve_specs_dir(None, ancestry_pids=frozenset({999, 424242}))
    assert resolved == (ws / "repos" / "proj" / "specs").resolve()


def test_resolve_specs_dir_ancestry_disjoint_falls_through_to_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disjoint ancestry_pids ⇒ unattributable ⇒ the unchanged cwd/error path (no ./specs)."""
    ws = _mk_ws(tmp_path, slug="proj")
    _stamp(ws, "proj", chain=[111, 222, 333])
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    with pytest.raises(typer.BadParameter):
        specs_resolver.resolve_specs_dir(None, ancestry_pids=frozenset({444, 555}))


# --- resolve_specs_dir: end-to-end persisted-bind resolution ------------------


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)


def test_resolve_specs_dir_uses_persisted_bind_from_workspace_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bound session, no env, cwd = workspace root ⇒ resolves the bound context's specs."""
    ws = _mk_ws(tmp_path, slug="proj")
    _stamp(ws, "proj", pid=os.getppid())
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    resolved = specs_resolver.resolve_specs_dir(None)
    assert resolved == (ws / "repos" / "proj" / "specs").resolve()


def test_resolve_specs_dir_unbound_falls_through_to_cwd_specs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No workspace in sight ⇒ a local ``./specs`` still wins (plain repo layout)."""
    repo = tmp_path / "plain-repo"  # NOT a workspace root — no .dadaia/states
    local_specs = repo / "specs"
    local_specs.mkdir(parents=True)
    _clean_env(monkeypatch)
    monkeypatch.chdir(repo)
    resolved = specs_resolver.resolve_specs_dir(None)
    assert resolved == local_specs.resolve()


def test_resolve_specs_dir_refuses_workspace_root_specs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.1.50 FR4: a specs/ AT the workspace root violates the root law ⇒ refuse.

    This exact shape was the disposed bug's landing zone
    (bugs-append-bound-session-falls-through-to-cwd-specs); the refusal message is
    actionable and redaction-safe (no absolute path echoed).
    """
    ws = _mk_ws(tmp_path, slug="proj")  # a real workspace root, no bind marker
    (ws / "specs").mkdir()
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    with pytest.raises(typer.BadParameter) as exc_info:
        specs_resolver.resolve_specs_dir(None)
    assert "Workspace Root" in str(exc_info.value)
    assert str(ws) not in str(exc_info.value)


def test_resolve_specs_dir_unbound_no_specs_raises_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No marker, no env, no ./specs ⇒ the current BadParameter error is unchanged."""
    ws = _mk_ws(tmp_path, slug="proj")  # repos/proj/specs exists but no bind marker, no ./specs
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    with pytest.raises(typer.BadParameter):
        specs_resolver.resolve_specs_dir(None)


def test_resolve_specs_dir_explicit_still_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit --specs-dir bypasses the persisted-bind fallback entirely."""
    ws = _mk_ws(tmp_path, slug="proj")
    _stamp(ws, "proj", pid=os.getppid())
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    explicit = ws / "elsewhere"
    explicit.mkdir()
    assert specs_resolver.resolve_specs_dir(str(explicit)) == explicit.resolve()
