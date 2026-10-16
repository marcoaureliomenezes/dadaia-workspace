"""One writer answers "how a fixed section is written": ``core.atomic_write`` refuses a
symlinked destination, ``specs upgrade`` refuses the path with its fix line and
leaves the outside file's bytes unchanged, ``doctor --fix`` refuses identically.
Size: SMALL (tmp_path, CliRunner in-process, no subprocess).
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.atomic_write import SymlinkRefusedError, atomic_write
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.gitflow import merge_frontmatter
from dadaia_workspace.features.migrate.upgrade import (
    fold_tech_stack,
    upgrade,
)
from dadaia_workspace.features.spec_context import sweep
from dadaia_workspace.features.specs import SpecsDoctor, canon
from tests.helpers.oslib import command, read_text, write_text
from tests.helpers.oslib import link as make_link

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_OUTSIDE = (  # a valid atom: the only error left is the refused symlink
    "---\nslug: QUALITY\ntitle: Quality\ntldr: Quality.\nsummary: Quality.\ntags:\n  - quality\n---\n"
    "# Quality\n\noperator text, no fixed block\n"
)


def _materialize(link: Path, target: Path) -> str:
    """The literal fix: one interpreter line, the same on every OS ."""
    code = (
        "import os, shutil, sys; os.remove(sys.argv[1]); shutil.copyfile(sys.argv[2], sys.argv[1])"
    )
    return command(sys.executable, "-c", code, str(link), str(target))


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()  # noqa: S324 — identity, not security


def _tree_with_linked_quality(tmp_path: Path) -> tuple[Path, Path]:
    specs = tmp_path / "repo" / "specs"
    canon.scaffold(specs, project_name="p")
    outside = tmp_path / "outside.md"
    write_text(outside, _OUTSIDE)
    quality = specs / "memory" / "QUALITY.md"
    quality.unlink()
    assert make_link(str(outside), quality, is_dir=False)
    return specs, outside


def test_b4_the_one_writer_refuses_a_symlinked_destination(tmp_path: Path) -> None:
    """The one writer never replaces or writes through a link."""
    outside = tmp_path / "outside.md"
    write_text(outside, "keep\n")
    link = tmp_path / "link.md"
    assert make_link(str(outside), link, is_dir=False)

    with pytest.raises(SymlinkRefusedError) as info:
        atomic_write(link, "new\n")

    assert link.is_symlink()
    assert read_text(outside) == "keep\n"
    assert str(info.value) == f"{link} is a symlink; refusing to write it"
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


@pytest.mark.medium
def test_b1_specs_upgrade_refuses_a_symlinked_quality_md_with_its_fix(tmp_path: Path) -> None:
    """`specs upgrade` repairs through the doctor's writer, which refuses the link:
    the verb exits non-zero naming the path with its fix line; the outside md5 is
    unchanged and the link stays a link."""
    specs, outside = _tree_with_linked_quality(tmp_path)
    before = _md5(outside)

    result = CliRunner().invoke(app, ["specs", "upgrade", "--specs-dir", str(specs)])

    assert result.exit_code == 1, result.output
    link = specs / "memory" / "QUALITY.md"
    assert f"[refused] FIXED-1 {link}" in result.output
    (fix,) = [ln[len("fix: ") :] for ln in result.output.splitlines() if ln.startswith("fix: ")]
    assert fix == _materialize(link, outside)
    assert _md5(outside) == before
    assert (specs / "memory" / "QUALITY.md").is_symlink()
    doctor = SpecsDoctor(specs, public_dir=_PUBLIC, templates_dir=_PUBLIC / "templates")
    quality = [i for i in doctor.check() if i.code.startswith("FIXED")]
    assert [(i.code, i.fixable, i.fix) for i in quality] == [
        ("FIXED-1", False, _materialize(link, outside))
    ]


def _v6_tree_linking(tmp_path: Path, linked: str) -> tuple[Path, Path]:
    """A v6 tree holding TECHSTACK.md whose *linked* entry is moved outside and symlinked back;
    returns the specs dir and the outside ARCHITECTURE.md."""
    specs = tmp_path / "repo" / "specs"
    canon.scaffold(specs, project_name="p")
    merge_frontmatter(specs, specs_pattern_version=6)
    write_text(specs / "memory" / "ARCHITECTURE.md", "# Architecture\n")
    write_text(specs / "memory" / "TECHSTACK.md", "# Tech\n\npython\n")
    outside = tmp_path / "outside"
    (specs / linked).rename(outside)
    assert make_link(str(outside), specs / linked, is_dir=False)
    return specs, outside / "ARCHITECTURE.md" if outside.is_dir() else outside


def test_b1_the_tech_stack_fold_refuses_a_symlinked_architecture_md(tmp_path: Path) -> None:
    """The 6 -> 7 fold writes ARCHITECTURE.md through the same writer."""
    specs, arch = _v6_tree_linking(tmp_path, "memory/ARCHITECTURE.md")

    with pytest.raises(SymlinkRefusedError):
        upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name))

    assert read_text(arch) == "# Architecture\n"


def test_a_fold_whose_delete_does_not_succeed_restores_architecture_md(tmp_path: Path) -> None:
    """A TECHSTACK.md the deleter refuses (memory/
    linked outside specs) or fails on is never reported folded and ARCHITECTURE.md is restored,
    so a re-run never appends a second ``## Tech Stack``."""
    specs, arch = _v6_tree_linking(tmp_path, "memory")

    def boom(path: Path) -> bool:
        raise OSError(13, "Permission denied")

    assert upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name)).tech_stack_folded == []
    assert upgrade(specs, remove=lambda p: sweep.remove(specs, p, p.name)).tech_stack_folded == []
    with pytest.raises(OSError, match="Permission denied"):
        fold_tech_stack(specs, boom)

    assert read_text(arch) == "# Architecture\n"


def test_b2_doctor_fix_leaves_a_symlinked_quality_md_a_link(tmp_path: Path) -> None:
    """`doctor --fix` neither replaces the link nor writes its target."""
    specs, outside = _tree_with_linked_quality(tmp_path)
    before = _md5(outside)
    doctor = SpecsDoctor(specs, public_dir=_PUBLIC, templates_dir=_PUBLIC / "templates")

    doctor.fix(doctor.check())

    assert (specs / "memory" / "QUALITY.md").is_symlink()
    assert _md5(outside) == before


def test_the_two_tier_refusal_renders_the_cli_words_inline(
    tmp_path: Path, sentence: Callable[..., str]
) -> None:
    specs = tmp_path / "specs"
    canon.scaffold(specs, project_name="p")
    merge_frontmatter(specs, specs_pattern_version=6)
    write_text(
        specs / "memory" / "ARCHITECTURE.md",
        "# A\n\n## Part 1 — Principles\n",
    )

    with pytest.raises(DadaiaError) as refused:
        upgrade(specs, remove=lambda _path: None)

    rerun = sentence("specs", "upgrade", "--specs-dir", str(specs))
    assert f"then re-run `{rerun}`." in refused.value.fix  # type: ignore[attr-defined]
