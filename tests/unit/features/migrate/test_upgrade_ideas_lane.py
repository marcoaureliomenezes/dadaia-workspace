"""Intent: CONTRACT — `specs upgrade` removes a live `releases/_ideas/` that holds nothing
but the scaffolded AGENTS.md (0.4.7 c5 T-047-49: `_ideas/` left the canon). Size: SMALL."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.migrate.upgrade import plan_empty_ideas_dir, remove_empty_ideas_dir
from dadaia_workspace.features.spec_context import sweep

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("files", "outside", "removed"),
    [(["AGENTS.md"], False, True), (["0.9.9/SPEC.md"], False, False), ([], False, False), (["AGENTS.md"], True, False)],
    ids=["only-agents-md-removed", "holding-a-draft-left-alone", "no-ideas-dir-no-op",
         "doctor-reports-a-refused-removal-as-deleted-refused-ideas-dir-not-reported"],
)  # fmt: skip
def test_upgrade_removes_an_ideas_dir_holding_only_its_agents_md(
    tmp_path: Path, files: list[str], outside: bool, removed: bool
) -> None:
    specs = tmp_path / "specs"
    ideas = specs / "releases" / "_ideas"
    for rel in files:
        (ideas / rel).parent.mkdir(parents=True, exist_ok=True)
        (ideas / rel).write_text("x\n", encoding="utf-8")
    if outside:  # releases/ resolves outside the specs tree: the deleter refuses
        (specs / "releases").rename(tmp_path / "elsewhere")
        (specs / "releases").symlink_to(tmp_path / "elsewhere")

    assert plan_empty_ideas_dir(specs) == ([ideas] if files == ["AGENTS.md"] else [])
    assert remove_empty_ideas_dir(specs, sweep.deleter(specs)) == ([ideas] if removed else [])
    assert ideas.exists() is (bool(files) and not removed)
