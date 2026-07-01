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


def _stamp(tmp_path: Path, slug: str, *, pid: int | None) -> None:
    """Write a bind-epoch marker for ``slug``; ``pid=None`` writes a legacy EMPTY marker."""
    marker = tmp_path / ".dadaia" / "states" / "bind_epoch" / slug
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
    """No attributable marker ⇒ unchanged behavior: a local ``./specs`` still wins."""
    ws = _mk_ws(tmp_path, slug="proj")  # no bind-epoch marker stamped
    local_specs = ws / "specs"
    local_specs.mkdir()
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    resolved = specs_resolver.resolve_specs_dir(None)
    assert resolved == local_specs.resolve()


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
