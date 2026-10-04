"""TREE-5 tells a stale SHIPPED projection (bytes equal a version we published: refresh is
lossless) from operator customisation (bytes we never shipped: never overwritten).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.core.template_history import (
    SHIPPED_HASHES_FILENAME,
    was_shipped,
)
from dadaia_workspace.features.specs import canon
from dadaia_workspace.features.specs.doctor import SpecsDoctor

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


def _specs_tree(root: Path, agents_md: str) -> Path:
    specs = root / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "AGENTS.md").write_text(agents_md, encoding="utf-8")
    return specs


_CUSTOMISED = "# AGENTS\n\nOur own workflow contract, hand-written.\n"


@pytest.mark.parametrize(
    ("agents_md", "history", "fixable"),
    [
        pytest.param(_STALE_SHIPPED, True, True, id="B38-3-stale-shipped-is-refreshed-rendered"),
        pytest.param(_CUSTOMISED, True, False, id="B38-5-operator-customisation-never-overwritten"),
        pytest.param(_STALE_SHIPPED, False, False, id="no-history-file-stays-warn-only"),
    ],
)
def test_tree5_refreshes_only_bytes_we_shipped(
    tmp_path: Path, agents_md: str, history: bool, fixable: bool
) -> None:
    """sa-specs-init-writes-unrendered-law#B38-3 sa-specs-init-writes-unrendered-law#B38-5:
    TREE-5 is fixable only when the on-disk bytes are a recorded shipped version; ``fix()``
    then writes the RENDERED law, otherwise it leaves the file byte-identical."""
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "specs-AGENTS.md").write_text(_CANONICAL_TEXT, encoding="utf-8")
    if history:
        hashes = {"specs-AGENTS.md": [_sha(_CANONICAL_TEXT), _sha(_STALE_SHIPPED)]}
        (templates / SHIPPED_HASHES_FILENAME).write_text(json.dumps(hashes), encoding="utf-8")
    specs = _specs_tree(tmp_path, agents_md)
    doctor = SpecsDoctor(specs, templates_dir=templates)
    [tree5] = [i for i in doctor.check() if i.code == "TREE-5"]
    assert tree5.fixable is fixable

    doctor.fix(doctor.check())
    law = (specs / "AGENTS.md").read_text(encoding="utf-8")
    if fixable:
        assert "| Area | Members |" in law and "<!-- specs-canon -->" not in law
        assert [i for i in doctor.check() if i.code == "TREE-5"] == []
    else:
        assert law == agents_md


def test_shipped_history_records_the_current_canonical_template(tmp_path: Path) -> None:
    """sa-specs-init-writes-unrendered-law#B38-4: the history records the digest of what `specs init` writes (the
    rendered law) and keeps the raw template an older init wrote as ours."""
    specs = tmp_path / "specs"
    canon.scaffold(specs, project_name="p")
    written = (specs / "AGENTS.md").read_text(encoding="utf-8")
    assert was_shipped(written, "specs-AGENTS.md", _REAL_TEMPLATES_DIR)
    assert was_shipped(_CANONICAL_TEXT, "specs-AGENTS.md", _REAL_TEMPLATES_DIR)


# T-053-15 (bug releases-agents-projection-stale-vs-scaffold-source): the same history
# covers every scoped scaffold law file (memory/ since 0.4.7 FR6).

_SCOPED_STALE = "# specs/releases/ — old era\n\nRELEASE.jsonl append-only event log.\n"
_SCOPED_CANONICAL = "# specs/releases/ — Release Rules\n\nRELEASE.json is one mutable doc.\n"


def _public_dir_with_scoped(root: Path, *shipped: str) -> Path:
    public = root / "public"
    templates = public / "templates"
    templates.mkdir(parents=True)
    (templates / "specs-AGENTS.md").write_text(_CANONICAL_TEXT, encoding="utf-8")
    scaffold = public / "scaffold" / "releases"
    scaffold.mkdir(parents=True)
    (scaffold / "AGENTS.md").write_text(_SCOPED_CANONICAL, encoding="utf-8")
    (templates / SHIPPED_HASHES_FILENAME).write_text(
        json.dumps(
            {
                "specs-AGENTS.md": [_sha(_CANONICAL_TEXT)],
                "scaffold/releases/AGENTS.md": [_sha(t) for t in (_SCOPED_CANONICAL, *shipped)],
            }
        ),
        encoding="utf-8",
    )
    return public


def test_stale_shipped_scoped_law_is_refreshed(tmp_path: Path) -> None:
    public = _public_dir_with_scoped(tmp_path, _SCOPED_STALE)
    specs = _specs_tree(tmp_path / "scoped-stale", _CANONICAL_TEXT)
    (specs / "releases").mkdir(parents=True, exist_ok=True)
    (specs / "releases" / "AGENTS.md").write_text(_SCOPED_STALE, encoding="utf-8")

    doctor = SpecsDoctor(specs, public_dir=public)
    issues = [i for i in doctor.check() if i.code == "TREE-5"]
    scoped = [i for i in issues if i.message.replace("\\", "/").endswith("releases/AGENTS.md)")]
    assert scoped and scoped[0].fixable, "a stale shipped scoped projection must be fixable"

    doctor.fix(issues)
    assert (specs / "releases" / "AGENTS.md").read_text(encoding="utf-8") == _SCOPED_CANONICAL


def test_shipped_history_records_every_current_scaffold_law() -> None:
    """Anti-rot, scoped half: every scaffold AGENTS.md edit must append its new hash."""
    scaffold_root = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold"
    for area in ("memory", "releases", "backlog", "bugs", "audits", "ADRs"):
        text = (scaffold_root / area / "AGENTS.md").read_text(encoding="utf-8")
        assert was_shipped(text, f"scaffold/{area}/AGENTS.md", _REAL_TEMPLATES_DIR), area
