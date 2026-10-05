"""``WorkspaceService.init`` persists the harness profile through the ONE writer,
``JsonHarnessProfileStore.write`` — the service never spells the file (the inline
``_write_harness_profile`` copy is gone). Re-running ``init`` with the same set is a no-op
(no spurious rewrite, no second hook entry). An absent profile file (a pre-v0.1.58 workspace)
reads as ``None`` — the "treated as all-four" back-compat convention every consumer honours.

These are unit-level assertions over the real service with fake asset/venv managers; the
harness-gated *scaffold* behaviour (which dirs/hooks appear) is pinned end-to-end by the
CLI suite ``tests/unit/cli/test_init_harness.py``.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.features.workspace import service as service_module
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


# fmt: off
@pytest.mark.parametrize(("inits", "expected"), [
    pytest.param([("codex",)], ("codex",), id="persists-the-selected-set"),
    pytest.param([("claude", "kimi-code")], ("claude", "kimi-code"), id="store-reads-back-what-init-wrote"),
    pytest.param([("codex",), ("codex",)], ("codex",), id="same-set-reinit-never-rewrites"),
    pytest.param([("claude", "codex"), ("kimi-code",)], ("claude", "codex", "kimi-code"), id="init-harness-profile-silent-narrowing-subset-merges"),
])
# fmt: on
def test_init_persists_the_harness_profile_through_the_one_store(
    service: WorkspaceService, tmp_path: Path, inits: list[tuple[str, ...]], expected: tuple[str, ...]
) -> None:
    """A subset re-init MERGES in canonical L1 order (init deletes no projection, so it never un-manages one)."""
    service.init(tmp_path, skip_assets=True, harnesses=inits[0])
    before = (_profile_path(tmp_path).read_bytes(), _profile_path(tmp_path).stat().st_mtime_ns)
    for harnesses in inits[1:]:
        service.init(tmp_path, skip_assets=True, harnesses=harnesses)

    assert JsonHarnessProfileStore().read(tmp_path / ".dadaia" / "states") == HarnessProfile(schema_version="1", harnesses=expected)
    assert json.loads(_profile_path(tmp_path).read_text(encoding="utf-8")) == {"schema_version": "1", "harnesses": list(expected)}
    if inits[1:] == inits[:1]:
        assert (_profile_path(tmp_path).read_bytes(), _profile_path(tmp_path).stat().st_mtime_ns) == before


def test_an_absent_profile_reads_none(tmp_path: Path) -> None:
    """A pre-v0.1.58 workspace (no profile file) reads as None: the all-four convention."""
    assert JsonHarnessProfileStore().read(tmp_path) is None


def test_init_writes_the_profile_through_the_store_and_never_spells_the_file() -> None:
    """AC9 (FR8): one writer. The service holds no copy of the profile's file name or
    payload shape — both live only in ``infrastructure/json_harness_profile_store``."""
    source = inspect.getsource(service_module)

    assert "_write_harness_profile" not in source
    assert "_persisted_profile_harnesses" not in source
    assert "harness_profile.json" not in source
