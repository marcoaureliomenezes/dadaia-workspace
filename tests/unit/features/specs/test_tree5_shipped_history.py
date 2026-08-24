"""Bug ``upgrade-never-refreshes-uncustomised-scoped-law-projection`` (MEDIUM) — TREE-5
must tell a stale SHIPPED projection apart from real operator customisation.

Intent: REGRESSION (bug upgrade-never-refreshes-uncustomised-scoped-law-projection). Size: SMALL.

``specs/AGENTS.md`` is projected from ``templates/specs-AGENTS.md`` and never refreshed:
TREE-5 warns and ``--fix`` skips it, because a silent overwrite would destroy operator
customisation. With no way to detect customisation, a file byte-identical to a version
this tool itself shipped earlier is frozen exactly like a hand-edited one — so instances
kept scoped law ordering agents to run ``dadaia lifecycle``, a command the CLI no longer
exposes.

The evidence that settles it is the shipped-version history: if the on-disk bytes equal a
version we published, the operator never touched it and refreshing is lossless. Bytes we
never shipped are operator content and stay untouched — pinned below so the repair can
never grow into a data-destroying overwrite.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.template_history import (
    SHIPPED_HASHES_FILENAME,
    was_shipped,
)

_REPO_ROOT = Path(__file__).parents[4]
_REAL_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_CANONICAL_TEXT = (_REAL_TEMPLATES_DIR / "specs-AGENTS.md").read_text(encoding="utf-8")

_STALE_SHIPPED = (
    "# SDD workflow contract\n\n"
    "Run ordered work through exactly one of the four `dadaia lifecycle` workflows:\n"
    "`backlog-definition`, `release-definition`, `implementation-reviews`, or `audit`.\n"
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _templates_dir(root: Path, *shipped: str) -> Path:
    """A templates dir carrying the canonical template plus a recorded shipped history."""
    templates = root / "templates"
    templates.mkdir(parents=True)
    (templates / "specs-AGENTS.md").write_text(_CANONICAL_TEXT, encoding="utf-8")
    (templates / SHIPPED_HASHES_FILENAME).write_text(
        json.dumps({"specs-AGENTS.md": [_sha(t) for t in (_CANONICAL_TEXT, *shipped)]}),
        encoding="utf-8",
    )
    return templates


def _specs_tree(root: Path, agents_md: str) -> Path:
    specs = root / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "AGENTS.md").write_text(agents_md, encoding="utf-8")
    return specs


def test_stale_shipped_projection_is_refreshed(tmp_path: Path) -> None:
    """Bytes we shipped earlier carry no customisation: TREE-5 offers the repair and
    ``fix()`` restores the canonical text, clearing the issue."""
    templates = _templates_dir(tmp_path, _STALE_SHIPPED)
    specs = _specs_tree(tmp_path / "stale", _STALE_SHIPPED)

    doctor = SpecsDoctor(specs, templates_dir=templates)
    issues = [i for i in doctor.check() if i.code == "TREE-5"]
    assert issues and issues[0].fixable, "a stale shipped projection must be auto-fixable"

    doctor.fix(issues)
    assert (specs / "AGENTS.md").read_text(encoding="utf-8") == _CANONICAL_TEXT
    assert [i for i in doctor.check() if i.code == "TREE-5"] == []


def test_operator_customisation_is_never_overwritten(tmp_path: Path) -> None:
    """Bytes the tool never shipped are operator content: TREE-5 stays warn-only and
    ``fix()`` leaves the file exactly as it is."""
    customised = "# AGENTS\n\nOur own workflow contract, hand-written.\n"
    templates = _templates_dir(tmp_path, _STALE_SHIPPED)
    specs = _specs_tree(tmp_path / "custom", customised)

    doctor = SpecsDoctor(specs, templates_dir=templates)
    issues = [i for i in doctor.check() if i.code == "TREE-5"]
    assert issues and not issues[0].fixable

    doctor.fix(doctor.check())
    assert (specs / "AGENTS.md").read_text(encoding="utf-8") == customised


def test_missing_history_file_keeps_the_conservative_behaviour(tmp_path: Path) -> None:
    """With no recorded history (older instance, hand-made templates dir) nothing is
    provably ours, so drift stays warn-only rather than being overwritten."""
    templates = tmp_path / "bare-templates"
    templates.mkdir()
    (templates / "specs-AGENTS.md").write_text(_CANONICAL_TEXT, encoding="utf-8")
    specs = _specs_tree(tmp_path / "bare", _STALE_SHIPPED)

    doctor = SpecsDoctor(specs, templates_dir=templates)
    issues = [i for i in doctor.check() if i.code == "TREE-5"]
    assert issues and not issues[0].fixable
    doctor.fix(doctor.check())
    assert (specs / "AGENTS.md").read_text(encoding="utf-8") == _STALE_SHIPPED


def test_shipped_history_records_the_current_canonical_template() -> None:
    """Anti-rot: every template edit must append its new hash, or the next stale
    projection stops being recognisable as ours."""
    assert was_shipped(_CANONICAL_TEXT, "specs-AGENTS.md", _REAL_TEMPLATES_DIR)
