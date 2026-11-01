"""Write sites never follow a link; a corrupt or oversized shipped-hashes history degrades
rather than crashes the doctor.

CWE-59/CWE-61 link following, CWE-73 externally supplied path, CWE-703 unchecked exceptional
condition, CWE-674 uncontrolled recursion. Covers SpecsDoctor's TREE-5 repair and
template_history.load_shipped_hashes' corrupt-input path.
Size: SMALL.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dadaia_workspace.core.template_history import (
    SHIPPED_HASHES_FILENAME,
    load_shipped_hashes,
)
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from tests.helpers.oslib import link, read_text, write_text

_REPO_ROOT = Path(__file__).parents[3]
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_CANONICAL_TEXT = read_text(_TEMPLATES_DIR / "specs-AGENTS.md")


def _specs_with_memory(root: Path) -> Path:
    specs = root / "specs"
    (specs / "memory").mkdir(parents=True)
    return specs


def test_fix_tree5_refuses_a_symlinked_projection(tmp_path: Path) -> None:
    """The repair must not write the canonical template through a link, and must ignore a
    caller-supplied path — the target is always derived from the specs dir."""
    stale = "# stale\n"
    templates = tmp_path / "templates"
    templates.mkdir()
    write_text(templates / "specs-AGENTS.md", _CANONICAL_TEXT)

    write_text(
        templates / SHIPPED_HASHES_FILENAME,
        json.dumps(
            {
                "specs-AGENTS.md": [
                    hashlib.sha256(t.encode("utf-8")).hexdigest() for t in (_CANONICAL_TEXT, stale)
                ]
            }
        ),
    )

    outside = tmp_path / "outside_agents.md"
    write_text(outside, stale)
    specs = _specs_with_memory(tmp_path / "linked")
    assert link(str(outside), specs / "AGENTS.md", is_dir=False)

    doctor = SpecsDoctor(specs, templates_dir=templates)
    doctor.fix(doctor.check())

    assert read_text(outside) == stale, "fix_tree5 wrote through a symlink"


def test_corrupt_history_degrades_instead_of_killing_the_doctor(tmp_path: Path) -> None:
    """A deeply nested history blows the JSON parser's stack; it must degrade to "nothing
    is provably ours" like every other malformation."""
    templates = tmp_path / "templates"
    templates.mkdir()
    write_text(templates / SHIPPED_HASHES_FILENAME, "[" * 200_000)

    assert load_shipped_hashes(templates) == {}


def test_symlinked_projection_is_not_advertised_as_fixable(tmp_path: Path) -> None:
    """The repair refuses a symlinked projection, so the check must not promise it —
    a reported fix that never happens is its own defect."""
    stale = "# stale\n"
    templates = tmp_path / "templates"
    templates.mkdir()
    write_text(templates / "specs-AGENTS.md", _CANONICAL_TEXT)
    write_text(
        templates / SHIPPED_HASHES_FILENAME,
        json.dumps(
            {
                "specs-AGENTS.md": [
                    hashlib.sha256(t.encode("utf-8")).hexdigest() for t in (_CANONICAL_TEXT, stale)
                ]
            }
        ),
    )
    outside = tmp_path / "outside.md"
    write_text(outside, stale)
    specs = _specs_with_memory(tmp_path / "advertise")
    assert link(str(outside), specs / "AGENTS.md", is_dir=False)

    doctor = SpecsDoctor(specs, templates_dir=templates)
    tree5 = [i for i in doctor.check() if i.code == "TREE-5"]
    assert tree5 and not tree5[0].fixable
    assert doctor.fix(doctor.check()) == [] or all(i.code != "TREE-5" for i in doctor.fix())
