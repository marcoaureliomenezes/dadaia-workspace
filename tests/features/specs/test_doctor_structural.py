"""TREE-5 tells a stale SHIPPED projection (bytes equal a version we published: refresh is
lossless) from operator customisation (bytes we never shipped: never overwritten).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.core import platform
from dadaia_workspace.core.template_history import (
    SHIPPED_HASHES_FILENAME,
    was_shipped,
)
from dadaia_workspace.core.workspace_layout import render_registry_tables
from dadaia_workspace.features.specs import canon
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_types import finding_path
from tests.helpers.oslib import read_text, write_text

_REPO_ROOT = Path(__file__).parents[3]
_REAL_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_CANONICAL_TEXT = read_text(_REAL_TEMPLATES_DIR / "specs-AGENTS.md")

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
    write_text(specs / "AGENTS.md", agents_md)
    return specs


_CUSTOMISED = "# AGENTS\n\nOur own workflow contract, hand-written.\n"


@pytest.mark.parametrize(
    ("agents_md", "history", "fixable"),
    [
        pytest.param(_STALE_SHIPPED, True, True, id="B38-3-stale-shipped-is-refreshed-rendered"),
        pytest.param(_CUSTOMISED, True, False, id="B38-5-operator-customisation-never-overwritten"),
        pytest.param(_STALE_SHIPPED, True, True, id="stale-shipped-is-refreshed-rendered"),
        pytest.param(_CUSTOMISED, True, False, id="operator-customisation-never-overwritten"),
        pytest.param(_STALE_SHIPPED, False, False, id="no-history-file-stays-warn-only"),
    ],
)
def test_tree5_refreshes_only_bytes_we_shipped(
    tmp_path: Path, agents_md: str, history: bool, fixable: bool
) -> None:
    """TREE-5 is fixable only when the on-disk bytes are a recorded shipped version; ``fix()``
    then writes the RENDERED law, otherwise it leaves the file byte-identical."""
    templates = tmp_path / "templates"
    templates.mkdir()
    write_text(templates / "specs-AGENTS.md", _CANONICAL_TEXT)
    if history:
        hashes = {"specs-AGENTS.md": [_sha(_CANONICAL_TEXT), _sha(_STALE_SHIPPED)]}
        write_text(templates / SHIPPED_HASHES_FILENAME, json.dumps(hashes))
    specs = _specs_tree(tmp_path, agents_md)
    doctor = SpecsDoctor(specs, templates_dir=templates)
    [tree5] = [i for i in doctor.check() if i.code == "TREE-5"]
    assert tree5.fixable is fixable

    doctor.fix(doctor.check())
    law = read_text(specs / "AGENTS.md")
    if fixable:
        assert "| Area | Members |" in law and "<!-- specs-canon -->" not in law
        assert [i for i in doctor.check() if i.code == "TREE-5"] == []
    else:
        assert law == agents_md


def test_shipped_history_records_the_current_canonical_template(tmp_path: Path) -> None:
    """The history records the digest of what `specs init` writes (the
    rendered law) and keeps the raw template an older init wrote as ours."""
    specs = tmp_path / "specs"
    canon.scaffold(specs, project_name="p")
    written = read_text(specs / "AGENTS.md")
    assert was_shipped(written, "specs-AGENTS.md", _REAL_TEMPLATES_DIR)
    assert was_shipped(_CANONICAL_TEXT, "specs-AGENTS.md", _REAL_TEMPLATES_DIR)


# Written with the project name filled in, so the file's own bytes are never what is on disk.
_PROJECT_FILLED = {"scaffold/memory/ARCHITECTURE.md", "scaffold/memory/QUALITY.md"}


def _held_text(asset: str) -> str:
    """The bytes a workspace of the current host holds for *asset*: hook scripts are installed
    as they are, every other asset through the installer's render."""
    public = _REAL_TEMPLATES_DIR.parent
    source = public / ("templates" if "/" not in asset else "") / asset
    text = read_text(source)
    return text if asset.startswith("scripts/") else render_registry_tables(text)


@pytest.mark.parametrize("host", ["linux", "win32"])
def test_shipped_history_records_every_shipped_asset_for_every_host(
    host: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whatever host a workspace runs on, the history recognises the current asset it holds."""
    monkeypatch.setattr(platform, "PLATFORM", platform.Capabilities.detect(host))
    history = json.loads(read_text(_REAL_TEMPLATES_DIR / SHIPPED_HASHES_FILENAME))
    unknown = [
        asset
        for asset in sorted(history.keys() - _PROJECT_FILLED)
        if not was_shipped(_held_text(asset), asset, _REAL_TEMPLATES_DIR)
    ]
    assert unknown == []


# The same history covers every scoped scaffold law file.

_SCOPED_STALE = "# specs/releases/ — old era\n\nRELEASE.jsonl append-only event log.\n"
_SCOPED_CANONICAL = "# specs/releases/ — Release Rules\n\nRELEASE.json is one mutable doc.\n"


def _public_dir_with_scoped(root: Path, *shipped: str) -> Path:
    public = root / "public"
    templates = public / "templates"
    templates.mkdir(parents=True)
    write_text(templates / "specs-AGENTS.md", _CANONICAL_TEXT)
    scaffold = public / "scaffold" / "releases"
    scaffold.mkdir(parents=True)
    write_text(scaffold / "AGENTS.md", _SCOPED_CANONICAL)
    write_text(
        templates / SHIPPED_HASHES_FILENAME,
        json.dumps(
            {
                "specs-AGENTS.md": [_sha(_CANONICAL_TEXT)],
                "scaffold/releases/AGENTS.md": [_sha(t) for t in (_SCOPED_CANONICAL, *shipped)],
            }
        ),
    )
    return public


def test_stale_shipped_scoped_law_is_refreshed(tmp_path: Path) -> None:
    public = _public_dir_with_scoped(tmp_path, _SCOPED_STALE)
    specs = _specs_tree(tmp_path / "scoped-stale", _CANONICAL_TEXT)
    (specs / "releases").mkdir(parents=True, exist_ok=True)
    write_text(specs / "releases" / "AGENTS.md", _SCOPED_STALE)

    doctor = SpecsDoctor(specs, public_dir=public)
    issues = [i for i in doctor.check() if i.code == "TREE-5"]
    scoped = [
        i for i in issues if Path(finding_path(i) or "").as_posix().endswith("releases/AGENTS.md")
    ]
    assert scoped and scoped[0].fixable, "a stale shipped scoped projection must be fixable"

    doctor.fix(issues)
    assert read_text(specs / "releases" / "AGENTS.md") == _SCOPED_CANONICAL


def test_shipped_history_records_every_current_scaffold_law() -> None:
    """Anti-rot, scoped half: every scaffold AGENTS.md edit must append its new hash."""
    scaffold_root = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold"
    for area in ("memory", "releases", "backlog", "bugs", "audits", "ADRs"):
        text = read_text(scaffold_root / area / "AGENTS.md")
        assert was_shipped(text, f"scaffold/{area}/AGENTS.md", _REAL_TEMPLATES_DIR), area
