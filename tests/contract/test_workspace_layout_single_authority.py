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

import pytest

pytestmark = pytest.mark.contract


def test_hook_whitelist_derives_from_core() -> None:
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.hooks import root_whitelist

    assert root_whitelist._WHITELIST == (
        workspace_layout.ROOT_ALLOWED_DIRS | workspace_layout.ROOT_ALLOWED_FILES
    )
    assert root_whitelist._ROOT_FILES is workspace_layout.ROOT_ALLOWED_FILES


def test_doctor_whitelist_is_the_same_object() -> None:
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import doctor

    assert doctor._ROOT_ALLOWED_DIRS is workspace_layout.ROOT_ALLOWED_DIRS
    assert doctor._ROOT_ALLOWED_FILES is workspace_layout.ROOT_ALLOWED_FILES


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

    assert workspace_layout.additive_prefixes() == gate_policy._DADAIA_ADDITIVE_PREFIXES


def test_public_doctor_foreign_scan_skips_the_registry_additive_view() -> None:
    """Compatibility reader (dies in T-046-25 when the foreign scan moves into the doctor
    walk): the public doctor skips exactly the registry's ADDITIVE zones."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.infrastructure import public_assets

    assert workspace_layout.additive_prefixes() == public_assets.DADAIA_ADDITIVE_PREFIXES


def test_doctor_dadaia_allow_set_is_the_registry_view() -> None:
    """Bug dadaia-reconcile-quarantines-sanctioned-references-clone: the doctor's
    ``.dadaia/`` allow set is ``zone_names()`` — compatibility name until T-046-25 switches
    the doctor to the registry walk."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import doctor

    assert workspace_layout.zone_names() == doctor._DADAIA_ALLOWED_SUBDIRS


def test_migrate_legacy_quarantine_set_never_contains_a_zone() -> None:
    """Bug dadaia-reconcile-quarantines-sanctioned-references-clone: a name cannot be a
    registry zone (never quarantined) and legacy (always quarantined) at once. Dies with
    ``legacy_dadaia_dirs`` in T-046-26."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.migrate import legacy_dadaia_dirs

    assert legacy_dadaia_dirs.LEGACY_DADAIA_SUBDIRS.isdisjoint(workspace_layout.zone_names())
