"""Unit tests for dadaia_workspace.core.workspace_resolver.

Covers:
  resolve_workspace_root —
    1. cwd inside a sub-repo that has .dadaia/ but no states/ → walks past, finds real root
    2. cwd at workspace root → returns workspace root immediately
    3. cwd outside any workspace tree → raises WorkspaceNotInitializedError
    4. cwd in a workspace whose .dadaia/states/ exists but spec_contexts.json is missing → raises
    5. No cwd arg → uses Path.cwd() default (monkeypatched)
    6. Returns absolute path (not relative)

  resolve_workspace_root_for_init (T-25) —
    7. sentinel present → returns sentinel's parent dir
    8. sentinel absent → returns cwd (no exception raised)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import (
    resolve_workspace_root,
    resolve_workspace_root_for_init,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_full_workspace(tmp_path: Path) -> Path:
    """Create a proper initialized workspace: .dadaia/states/spec_contexts.json."""
    states_dir = tmp_path / ".dadaia" / "states"
    states_dir.mkdir(parents=True)
    (states_dir / "spec_contexts.json").write_text("{}")
    return tmp_path


def _make_partial_dadaia(parent: Path, name: str) -> Path:
    """Create a sub-repo directory with .dadaia/ but no states/ (partial workspace)."""
    sub = parent / name
    sub.mkdir(parents=True)
    (sub / ".dadaia").mkdir()
    return sub


# ---------------------------------------------------------------------------
# resolve_workspace_root — SUCCESS paths.
# ---------------------------------------------------------------------------


def test_resolve_workspace_root_success_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # (1) cwd inside a sub-repo that has .dadaia/ but no states/ must be skipped; the
    # resolver climbs up and finds the real workspace root.
    workspace_root = _make_full_workspace(tmp_path / "workspace")
    sub_repo = _make_partial_dadaia(workspace_root / "repos", "sample-consumer")
    deep = sub_repo / "src" / "module"
    deep.mkdir(parents=True)
    assert resolve_workspace_root(deep) == workspace_root

    # (2) cwd IS the workspace root → return it immediately.
    assert resolve_workspace_root(workspace_root) == workspace_root

    # (5) No cwd arg → defaults to Path.cwd().
    monkeypatch.chdir(workspace_root)
    assert resolve_workspace_root() == workspace_root

    # (6) The returned path is always absolute.
    assert resolve_workspace_root(workspace_root).is_absolute()

    # Backward-compat: a properly initialized workspace resolves the same from a
    # nested dir the old .dadaia/-presence logic would also have found.
    nested = workspace_root / "tools" / "scripts"
    nested.mkdir(parents=True)
    assert resolve_workspace_root(nested) == workspace_root


# ---------------------------------------------------------------------------
# resolve_workspace_root — FAILURE paths.
# ---------------------------------------------------------------------------


def test_resolve_workspace_root_failure_table(tmp_path: Path) -> None:
    # (3) A path with no .dadaia/states/spec_contexts.json anywhere raises, and the
    # message mentions the inspected cwd.
    orphan_dir = tmp_path / "nowhere" / "deep" / "path"
    orphan_dir.mkdir(parents=True)
    with pytest.raises(WorkspaceNotInitializedError) as exc_info:
        resolve_workspace_root(orphan_dir)
    assert str(orphan_dir) in str(exc_info.value)

    # (4) Having .dadaia/states/ but no spec_contexts.json inside is NOT a valid
    # workspace.
    workspace_candidate = tmp_path / "partial"
    states_dir = workspace_candidate / ".dadaia" / "states"
    states_dir.mkdir(parents=True)
    with pytest.raises(WorkspaceNotInitializedError):
        resolve_workspace_root(workspace_candidate)

    # The error message lists skipped partial-.dadaia candidates.
    orphan_root = tmp_path / "orphan"
    sub_repo = _make_partial_dadaia(orphan_root / "repos", "some-subrepo")
    deep = sub_repo / "src"
    deep.mkdir(parents=True)
    with pytest.raises(WorkspaceNotInitializedError) as exc_info2:
        resolve_workspace_root(deep)
    assert str(sub_repo) in str(exc_info2.value)


# ---------------------------------------------------------------------------
# resolve_workspace_root_for_init (T-25) — sentinel present/absent.
# ---------------------------------------------------------------------------


def test_resolve_workspace_root_for_init_sentinel_and_fallback(tmp_path: Path) -> None:
    # T-25a: when .dadaia/states/spec_contexts.json is present, return its parent dir.
    workspace_root = _make_full_workspace(tmp_path / "workspace")
    nested = workspace_root / "repos" / "sub"
    nested.mkdir(parents=True)
    assert resolve_workspace_root_for_init(nested) == workspace_root

    # T-25b: when no sentinel is found, return the given cwd path without raising —
    # the safe fallback for first-time init.
    orphan = tmp_path / "no-workspace" / "somewhere"
    orphan.mkdir(parents=True)
    assert resolve_workspace_root_for_init(orphan) == orphan


# ---------------------------------------------------------------------------
# T-016-Z01: explicit --workspace flag is authoritative (bug: init-ignores-workspace-flag)
# ---------------------------------------------------------------------------


def test_explicit_workspace_is_authoritative(tmp_path: Path) -> None:
    """T-016-Z01: init --workspace <dir> from inside an existing workspace must target <dir>.

    Bug: resolve_workspace_root_for_init used to walk UP to the ancestor
    workspace when cwd was inside one, ignoring the explicit --workspace path.
    Fix: an explicit path is returned directly — no ancestor-walk, regardless of
    whether the target dir exists yet (init is allowed to initialize a directory
    that doesn't exist yet).
    """
    # Set up an existing workspace at tmp_path/existing_ws.
    existing_ws = _make_full_workspace(tmp_path / "existing_ws")
    # Simulate CWD inside the existing workspace (e.g. its .dadaia/tmp subdirectory).
    cwd_inside_ws = existing_ws / ".dadaia" / "tmp" / "agent-session"
    cwd_inside_ws.mkdir(parents=True)

    # The explicit --workspace target (a fresh, uninitialized dir).
    fresh_target = tmp_path / "freshws"
    fresh_target.mkdir(parents=True)
    result = resolve_workspace_root_for_init(fresh_target, explicit=True)
    assert result == fresh_target.resolve()
    # Sanity: the ancestor workspace is NOT what we got back.
    assert result != existing_ws

    # A target path that does not yet exist is returned as-is.
    nonexistent = tmp_path / "brand_new_workspace"
    assert resolve_workspace_root_for_init(nonexistent, explicit=True) == nonexistent.resolve()

    # Backward compat: without explicit=True, ancestor-walk is preserved — a nested
    # sub-repo with partial .dadaia (no sentinel) still walks up to find the proper
    # workspace.
    sub_repo = _make_partial_dadaia(existing_ws / "repos", "my-service")
    deep = sub_repo / "src"
    deep.mkdir(parents=True)
    assert resolve_workspace_root_for_init(deep, explicit=False) == existing_ws
