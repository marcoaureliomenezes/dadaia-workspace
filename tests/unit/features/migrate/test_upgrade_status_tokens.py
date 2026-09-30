"""Intent: CONTRACT — `specs upgrade` rewrites the retired Portuguese status tokens in the
live candidate's trio (0.4.7 FR4 / T-047-58), never in a closed rc-<N>/ or published
history (ADR 0150 (1)). Size: SMALL."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.gitflow import merge_frontmatter
from dadaia_workspace.features.migrate.upgrade import (
    plan_status_token_rewrites,
    rewrite_status_tokens,
)
from dadaia_workspace.features.specs import canon
from dadaia_workspace.features.specs.doctor import SpecsDoctor

pytestmark = pytest.mark.unit


def _trio(root: Path, status: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root.parent / "_RELEASE.json").write_text("{}", encoding="utf-8")
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (root / name).write_text(f"# doc\n\n> **Status:** {status}\n", encoding="utf-8")


# fmt: off
@pytest.mark.parametrize(("dirs", "expected"), [
    pytest.param({"0.4.7/rc-1": "Em revisão", "0.4.7/rc-2": "Rascunho"},
                 {"0.4.7/rc-2": "Draft"}, id="live-candidate-only-closed-rc-kept"),
    pytest.param({"0.9.9/rc-1": "Em revisao"}, {"0.9.9/rc-1": "In review"}, id="accent-stripped-worker-spelling"),
    pytest.param({"_archive/0.4.6/rc-1": "Aprovado"}, {}, id="published-archive-never-rewritten"),
    pytest.param({"0.4.7/rc-1": "Approved"}, {}, id="already-english-no-op"),
])
# fmt: on
def test_upgrade_rewrites_retired_status_tokens_only_in_the_live_trio(tmp_path: Path, dirs: dict[str, str], expected: dict[str, str]) -> None:
    for rel, status in dirs.items():
        _trio(tmp_path / "releases" / rel, status)
    touched = {tmp_path / "releases" / rel / n for rel in expected for n in ("SPEC.md", "PLAN.md", "TASKS.md")}

    assert set(plan_status_token_rewrites(tmp_path)) == touched
    assert set(rewrite_status_tokens(tmp_path)) == touched
    for rel, status in dirs.items():
        text = (tmp_path / "releases" / rel / "PLAN.md").read_text(encoding="utf-8")
        assert text.splitlines()[2] == f"> **Status:** {expected.get(rel, status)}"


def test_one_upgrade_run_folds_a_legacy_flat_tree_clean(tmp_path: Path) -> None:
    """ADR 0150, 0151 M5, 0152 (4): a stamp-6 tree whose release carries the legacy
    `RELEASE.json`, a closed `rc-1/` and a flat trio is clean after ONE `specs upgrade`:
    the trio lands in `rc-2/`, the dry run plans the same destinations, `rc-1/` is kept."""
    specs = tmp_path / "specs"
    canon.scaffold(specs, project_name="p")
    merge_frontmatter(specs, specs_pattern_version=6)
    release = specs / "releases" / "0.7.0"
    _trio(release / "rc-1", "Aprovado")
    state = {"schema": "release-state-v1", "release": "0.7.0", "phase": "DEFINITION",
             "defined": None, "implemented": None, "shipped": None, "log": []}  # fmt: skip
    (release / "RELEASE.json").write_text(json.dumps(state), encoding="utf-8")
    (release / "_RELEASE.json").unlink()
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (release / name).write_text("**Status:** Rascunho\n**Origin:** operator-demand\n")
    argv = ["specs", "upgrade", "--specs-dir", str(specs)]

    dry = CliRunner().invoke(app, [*argv, "--dry-run"])
    assert f"rewrite {release / 'rc-2' / 'PLAN.md'}" in dry.output
    assert "rc-1" not in "".join(line for line in dry.output.splitlines() if "rewrite" in line)
    done = CliRunner().invoke(app, argv)
    assert done.exit_code == 0, done.output
    assert sorted(p.name for p in release.iterdir()) == ["_RELEASE.json", "rc-1", "rc-2"]
    assert "Draft" in (release / "rc-2" / "PLAN.md").read_text(encoding="utf-8")
    assert "Aprovado" in (release / "rc-1" / "PLAN.md").read_text(encoding="utf-8")
    assert [i.code for i in SpecsDoctor(specs).check() if i.error] == []
