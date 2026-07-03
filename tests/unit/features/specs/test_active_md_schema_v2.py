"""ACTIVE.md schema v2 reader — optional `segment:` field (T-ENG-01, ADR-1/ADR-5)."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs.doctor_common import read_active_md as _read_active_md


def _write(p: Path, body: str) -> Path:
    f = p / "ACTIVE.md"
    f.write_text(body, encoding="utf-8")
    return f


def test_flat_active_md_has_no_segment(tmp_path: Path) -> None:
    f = _write(tmp_path, "release: v0.1.5\nphase: IMPLEMENTATION\n")
    release, segment, phase, err = _read_active_md(f)
    assert (release, segment, phase, err) == ("v0.1.5", None, "IMPLEMENTATION", None)


def test_segmented_active_md_parses_segment(tmp_path: Path) -> None:
    f = _write(tmp_path, "release: v0.1.6\nsegment: alpha-2\nphase: TASKS\n")
    release, segment, phase, err = _read_active_md(f)
    assert (release, segment, phase, err) == ("v0.1.6", "alpha-2", "TASKS", None)


def test_segment_none_is_treated_as_absent(tmp_path: Path) -> None:
    f = _write(tmp_path, "release: v0.1.6\nsegment: none\nphase: SPEC\n")
    _, segment, _, err = _read_active_md(f)
    assert segment is None
    assert err is None


def test_missing_file(tmp_path: Path) -> None:
    release, segment, phase, err = _read_active_md(tmp_path / "ACTIVE.md")
    assert release is None and segment is None and phase is None
    assert err == "ACTIVE.md not found"


def test_missing_release_or_phase_still_errors(tmp_path: Path) -> None:
    f = _write(tmp_path, "segment: rc-1\n")
    release, segment, phase, err = _read_active_md(f)
    assert segment == "rc-1"
    assert err is not None and "missing" in err
