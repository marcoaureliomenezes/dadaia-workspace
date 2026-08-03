"""A remedy that damages the tree is worse than a remedy in prose.

I replaced SPEC-DOC-024's prose ("advance ACTIVE.md or correct the markers") with a
`printf ... > ACTIVE.md` that omitted the `segment:` line. Pasted verbatim — which is
exactly what R-23 demands the operator be able to do — it OVERWROTE a valid ACTIVE.md
with an incomplete one and turned zero errors into seven.

So this test does not read the message. It extracts the command, runs it, and asserts the
tree the operator is left with is doctor-clean.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.specs.scaffolder import scaffold, scaffold_release_segment

_TEMPLATES_DIR = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public" / "templates"


def _tree(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    scaffold(specs, project_name="demo", force=False, templates_dir=_TEMPLATES_DIR)
    scaffold_release_segment(specs, "v0.1.0", "alpha-1")
    (specs / "releases" / "ACTIVE.md").write_text(
        "release: v0.1.0\nsegment: alpha-1\nphase: SPEC\n", encoding="utf-8"
    )
    # A release whose tasks are done is a release whose artifacts were approved — set the
    # canonical token so the tree is faithful, not just close enough.
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        f = specs / "releases" / "v0.1.0" / "alpha-1" / name
        f.write_text(
            f.read_text(encoding="utf-8").replace("**Status:** Draft", "**Status:** Aprovado", 1),
            encoding="utf-8",
        )
    tasks = specs / "releases" / "v0.1.0" / "alpha-1" / "TASKS.md"
    tasks.write_text(
        tasks.read_text(encoding="utf-8").replace(
            "## Tasks", "## Tasks\n\n- [x] T-001 done\n- [x] T-002 done\n- [x] T-003 done"
        ),
        encoding="utf-8",
    )
    return specs


def test_the_prescribed_command_leaves_the_tree_clean(tmp_path: Path) -> None:
    specs = _tree(tmp_path)

    doc024 = [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-024"]
    assert doc024, "the fixture did not reproduce the finding"

    command = re.search(r"(printf [^\s].*?ACTIVE\.md)", doc024[0].description)
    assert command, f"no pasteable command in: {doc024[0].description}"

    subprocess.run(command.group(1), shell=True, check=True, cwd=tmp_path)

    after = SpecsDoctor(specs).check()
    errors = [i for i in after if i.severity == Severity.ERROR]
    assert errors == [], (
        "pasting the prescribed remedy left the tree with errors: "
        f"{[(i.code, i.description[:70]) for i in errors]}"
    )
    assert (specs / "releases" / "ACTIVE.md").read_text(encoding="utf-8").count("segment:") == 1
