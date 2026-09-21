"""Release 0.4.6 candidate 1, FR3 (ADR 0007) — SPEC-DOC-046: a live release carrying
the legacy ``RELEASE.json`` name gets a WARNING with a doctor ``--fix`` rename to the
canonical ``_RELEASE.json``. The FR4 second-live-release refusal is the release script's
own contract now (``tests/unit/skills/test_release_implementation_release_script.py``).

Intent: CONTRACT (the migration lane for consumer instances). Size: SMALL.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.specs.doctor import SpecsDoctor


def _specs_with_release(tmp_path: Path, *, legacy_name: bool) -> Path:
    specs = tmp_path / "specs"
    rdir = specs / "releases" / "1.0.0"
    rdir.mkdir(parents=True)
    (rdir / "SPEC.md").write_text(
        "# SPEC — Release: 1.0.0\n\n**Status:** Approved\n", encoding="utf-8"
    )
    (rdir / "PLAN.md").write_text("# PLAN\n\n**Status:** Approved\n", encoding="utf-8")
    (rdir / "TASKS.md").write_text("# TASKS\n\n**Status:** Approved\n", encoding="utf-8")
    state = {
        "schema": "release-state-v1",
        "release": "1.0.0",
        "phase": "IMPLEMENTATION",
        "rc": None,
        "defined": None,
        "implemented": None,
        "shipped": None,
        "log": [],
    }
    name = "RELEASE.json" if legacy_name else "_RELEASE.json"
    (rdir / name).write_text(json.dumps(state), encoding="utf-8")
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    return specs


def test_legacy_filename_emits_fixable_spec_doc_046(tmp_path: Path) -> None:
    specs = _specs_with_release(tmp_path, legacy_name=True)
    doctor = SpecsDoctor(specs)
    issues = [i for i in doctor.check() if i.code == "SPEC-DOC-046"]
    assert issues and issues[0].fixable
    doctor.fix(issues)
    rdir = specs / "releases" / "1.0.0"
    assert (rdir / "_RELEASE.json").is_file()
    assert not (rdir / "RELEASE.json").exists()
    assert not [i for i in doctor.check() if i.code == "SPEC-DOC-046"]


def test_canonical_filename_emits_nothing(tmp_path: Path) -> None:
    specs = _specs_with_release(tmp_path, legacy_name=False)
    issues = [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-046"]
    assert issues == []
