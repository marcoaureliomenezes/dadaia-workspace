"""The symlink refusal's fix is spelled over its words: a blank in the path stays one word."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import command, link

_NEW = load_owner("dd-release-implementation", "_release_new")


def test_the_symlink_fix_quotes_a_releases_path_with_a_blank(tmp_path: Path) -> None:
    specs = tmp_path / "a b" / "specs"
    specs.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    if not link(str(elsewhere), specs / "releases", is_dir=True):
        pytest.skip("the host refuses symlinks")
    with pytest.raises(_NEW.Refusal) as refused:
        _NEW.new_release(specs, "0.5.0", "2026-10-16", "operator-demand")
    assert refused.value.fix == command("ls", "-l", str(specs / "releases"))
