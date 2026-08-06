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
