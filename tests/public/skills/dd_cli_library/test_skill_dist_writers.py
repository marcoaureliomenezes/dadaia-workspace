"""The skill's sentence listing what writes `.dadaia/dist/` names every verb that does."""

from __future__ import annotations

from pathlib import Path

from tests.helpers.oslib import read_text

_SKILL = (
    Path(__file__).resolve().parents[4] / "dadaia_workspace/public/skills/dd-cli-library/SKILL.md"
)


def test_the_dist_writer_sentence_names_worktree_pause_and_resume() -> None:
    (sentence,) = [ln for ln in read_text(_SKILL).splitlines() if ".dadaia/dist/" in ln]

    assert "`worktree pause`" in sentence
    assert "`worktree resume`" in sentence
