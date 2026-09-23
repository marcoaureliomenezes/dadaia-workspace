"""Intent: CONTRACT — `specs upgrade` removes a live `releases/_ideas/` that holds nothing
but the scaffolded AGENTS.md (0.4.7 c5 T-047-49: `_ideas/` left the canon). Size: SMALL."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.upgrade import plan_empty_ideas_dir, remove_empty_ideas_dir

pytestmark = pytest.mark.unit


def test_an_ideas_dir_with_only_agents_md_is_removed(tmp_path: Path) -> None:
    ideas = tmp_path / "releases" / "_ideas"
    ideas.mkdir(parents=True)
    (ideas / "AGENTS.md").write_text("# ideas\n", encoding="utf-8")
    assert plan_empty_ideas_dir(tmp_path) == [ideas]
    assert remove_empty_ideas_dir(tmp_path) == [ideas]
    assert not ideas.exists()


def test_an_ideas_dir_holding_a_draft_is_left_alone(tmp_path: Path) -> None:
    ideas = tmp_path / "releases" / "_ideas" / "0.9.9"
    ideas.mkdir(parents=True)
    (ideas / "SPEC.md").write_text("draft\n", encoding="utf-8")
    assert plan_empty_ideas_dir(tmp_path) == []
    assert remove_empty_ideas_dir(tmp_path) == []
    assert ideas.exists()


def test_no_ideas_dir_is_a_no_op(tmp_path: Path) -> None:
    assert remove_empty_ideas_dir(tmp_path) == []
