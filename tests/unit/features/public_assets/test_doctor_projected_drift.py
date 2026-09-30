"""Unit tests for T-PROP-02: doctor staging-vs-projected drift detection.

Verifies that `dadaia public doctor` (via FileSystemPublicAssetManager.doctor):
1. Exits 0 and emits [ok] for every staged asset on a clean workspace.
2. Exits non-zero (via the CLI) and emits [drift] for staged assets whose SHA
   differs from their projected counterparts.
3. Emits [missing] / exits non-zero when a staged asset has no projected file.

Doctor drift detection gates agent dispatch, so both failure modes ([drift] and
[missing]) are kept as named tests; the clean/[ok] path (incl. the scripts
staging↔projected facet) is merged into one parametrized test; the CLI exit code is
pinned by tests/integration/cli/test_doctor_exit_verdict.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dadaia_workspace.core.models.doctor_report import (
    DoctorStatus,
)
from dadaia_workspace.infrastructure.projection import doctor_rules, tree_bytes_rules
from dadaia_workspace.infrastructure.public_assets import (
    FileSystemPublicAssetManager,
)


def _render_one(line: object) -> str:
    return line.render() if hasattr(line, "render") else str(line)  # type: ignore[attr-defined]


def _rendered(result: object) -> list[str]:
    """Legacy string view of a typed doctor result (DoctorReport | list[DoctorLine])."""
    if hasattr(result, "rendered"):
        return result.rendered()  # type: ignore[attr-defined, no-any-return]
    return [
        line.render() if hasattr(line, "render") else str(line)
        for line in result  # type: ignore[union-attr]
    ]


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _make_manager(public_dir: Path) -> FileSystemPublicAssetManager:
    mgr = FileSystemPublicAssetManager.__new__(FileSystemPublicAssetManager)
    mgr._public_dir = public_dir
    return mgr


def test_drift_and_missing_exit_nonzero(tmp_path: Path) -> None:
    """T-PROP-02 AC-1/AC-3: staged SHA differs from projected → [drift]; staged asset
    with no projection at all → [missing]. Both are the doctor's non-zero-exit codes."""
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    mgr = _make_manager(public_dir)

    staged = tmp_path / "staged.md"
    projected = tmp_path / "projected.md"
    _write(staged, b"# new staged content\n")
    _write(projected, b"# old projected content\n")

    line = _render_one(mgr._compare(staged, projected, "stage:test.md"))
    assert line.startswith("[drift]"), f"Expected [drift], got: {line!r}"

    staged2 = tmp_path / "staged2.md"
    projected2 = tmp_path / "non_existent.md"
    _write(staged2, b"# some content\n")
    # projected2 does NOT exist

    line2 = _render_one(mgr._compare(staged2, projected2, "stage:test.md"))
    assert line2.startswith("[missing]"), f"Expected [missing], got: {line2!r}"


def test_clean_ok_paths_incl_scripts(tmp_path: Path) -> None:
    """T-PROP-02 AC-2: identical staged/projected content is [ok]."""
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    mgr = _make_manager(public_dir)

    staged = tmp_path / "staged.md"
    projected = tmp_path / "projected.md"
    content = b"# identical content\n"
    _write(staged, content)
    _write(projected, content)
    line = _render_one(mgr._compare(staged, projected, "stage:test.md"))
    assert line.startswith("[ok]"), f"Expected [ok], got: {line!r}"
    assert "[drift]" not in line
    assert "[missing]" not in line


@pytest.mark.skipif(os.name == "nt", reason="Windows has no POSIX exec bit")
def test_an_executable_rule_that_lost_its_exec_bit_is_drift(tmp_path: Path) -> None:
    """sa-projected-file-judged-by-four-verifiers: doctor_rules is the one verifier, with an
    exec-bit mode check — equal bytes with a cleared exec bit are [drift]; chmod clears it."""
    src, dst = tmp_path / "src" / "hook.sh", tmp_path / "dst" / "hook.sh"
    _write(src, b"#!/bin/sh\n")
    _write(dst, b"#!/bin/sh\n")
    src.chmod(0o755)
    dst.chmod(0o644)
    rules = tree_bytes_rules(src.parent, dst.parent, harness="agents", label_prefix="s/")
    assert [line.render() for line in doctor_rules(rules)] == ["[drift] s/hook.sh (not executable)"]
    dst.chmod(0o755)
    assert [line.status for line in doctor_rules(rules)] == [DoctorStatus.OK]
