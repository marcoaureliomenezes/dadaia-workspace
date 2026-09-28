"""Intent: CONTRACT — F004: canon paths accept a suffixed release id."""

from __future__ import annotations


def test_suffixed_release_id_is_canon_conformant() -> None:
    """F004: a suffixed id (rc/canary/hotfix — legitimate per AS-13) passed the naming
    checks while TREE-8 errored every file under it. One decider: canon paths accept
    exactly what the naming canon accepts on the bare axis. Intent: regression;
    size: unit."""
    from dadaia_workspace.features.specs.canon import is_canon_path

    assert is_canon_path("releases/0.6.0-rc1/SPEC.md")
    assert is_canon_path("releases/0.6.0-rc1/RELEASE.json")
    assert is_canon_path("releases/_archive/0.6.0-rc1/SPEC.md")
