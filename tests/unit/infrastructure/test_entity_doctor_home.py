"""F014 (20260830-design-bug-surface-audit): modules split by seam, not line-count.

The harness-independent public-asset coherence checks live in an honestly named home
(``infrastructure.entity_doctor``), not a codex-named one; ``public_assets`` no longer
re-exports ~25 underscore names as a test-only interface; ``_compare_content`` (zero
callers) is deleted. Intent: contract; size: unit.
"""

from __future__ import annotations

from pathlib import Path


def test_harness_independent_checks_live_in_entity_doctor() -> None:
    from dadaia_workspace.infrastructure import codex_doctor, entity_doctor

    assert callable(entity_doctor.check_agent_skill_refs)
    assert callable(entity_doctor.check_memory_phase_single_source)
    assert callable(entity_doctor.check_entities_derivation)
    for name in (
        "check_agent_skill_refs",
        "check_memory_phase_single_source",
        "check_entities_derivation",
    ):
        assert not hasattr(codex_doctor, name), name


def test_compare_content_dead_code_is_gone() -> None:
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

    assert not hasattr(FileSystemPublicAssetManager, "_compare_content")


def test_public_assets_carries_no_underscore_reexport_shim() -> None:
    from dadaia_workspace.infrastructure import public_assets

    src = Path(public_assets.__file__).read_text(encoding="utf-8")
    assert "noqa: F401" not in src
