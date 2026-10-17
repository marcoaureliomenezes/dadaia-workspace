"""The symlink refusal's fix is an act every shell reads alike: a blank in the path stays one word."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import link, quote

_NEW = load_owner("dd-release-implementation", "_release_new")


def test_the_symlink_fix_names_the_releases_path_with_a_blank(tmp_path: Path) -> None:
    specs = tmp_path / "a b" / "specs"
    specs.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    if not link(str(elsewhere), specs / "releases", is_dir=True):
        pytest.skip("the host refuses symlinks")
    with pytest.raises(_NEW.Refusal) as refused:
        _NEW.new_release(specs, "0.5.0", "2026-10-16", "operator-demand")
    assert (
        refused.value.fix
        == f"Agent action: replace the symlink {quote(str(specs / 'releases'))} with a real directory or file"
    )
