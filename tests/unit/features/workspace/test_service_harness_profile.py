"""AC-4 (v0.1.58 FR2) — ``WorkspaceService.init`` persists the harness profile.

The init-time write lands ``.dadaia/states/harness_profile.json`` with the chosen L1
harness set (schema v1). The write is inline (like the ``_init_json_file`` state
bootstraps) but produces exactly the shape the ``infrastructure`` adapter reads back, so
this suite cross-checks the two writers via ``JsonHarnessProfileStore.read``. Re-running
``init`` with the same set is a no-op (no spurious rewrite, no second hook entry). An
absent profile file (a pre-v0.1.58 workspace) reads as ``None`` — the "treated as all-four"
back-compat convention every consumer honours.

These are unit-level assertions over the real service with fake asset/venv managers; the
harness-gated *scaffold* behaviour (which dirs/hooks appear) is pinned end-to-end by the
CLI suite ``tests/unit/cli/test_init_harness.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore
from tests.fakes import FakePublicAssetManager, FakePythonEnvironmentManager


@pytest.fixture()
def service() -> WorkspaceService:
    return WorkspaceService(
        public_assets=FakePublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    )


def _profile_path(root: Path) -> Path:
    return root / ".dadaia" / "states" / "harness_profile.json"


def test_persists_selected_set_roundtrips_and_defaults_to_all_four(
    service: WorkspaceService, tmp_path: Path
) -> None:
    # persists the selected harness set.
    service.init(tmp_path, skip_assets=True, harnesses=("codex",))
    data = json.loads(_profile_path(tmp_path).read_text(encoding="utf-8"))
    assert data == {"schema_version": "1", "harnesses": ["codex"]}

    # the inline init write and the infra adapter agree on shape (no fork).
    service.init(
        tmp_path.parent / (tmp_path.name + "-roundtrip"),
        skip_assets=True,
        harnesses=("claude", "pi"),
    )
    states_dir = tmp_path.parent / (tmp_path.name + "-roundtrip") / ".dadaia" / "states"
    profile = JsonHarnessProfileStore().read(states_dir)
    assert profile == HarnessProfile(schema_version="1", harnesses=("claude", "pi"))

    # omitting *harnesses* persists the full L1 roster (default all-four).
    default_root = tmp_path.parent / (tmp_path.name + "-default")
    service.init(default_root, skip_assets=True)
    default_data = json.loads(_profile_path(default_root).read_text(encoding="utf-8"))
    assert default_data["harnesses"] == list(L1_ENTRY_HARNESSES)


def test_idempotent_reinit_and_absent_profile_reads_none(
    service: WorkspaceService, tmp_path: Path
) -> None:
    # re-running init with the same set does not rewrite the profile file.
    service.init(tmp_path, skip_assets=True, harnesses=("codex",))
    path = _profile_path(tmp_path)
    first_mtime = path.stat().st_mtime_ns
    first_bytes = path.read_bytes()

    service.init(tmp_path, skip_assets=True, harnesses=("codex",))

    assert path.read_bytes() == first_bytes
    assert path.stat().st_mtime_ns == first_mtime

    # a pre-v0.1.58 workspace (no profile file) reads as None ⇒ all-four convention.
    absent_root = tmp_path.parent / (tmp_path.name + "-absent")
    states_dir = absent_root / ".dadaia" / "states"
    states_dir.mkdir(parents=True)
    assert JsonHarnessProfileStore().read(states_dir) is None


def test_reinit_with_subset_merges_previously_persisted_harnesses(
    service: WorkspaceService, tmp_path: Path
) -> None:
    """Bug init-harness-profile-silent-narrowing: a subset re-init MERGES the profile.

    init deletes no projection, so it must never un-manage one: re-running init with a
    harness subset (e.g. adding kimi-code to a claude+codex workspace) merges into the
    persisted profile in canonical L1 order instead of replacing it — otherwise the
    previously scaffolded harnesses silently drop out of install/doctor scope
    ([warn] out-of-profile) and their projections rot.
    """
    service.init(tmp_path, skip_assets=True, harnesses=("claude", "codex"))
    service.init(tmp_path, skip_assets=True, harnesses=("kimi-code",))

    data = json.loads(_profile_path(tmp_path).read_text(encoding="utf-8"))
    assert data == {"schema_version": "1", "harnesses": ["claude", "codex", "kimi-code"]}


def test_reinit_same_set_does_not_duplicate_ctx_inject_hook(
    service: WorkspaceService, tmp_path: Path
) -> None:
    """A claude re-init leaves exactly one ctx-inject hook entry (no second registration).

    Kept named — this proved a real drift-bug class (duplicate hook registration on
    repeated init)."""
    service.init(tmp_path, skip_assets=True, harnesses=("claude",))
    service.init(tmp_path, skip_assets=True, harnesses=("claude",))

    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    entries = settings["hooks"]["UserPromptSubmit"]
    ctx_inject = [
        h
        for entry in entries
        for h in entry.get("hooks", [])
        if "dadaia_workspace.hooks.ctx_inject" in h.get("command", "")
    ]
    assert len(ctx_inject) == 1, entries
    assert " -B -m dadaia_workspace.hooks.ctx_inject" in ctx_inject[0]["command"]
