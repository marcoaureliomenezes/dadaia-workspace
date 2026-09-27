"""Intent: CONTRACT — sa-specs-upgrade-writes-through-symlinks (0.5.0 WP-14, AC1.2).

One writer answers "how a fixed section is written": ``core.atomic_write`` refuses a
symlinked destination (sa-specs-upgrade-writes-through-symlinks#B4), ``specs upgrade`` refuses the path with its fix line and
leaves the outside file's bytes unchanged (sa-specs-upgrade-writes-through-symlinks#B1), ``doctor --fix`` refuses identically (sa-specs-upgrade-writes-through-symlinks#B2).
Size: SMALL (tmp_path, CliRunner in-process, no subprocess).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.atomic_write import SymlinkRefusedError, atomic_write
from dadaia_workspace.core.gitflow import merge_frontmatter
from dadaia_workspace.features.migrate.upgrade import upgrade
from dadaia_workspace.features.specs import SpecsDoctor, canon

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public"
_OUTSIDE = "# Quality\n\noperator text, no fixed block\n"


def _materialize(link: Path, target: Path) -> str:
    """The literal fix per host shell: POSIX sh, Windows cmd."""
    if os.name == "nt":
        return f'del "{link}" && copy /Y "{target}" "{link}"'
    return f"cp --remove-destination -- {target} {link}"


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()  # noqa: S324 — identity, not security


def _tree_with_linked_quality(tmp_path: Path) -> tuple[Path, Path]:
    specs = tmp_path / "repo" / "specs"
    canon.scaffold(specs, project_name="p")
    outside = tmp_path / "outside.md"
    outside.write_text(_OUTSIDE, encoding="utf-8")
    quality = specs / "memory" / "QUALITY.md"
    quality.unlink()
    quality.symlink_to(outside)
    return specs, outside


def test_b4_the_one_writer_refuses_a_symlinked_destination(tmp_path: Path) -> None:
    """#B4: the one writer never replaces or writes through a link."""
    outside = tmp_path / "outside.md"
    outside.write_text("keep\n", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to(outside)

    with pytest.raises(SymlinkRefusedError) as info:
        atomic_write(link, "new\n")

    assert link.is_symlink()
    assert outside.read_text(encoding="utf-8") == "keep\n"
    assert str(info.value) == f"{link} is a symlink; refusing to write it"
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_b1_specs_upgrade_refuses_a_symlinked_quality_md_with_its_fix(tmp_path: Path) -> None:
    """#B1: `specs upgrade` repairs through the doctor's writer, which refuses the link:
    the verb exits non-zero naming the path with its fix line; the outside md5 is
    unchanged and the link stays a link."""
    specs, outside = _tree_with_linked_quality(tmp_path)
    before = _md5(outside)

    result = CliRunner().invoke(app, ["specs", "upgrade", "--specs-dir", str(specs)])

    assert result.exit_code == 1, result.output
    link = specs / "memory" / "QUALITY.md"
    assert f"[refused] FIXED-1 {link}" in result.output
    assert f"fix: {_materialize(link, outside)}" in result.output
    assert _md5(outside) == before
    assert (specs / "memory" / "QUALITY.md").is_symlink()
    doctor = SpecsDoctor(specs, public_dir=_PUBLIC, templates_dir=_PUBLIC / "templates")
    quality = [i for i in doctor.check() if i.code.startswith("FIXED")]
    assert [(i.code, i.fixable, i.fix) for i in quality] == [
        ("FIXED-1", False, _materialize(link, outside))
    ]


def test_b1_the_tech_stack_fold_refuses_a_symlinked_architecture_md(tmp_path: Path) -> None:
    """#B1: the 6 -> 7 fold writes ARCHITECTURE.md through the same writer."""
    specs = tmp_path / "repo" / "specs"
    canon.scaffold(specs, project_name="p")
    merge_frontmatter(specs, specs_pattern_version=6)
    outside = tmp_path / "arch.md"
    outside.write_text("# Architecture\n", encoding="utf-8")
    arch = specs / "memory" / "ARCHITECTURE.md"
    arch.unlink()
    arch.symlink_to(outside)
    (specs / "memory" / "TECHSTACK.md").write_text("# Tech\n\npython\n", encoding="utf-8")

    with pytest.raises(SymlinkRefusedError):
        upgrade(specs)

    assert outside.read_text(encoding="utf-8") == "# Architecture\n"


def test_b2_doctor_fix_leaves_a_symlinked_quality_md_a_link(tmp_path: Path) -> None:
    """#B2: `doctor --fix` neither replaces the link nor writes its target."""
    specs, outside = _tree_with_linked_quality(tmp_path)
    before = _md5(outside)
    doctor = SpecsDoctor(specs, public_dir=_PUBLIC, templates_dir=_PUBLIC / "templates")

    doctor.fix(doctor.check())

    assert (specs / "memory" / "QUALITY.md").is_symlink()
    assert _md5(outside) == before
