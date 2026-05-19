"""Unit tests for dadaia_workspace.core.workspace_resolver.resolve_workspace_root.

TDD — these tests are written BEFORE the implementation and must fail first.

Scenarios covered:
1. cwd inside a sub-repo that has .dadaia/ but no states/ → walks past, finds real root
2. cwd at workspace root → returns workspace root immediately
3. cwd outside any workspace tree → raises WorkspaceNotInitializedError
4. cwd in a workspace whose .dadaia/states/ exists but spec_contexts.json is missing → raises
5. No cwd arg → uses Path.cwd() default (monkeypatched)
6. Returns absolute path (not relative)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

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
# Test 1 — sub-repo with .dadaia/ but no states/ is skipped; real root is found
# ---------------------------------------------------------------------------


def test_walks_past_partial_dadaia_to_real_workspace(tmp_path: Path) -> None:
    """cwd inside a sub-repo that has .dadaia/ but no states/ must be skipped.

    The resolver should climb up and find the real workspace root that has
    .dadaia/states/spec_contexts.json.
    """
    # Workspace root (proper)
    workspace_root = _make_full_workspace(tmp_path / "workspace")

    # Sub-repo: has .dadaia/ but no states/
    sub_repo = _make_partial_dadaia(workspace_root / "repos", "redacted-slug")
    # A file deep inside the sub-repo
    deep = sub_repo / "src" / "module"
    deep.mkdir(parents=True)

    result = resolve_workspace_root(deep)

    assert result == workspace_root


# ---------------------------------------------------------------------------
# Test 2 — cwd at workspace root itself
# ---------------------------------------------------------------------------


def test_returns_workspace_root_when_cwd_is_root(tmp_path: Path) -> None:
    """When cwd IS the workspace root, return it immediately."""
    workspace_root = _make_full_workspace(tmp_path / "workspace")

    result = resolve_workspace_root(workspace_root)

    assert result == workspace_root


# ---------------------------------------------------------------------------
# Test 3 — cwd outside any workspace tree raises WorkspaceNotInitializedError
# ---------------------------------------------------------------------------


def test_raises_when_no_workspace_found(tmp_path: Path) -> None:
    """A path with no .dadaia/states/spec_contexts.json anywhere raises the error."""
    orphan_dir = tmp_path / "nowhere" / "deep" / "path"
    orphan_dir.mkdir(parents=True)

    with pytest.raises(WorkspaceNotInitializedError) as exc_info:
        resolve_workspace_root(orphan_dir)

    # Error message must mention the cwd that was inspected
    assert str(orphan_dir) in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 4 — .dadaia/states/ exists but spec_contexts.json is absent → raises
# ---------------------------------------------------------------------------


def test_raises_when_spec_contexts_json_missing(tmp_path: Path) -> None:
    """Having .dadaia/states/ but no spec_contexts.json inside is NOT a valid workspace."""
    workspace_candidate = tmp_path / "partial"
    states_dir = workspace_candidate / ".dadaia" / "states"
    states_dir.mkdir(parents=True)
    # Deliberately do NOT create spec_contexts.json

    with pytest.raises(WorkspaceNotInitializedError):
        resolve_workspace_root(workspace_candidate)


# ---------------------------------------------------------------------------
# Test 5 — no cwd arg → uses Path.cwd() default (monkeypatching os.getcwd)
# ---------------------------------------------------------------------------


def test_uses_cwd_when_no_arg_given(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When called with no argument, resolver should default to Path.cwd()."""
    workspace_root = _make_full_workspace(tmp_path / "workspace")

    # Monkeypatch os.getcwd to simulate running from within the workspace root
    monkeypatch.chdir(workspace_root)

    result = resolve_workspace_root()

    assert result == workspace_root


# ---------------------------------------------------------------------------
# Test 6 — result is always absolute
# ---------------------------------------------------------------------------


def test_returns_absolute_path(tmp_path: Path) -> None:
    """The returned path must be absolute regardless of how cwd is expressed."""
    workspace_root = _make_full_workspace(tmp_path / "workspace")

    result = resolve_workspace_root(workspace_root)

    assert result.is_absolute()


# ---------------------------------------------------------------------------
# Test 7 (bonus) — backward-compat: workspace already resolved correctly stays same
# ---------------------------------------------------------------------------


def test_backward_compat_correctly_resolved_workspace(tmp_path: Path) -> None:
    """A workspace that was correctly resolved by the old logic returns the same path.

    The old logic returned the first directory containing .dadaia/.
    Our new logic requires .dadaia/states/spec_contexts.json.
    For a properly initialized workspace, both point to the same root.
    """
    workspace_root = _make_full_workspace(tmp_path / "myworkspace")
    # cwd is a nested dir inside the workspace
    nested = workspace_root / "tools" / "scripts"
    nested.mkdir(parents=True)

    result = resolve_workspace_root(nested)

    assert result == workspace_root


# ---------------------------------------------------------------------------
# Test 8 — error message includes skipped candidates
# ---------------------------------------------------------------------------


def test_error_message_mentions_skipped_candidates(tmp_path: Path) -> None:
    """When sub-repos with partial .dadaia/ are skipped, they appear in error message."""
    # Build a tree: orphan_root/repos/sub-repo/.dadaia (no states)
    # orphan_root itself has no .dadaia at all
    orphan_root = tmp_path / "orphan"
    sub_repo = _make_partial_dadaia(orphan_root / "repos", "some-subrepo")
    deep = sub_repo / "src"
    deep.mkdir(parents=True)

    with pytest.raises(WorkspaceNotInitializedError) as exc_info:
        resolve_workspace_root(deep)

    msg = str(exc_info.value)
    # The skipped candidate (sub_repo) should be mentioned
    assert str(sub_repo) in msg
