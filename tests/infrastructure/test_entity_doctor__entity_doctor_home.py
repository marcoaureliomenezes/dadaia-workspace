"""The harness-independent public-asset coherence checks live in
``infrastructure.entity_doctor``, not a codex-named home; ``public_assets`` re-exports no
underscore name as a test-only interface."""

from __future__ import annotations

from pathlib import Path


def test_harness_independent_checks_live_in_entity_doctor() -> None:
    from dadaia_workspace.infrastructure import codex_doctor, entity_doctor

    assert callable(entity_doctor.check_agent_skill_refs)
    assert callable(entity_doctor.check_entities_derivation)
    for name in (
        "check_agent_skill_refs",
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
