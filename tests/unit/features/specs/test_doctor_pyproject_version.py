"""SPEC-DOC-045: pyproject.toml's [tool.poetry].version must equal the active
release id once that release reaches CLOSURE (or later).

Bug: release-shipped-without-a-pyproject-version-bump — main shipped 0.5.1 while
pyproject.toml still minted 0.5.0; nothing in definition, doctor, or the ship gate
tied the release id to the package version. This is the deterministic closure-
boundary check that closes that gap.

Intent: CONTRACT — bug release-shipped-without-a-pyproject-version-bump
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.features.specs import Severity, SpecsDoctor


def _write_release(specs_dir: Path, release_id: str, phase: str) -> None:
    rdir = specs_dir / "releases" / release_id
    rdir.mkdir(parents=True, exist_ok=True)
    state = {
        "schema": "release-state-v1",
        "release": release_id,
        "phase": phase,
        "rc": None,
        "defined": None,
        "implemented": None,
        "shipped": None,
        "audited": None,
        "log": [],
    }
    (rdir / "RELEASE.json").write_text(json.dumps(state) + "\n", encoding="utf-8")


def _write_pyproject(repo_root: Path, version: str) -> None:
    (repo_root / "pyproject.toml").write_text(
        f'[tool.poetry]\nname = "dadaia-workspace"\nversion = "{version}"\n',
        encoding="utf-8",
    )


def test_mismatched_pyproject_version_is_an_error_at_closure(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_release(specs, "0.5.1", "CLOSURE")
    _write_pyproject(tmp_path, "0.5.0")

    issues = SpecsDoctor(specs, repo_root=tmp_path).check()
    hits = [i for i in issues if i.code == "SPEC-DOC-045"]
    assert len(hits) == 1
    assert hits[0].severity == Severity.ERROR
    assert "0.5.0" in hits[0].description
    assert "0.5.1" in hits[0].description


def test_mismatched_pyproject_version_is_an_error_when_archived(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_release(specs, "0.5.1", "ARCHIVED")
    _write_pyproject(tmp_path, "0.5.0")

    issues = SpecsDoctor(specs, repo_root=tmp_path).check()
    assert [i for i in issues if i.code == "SPEC-DOC-045"]


def test_matching_pyproject_version_is_silent(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_release(specs, "0.5.1", "CLOSURE")
    _write_pyproject(tmp_path, "0.5.1")

    issues = SpecsDoctor(specs, repo_root=tmp_path).check()
    assert [i for i in issues if i.code == "SPEC-DOC-045"] == []


def test_pre_closure_phase_is_silent_even_when_mismatched(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_release(specs, "0.5.1", "IMPLEMENTATION")
    _write_pyproject(tmp_path, "0.5.0")

    issues = SpecsDoctor(specs, repo_root=tmp_path).check()
    assert [i for i in issues if i.code == "SPEC-DOC-045"] == []


def test_no_pyproject_toml_is_silent(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    _write_release(specs, "0.5.1", "CLOSURE")
    # no pyproject.toml written at repo_root

    issues = SpecsDoctor(specs, repo_root=tmp_path).check()
    assert [i for i in issues if i.code == "SPEC-DOC-045"] == []


def test_no_repo_root_is_silent_never_guesses(tmp_path: Path) -> None:
    """Mirrors SPEC-DOC-028/044's optional-repo_root shape: this check genuinely
    cannot evaluate without a resolved repo root, so it stays silent rather than
    guessing."""
    specs = tmp_path / "specs"
    _write_release(specs, "0.5.1", "CLOSURE")
    _write_pyproject(tmp_path, "0.5.0")

    issues = SpecsDoctor(specs).check()  # no repo_root passed
    assert [i for i in issues if i.code == "SPEC-DOC-045"] == []


def test_no_active_release_is_silent(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "releases").mkdir(parents=True)
    _write_pyproject(tmp_path, "0.5.0")

    issues = SpecsDoctor(specs, repo_root=tmp_path).check()
    assert [i for i in issues if i.code == "SPEC-DOC-045"] == []
