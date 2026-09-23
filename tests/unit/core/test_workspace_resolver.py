"""Unit tests for dadaia_workspace.core.workspace_resolver.

Covers:
  resolve_workspace_root —
    1. cwd inside a sub-repo that has .dadaia/ but no states/ → walks past, finds real root
    2. cwd at workspace root → returns workspace root immediately
    3. cwd outside any workspace tree → raises WorkspaceNotInitializedError
    4. cwd in a workspace whose .dadaia/states/ exists but spec_contexts.json is missing → raises
    5. No cwd arg → uses Path.cwd() default (monkeypatched)
    6. Returns absolute path (not relative)

  resolve_cli_workspace_root —
    9. explicit --workspace is authoritative and must hold .dadaia/ (bug
       import-export-workspace-flag-re-resolves-through-ancestor-walk)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import (
    resolve_cli_workspace_root,
    resolve_workspace_root,
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
# resolve_cli_workspace_root: an explicit --workspace is authoritative for EVERY verb
# (bugs: init-ignores-workspace-flag, import-export-workspace-flag-re-resolves-through-ancestor-walk)
# ---------------------------------------------------------------------------


def test_explicit_workspace_is_authoritative_and_must_be_initialized(tmp_path: Path) -> None:
    """Intent: CONTRACT — bug import-export-workspace-flag-re-resolves-through-ancestor-walk.

    Size: SMALL — filesystem only."""
    existing_ws = _make_full_workspace(tmp_path / "existing_ws")

    # An uninitialized directory nested inside a live workspace is REFUSED, never
    # silently re-resolved to the enclosing workspace.
    nested = existing_ws / ".dadaia" / "tmp" / "x"
    nested.mkdir(parents=True)
    with pytest.raises(WorkspaceNotInitializedError) as exc:
        resolve_cli_workspace_root(nested)
    assert str(nested) in str(exc.value)
    assert "brand_new" not in str(exc.value)

    # An initialized explicit target is used as given.
    other = _make_full_workspace(tmp_path / "other_ws")
    assert resolve_cli_workspace_root(other) == other.resolve()

    # A partial .dadaia/ (sub-repo shape) counts as explicit-target-initialized:
    # the flag names the root, no walk is performed.
    sub_repo = _make_partial_dadaia(existing_ws / "repos", "my-service")
    assert resolve_cli_workspace_root(sub_repo) == sub_repo.resolve()

    # None keeps the cwd ancestor walk.
    deep = sub_repo / "src"
    deep.mkdir(parents=True)
    assert resolve_cli_workspace_root(None, deep) == existing_ws
