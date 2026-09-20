"""Intent: CONTRACT — core.workspace_layout single authority (bug dadaia-reconcile-quarantines-sanctioned-references-clone; 0.4.6 AC1); size: SMALL.

One authority per filesystem-layout invariant (2026-08-06 analysis). The root whitelist
diverged the day the root `AGENTS.md` map was added to the hook's copy and not the doctor's; the
``.dadaia/`` layout diverged six times as bare name lists (architect G, 0.4.6). These
tests pin that every consumer DERIVES from ``core/workspace_layout.py`` — identity where a
constant is re-exported, equality against the registry view where a consumer derives —
so divergence is unrepresentable. ``tests/contract/test_zone_registry.py`` adds the
package-wide ratchet that no second list can be born.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract


def test_hook_whitelist_derives_from_core() -> None:
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.hooks import root_whitelist

    assert root_whitelist._WHITELIST == (
        workspace_layout.ROOT_ALLOWED_DIRS | workspace_layout.ROOT_ALLOWED_FILES
    )
    assert root_whitelist._ROOT_FILES is workspace_layout.ROOT_ALLOWED_FILES


def test_doctor_root_walk_derives_from_core(tmp_path: Path) -> None:
    """The doctor holds no root list of its own (T-046-25): every name the law allows
    reads canon straight off ``workspace_layout``, and the module re-exports nothing."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import doctor
    from tests.fakes import FakeContextStore, FakeGitClient

    assert not hasattr(doctor, "_ROOT_ALLOWED_DIRS")
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    for name in workspace_layout.ROOT_ALLOWED_DIRS:
        (tmp_path / name).mkdir(exist_ok=True)
    for name in workspace_layout.ROOT_ALLOWED_FILES:
        (tmp_path / name).write_text("", encoding="utf-8")
    findings = doctor.DoctorService(FakeContextStore(), FakeGitClient(), tmp_path).scan()
    root = {f.path: f.verdict.value for f in findings if f.code.startswith("WS-root-")}
    assert set(root.values()) == {"canon"}
    assert set(root) == workspace_layout.ROOT_ALLOWED_DIRS | workspace_layout.ROOT_ALLOWED_FILES


def test_gate_law_sets_are_the_same_objects() -> None:
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import gate_policy

    assert gate_policy._LAW_BASENAMES is workspace_layout.LAW_BASENAMES


def test_harness_dirs_derive_from_the_one_harness_registry() -> None:
    """0.4.7 FR3: "which root directory a harness owns" lives once, in
    ``core.harness_registry.HARNESS_PROJECTION_DIRS``. ``HARNESS_DIRS`` is the shared
    ``.agents`` tree plus that registry's values — never a second hand-kept name list,
    and a harness with an empty set (``kimi-code``) contributes nothing."""
    from dadaia_workspace.core import harness_registry, workspace_layout

    assert harness_registry.HARNESS_PROJECTION_DIRS["kimi-code"] == ()
    derived = {".agents"} | {
        d for dirs in harness_registry.HARNESS_PROJECTION_DIRS.values() for d in dirs
    }
    assert derived == workspace_layout.HARNESS_DIRS
    assert ".kimi-code" not in workspace_layout.HARNESS_DIRS


def test_gate_additive_prefixes_are_the_registry_view() -> None:
    """The gate's ``.dadaia/`` ADDITIVE class is the OUTPUT + EPHEMERAL rows of the
    registry (SPEC 0.4.6 FR1, architect A) — ``reports/`` left the class the moment its
    row left the registry, with no gate edit."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import gate_policy

    assert workspace_layout.additive_prefixes() == gate_policy._ADDITIVE_DADAIA_PREFIXES
