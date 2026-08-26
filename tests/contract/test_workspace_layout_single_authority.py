"""Contract — one authority per filesystem-layout invariant (2026-08-06 analysis).

The root whitelist diverged the day DADAIA.md was added to the hook's copy and not the
doctor's. These tests pin that every consumer DERIVES from ``core/workspace_layout.py``
— identity, not equality, where possible — so divergence is unrepresentable.
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
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.infrastructure import install_helpers

    assert install_helpers._DADAIA_MD_HARNESS_TARGETS is (
        workspace_layout.DADAIA_MD_HARNESS_TARGETS
    )


def test_doctor_dadaia_allowlist_is_the_same_object() -> None:
    """Bug dadaia-reconcile-quarantines-sanctioned-references-clone: doctor's ROOT-4
    ``.dadaia/`` allowlist must be the SAME object as the core authority, never a
    hand-copied literal that can silently diverge (as it did the moment T-045-23
    sanctioned "references" in one copy but not the other)."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.spec_context import doctor

    assert doctor._DADAIA_ALLOWED_SUBDIRS is workspace_layout.DADAIA_ALLOWED_SUBDIRS


def test_migrate_legacy_quarantine_set_never_contains_a_canonical_dadaia_dir() -> None:
    """Bug dadaia-reconcile-quarantines-sanctioned-references-clone: migrate's legacy-
    quarantine set is DERIVED from the same core authority doctor's ROOT-4 allowlist
    uses, so a name cannot be canonical (never quarantined) and legacy (always
    quarantined) at once — the structural cause of the bug is unrepresentable, not
    merely absent from today's values."""
    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.features.migrate import legacy_dadaia_dirs

    assert legacy_dadaia_dirs.LEGACY_DADAIA_SUBDIRS.isdisjoint(
        workspace_layout.DADAIA_ALLOWED_SUBDIRS
    )
