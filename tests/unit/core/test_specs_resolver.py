"""``core.specs_resolver.resolve_specs_dir``: authority-only resolution.

T-50-05 (SPEC v0.5.0 FR1 deletion item 4): the old ``cwd/specs`` fallback and its
workspace-root refusal patch are deleted outright — ``DADAIA.md`` §3 never granted a
fourth rung for "any directory that happens to contain a specs/ folder", so that
shortcut was a workaround, not a rung. Resolution now goes through
:func:`~dadaia_workspace.core.specs_resolver.resolve_context` only (see
``tests/unit/core/test_specs_resolver_resolve_context.py`` for that law's own tests);
anywhere it cannot resolve a context reaches the one terminal, actionable error.
"""

from __future__ import annotations

import json
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
    (tmp_path / "repos" / slug / "specs").mkdir(parents=True)
    return tmp_path


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)


def test_resolve_specs_dir_no_workspace_raises_not_cwd_specs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-50-05: a bare, non-workspace directory with its own ``./specs`` used to be a
    legitimate fallback (plain repo layout); that fallback is deleted — the law grants
    no rung for it, so this now raises the same terminal error as any other
    unresolvable case, even though ``./specs`` exists right there on disk."""
    _clean_env(monkeypatch)
    repo = tmp_path / "plain-repo"  # NOT a workspace root — no .dadaia/states
    local_specs = repo / "specs"
    local_specs.mkdir(parents=True)
    monkeypatch.chdir(repo)
    with pytest.raises(typer.BadParameter):
        specs_resolver.resolve_specs_dir(None)


def test_resolve_specs_dir_unbound_no_specs_raises_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No bind, no env, cwd outside every repos/<slug>/ ⇒ the actionable BadParameter
    error — unchanged by T-50-05, since this already resolved via the authority alone."""
    _clean_env(monkeypatch)
    ws = _mk_ws(tmp_path, slug="proj")
    monkeypatch.chdir(ws)  # cwd is the workspace ROOT, not repos/proj — rung 3 misses
    with pytest.raises(typer.BadParameter):
        specs_resolver.resolve_specs_dir(None)


def test_resolve_specs_dir_no_context_raises_generic_and_explicit_still_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-50-05: a ``specs/`` AT the workspace root with NO bound context no longer
    raises the old specific "Workspace Root Law" refusal (that patch is deleted with the
    fallback it was bolted onto) — it now raises the SAME generic, actionable,
    redaction-safe terminal error every unresolved case raises. An explicit
    --specs-dir still bypasses resolution entirely, unchanged."""
    ws = _mk_ws(tmp_path, slug="proj")  # a real workspace root, no bind
    (ws / "specs").mkdir()
    _clean_env(monkeypatch)
    monkeypatch.chdir(ws)
    with pytest.raises(typer.BadParameter) as exc_info:
        specs_resolver.resolve_specs_dir(None)
    assert "Workspace Root" not in str(exc_info.value)
    assert "Could not resolve specs_dir" in str(exc_info.value)
    assert str(ws) not in str(exc_info.value)

    ws2 = tmp_path.parent / (tmp_path.name + "-explicit")
    _mk_ws(ws2, slug="proj")
    monkeypatch.chdir(ws2)
    explicit = ws2 / "elsewhere"
    explicit.mkdir()
    assert specs_resolver.resolve_specs_dir(str(explicit)) == explicit.resolve()
