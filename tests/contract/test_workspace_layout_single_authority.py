"""Intent: CONTRACT — core.workspace_layout single authority (bug dadaia-reconcile-quarantines-sanctioned-references-clone; 0.4.6 AC1); size: SMALL.

One authority per filesystem-layout invariant (2026-08-06 analysis). The root whitelist
diverged the day DADAIA.md was added to the hook's copy and not the doctor's; the
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
    assert gate_policy._LAW_HARNESS_DIRS is workspace_layout.LAW_HARNESS_DIRS


def test_installer_targets_are_the_same_object() -> None:
    """K3 (v0.5.1): the law-projection rule builder (``_law_projection_rules``) reads
    ``DADAIA_MD_HARNESS_TARGETS`` straight off ``core.workspace_layout`` — no more
    private per-module re-export to keep byte-identical (the retired
    ``install_helpers._DADAIA_MD_HARNESS_TARGETS`` alias)."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.infrastructure import projection_rules

    assert projection_rules.DADAIA_MD_HARNESS_TARGETS is workspace_layout.DADAIA_MD_HARNESS_TARGETS


def test_gate_additive_prefixes_are_the_registry_view() -> None:
    """The gate's ``.dadaia/`` ADDITIVE class is the OUTPUT + EPHEMERAL rows of the
    registry (SPEC 0.4.6 FR1, architect A) — ``reports/`` left the class the moment its
    row left the registry, with no gate edit."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import gate_policy

    assert workspace_layout.additive_prefixes() == gate_policy._ADDITIVE_DADAIA_PREFIXES
