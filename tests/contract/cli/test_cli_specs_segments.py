"""CLI contracts for `dadaia specs release open` + `segment open` (T-ENG-03, ADR-5)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def _specs(tmp_path: Path) -> Path:
    s = tmp_path / "specs"
    (s / "releases").mkdir(parents=True)
    return s


def test_release_open_then_segment_open_advances_active(tmp_path: Path) -> None:
    specs = _specs(tmp_path)
    res = _runner.invoke(app, ["specs", "release", "open", "v0.1.6", "--specs-dir", str(specs)])
    assert res.exit_code == 0, res.output
    seg = specs / "releases" / "v0.1.6" / "alpha-1"
    assert (seg / "SPEC.md").is_file()
    assert (seg / "PLAN.md").is_file()
    assert (seg / "TASKS.md").is_file()
    active = (specs / "releases" / "ACTIVE.md").read_text()
    assert "release: v0.1.6" in active
    assert "segment: alpha-1" in active
    assert "phase: SPEC" in active

    res = _runner.invoke(app, ["specs", "segment", "open", "rc-1", "--specs-dir", str(specs)])
    assert res.exit_code == 0, res.output
    assert (specs / "releases" / "v0.1.6" / "rc-1" / "TASKS.md").is_file()
    active = (specs / "releases" / "ACTIVE.md").read_text()
    assert "segment: rc-1" in active


@pytest.mark.parametrize(
    "setup_and_invoke",
    ["bad-version", "bad-segment", "no-active-release"],
)
def test_specs_segment_error_matrix(tmp_path: Path, setup_and_invoke: str) -> None:
    specs = _specs(tmp_path)
    if setup_and_invoke == "bad-version":
        res = _runner.invoke(app, ["specs", "release", "open", "0.1.6", "--specs-dir", str(specs)])
    elif setup_and_invoke == "bad-segment":
        _runner.invoke(app, ["specs", "release", "open", "v0.1.6", "--specs-dir", str(specs)])
        res = _runner.invoke(app, ["specs", "segment", "open", "beta-1", "--specs-dir", str(specs)])
    else:
        (specs / "releases" / "ACTIVE.md").write_text(
            "release: none\nphase: none\n", encoding="utf-8"
        )
        res = _runner.invoke(
            app, ["specs", "segment", "open", "alpha-2", "--specs-dir", str(specs)]
        )
    assert res.exit_code == 2


def test_reopening_an_existing_release_is_refused(tmp_path: Path) -> None:
    """`open` creates. Re-running it on a live release silently rewound ACTIVE.md's
    phase (IMPLEMENTATION -> SPEC) while reporting `[ok]` — a state regression with no
    trace. The verb must refuse and name the verb that advances a release instead."""
    specs = _specs(tmp_path)
    assert _runner.invoke(app, ["specs", "release", "open", "v0.1.6", "--specs-dir", str(specs)]).exit_code == 0
    active = specs / "releases" / "ACTIVE.md"
    active.write_text(active.read_text().replace("phase: SPEC", "phase: IMPLEMENTATION"))

    res = _runner.invoke(app, ["specs", "release", "open", "v0.1.6", "--specs-dir", str(specs)])

    assert res.exit_code != 0, res.output
    assert "phase: IMPLEMENTATION" in active.read_text(), "a refusal must not rewind the phase"
    assert "segment open" in res.output, "the refusal must name the verb that advances a release"
    assert "Traceback" not in res.output


def test_force_still_reopens_deliberately(tmp_path: Path) -> None:
    """`--force` is the documented escape hatch and must keep working."""
    specs = _specs(tmp_path)
    _runner.invoke(app, ["specs", "release", "open", "v0.1.6", "--specs-dir", str(specs)])

    res = _runner.invoke(
        app, ["specs", "release", "open", "v0.1.6", "--specs-dir", str(specs), "--force"]
    )

    assert res.exit_code == 0, res.output
    assert "phase: SPEC" in (specs / "releases" / "ACTIVE.md").read_text()
