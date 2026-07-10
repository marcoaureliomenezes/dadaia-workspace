"""ACTIVE.md schema v2 reader — optional `segment:` field (T-ENG-01, ADR-1/ADR-5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.doctor_common import read_active_md as _read_active_md


def _write(p: Path, body: str) -> Path:
    f = p / "ACTIVE.md"
    f.write_text(body, encoding="utf-8")
    return f


@pytest.mark.parametrize(
    ("body", "expect_missing_file", "expected"),
    [
        pytest.param(
            "release: v0.1.5\nphase: IMPLEMENTATION\n",
            False,
            ("v0.1.5", None, "IMPLEMENTATION", None),
            id="flat-no-segment",
        ),
        pytest.param(
            "release: v0.1.6\nsegment: alpha-2\nphase: TASKS\n",
            False,
            ("v0.1.6", "alpha-2", "TASKS", None),
            id="segmented-parses-segment",
        ),
        pytest.param(
            "release: v0.1.6\nsegment: none\nphase: SPEC\n",
            False,
            ("v0.1.6", None, "SPEC", None),
            id="segment-none-treated-as-absent",
        ),
        pytest.param(None, True, (None, None, None, "ACTIVE.md not found"), id="missing-file"),
        pytest.param(
            "segment: rc-1\n",
            False,
            ("rc-1-marker", None, None, None),  # sentinel: checked specially below
            id="missing-release-or-phase-still-errors",
        ),
    ],
)
def test_active_md_schema_v2_matrix(
    tmp_path: Path,
    body: str | None,
    expect_missing_file: bool,
    expected: tuple[str | None, str | None, str | None, str | None],
) -> None:
    if expect_missing_file:
        release, segment, phase, err = _read_active_md(tmp_path / "ACTIVE.md")
        assert release is None and segment is None and phase is None
        assert err == "ACTIVE.md not found"
        return

    f = _write(tmp_path, body)  # type: ignore[arg-type]
    release, segment, phase, err = _read_active_md(f)

    if expected[0] == "rc-1-marker":
        assert segment == "rc-1"
        assert err is not None and "missing" in err
        return

    assert (release, segment, phase, err) == expected
