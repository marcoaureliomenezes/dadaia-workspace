"""Integration tests for `dadaia specs doctor --fix`.

Tests use Typer's CliRunner on a real tmp_path filesystem.

Covers:
- TREE-3 auto-fix via --fix flag renders missing memory HTML
- TREE-4 auto-fix via --fix flag creates missing directories
- TREE-1 and TREE-2 warn-only invariants are NOT auto-fixed
- --fix re-checks and reports residual issues
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.specs.scaffolder import scaffold

_runner = CliRunner()

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_SCAFFOLD_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"


def _make_minimal_specs(root: Path) -> Path:
    """Scaffold a minimal valid specs/ tree using the canonical scaffold()."""
    specs = root / "specs"
    result = scaffold(
        specs_dir=specs,
        project_name="test-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], f"Scaffold errors: {result.errors}"
    # Add bugs/ dir (part of T-4 scaffold)
    bugs_dir = specs / "bugs"
    bugs_dir.mkdir(exist_ok=True)
    src_readme = _SCAFFOLD_DIR / "bugs" / "README.md"
    if src_readme.exists():
        (bugs_dir / "README.md").write_text(
            src_readme.read_text(encoding="utf-8"), encoding="utf-8"
        )
    (bugs_dir / ".gitkeep").write_text("", encoding="utf-8")
    # Add canonical AGENTS.md to suppress TREE-5 warning
    agents_template = _TEMPLATES_DIR / "specs-AGENTS.md"
    if agents_template.exists():
        (specs / "AGENTS.md").write_text(
            agents_template.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return specs


def test_doctor_fix_renders_missing_memory_html(tmp_path: Path) -> None:
    """--fix renders missing memory HTML files from canonical Jinja templates."""
    specs = _make_minimal_specs(tmp_path)
    arch = specs / "memory" / "architecture.html"
    arch.unlink()

    result = _runner.invoke(
        app,
        ["specs", "doctor", "--fix", "--specs-dir", str(specs)],
    )
    # arch.html must now exist
    assert arch.exists(), f"architecture.html must be created; output:\n{result.output}"
    # Command should exit 0 (all residual issues are warnings or fixed)
    assert result.exit_code == 0, f"Expected exit 0; got {result.exit_code}:\n{result.output}"


def test_doctor_fix_creates_missing_dirs(tmp_path: Path) -> None:
    """--fix creates missing backlog/ and bugs/ directories with README.md + .gitkeep."""
    specs = _make_minimal_specs(tmp_path)
    import shutil

    backlog = specs / "backlog"
    if backlog.exists():
        shutil.rmtree(backlog)

    result = _runner.invoke(
        app,
        ["specs", "doctor", "--fix", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert backlog.exists(), f"backlog/ must be created; output:\n{result.output}"
    assert (backlog / "README.md").exists(), "backlog/README.md must be created"
    assert (backlog / ".gitkeep").exists(), "backlog/.gitkeep must be created"
    assert result.exit_code == 0, f"Expected exit 0; got {result.exit_code}:\n{result.output}"


def test_doctor_fix_does_not_move_root_spec_md(tmp_path: Path) -> None:
    """--fix must NOT move specs/SPEC.md even though TREE-2 warns about it."""
    specs = _make_minimal_specs(tmp_path)
    root_spec = specs / "SPEC.md"
    root_spec.write_text("# Root Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")

    result = _runner.invoke(
        app,
        ["specs", "doctor", "--fix", "--specs-dir", str(specs)],
    )
    assert root_spec.exists(), "--fix must NOT remove/move specs/SPEC.md"
    # TREE-2 warning still in output (warn-only; migration hint always shown)
    assert "TREE-2" in result.output or "MIGRATION" in result.output, (
        f"TREE-2 migration hint must appear; got:\n{result.output}"
    )


def test_doctor_fix_does_not_delete_foundation(tmp_path: Path) -> None:
    """--fix must NOT delete specs/foundation/ even though TREE-1 warns about it."""
    specs = _make_minimal_specs(tmp_path)
    foundation = specs / "foundation"
    foundation.mkdir()
    (foundation / "content.md").write_text("# Protected\n", encoding="utf-8")

    result = _runner.invoke(
        app,
        ["specs", "doctor", "--fix", "--specs-dir", str(specs)],
    )
    assert foundation.exists(), "--fix must NOT delete specs/foundation/"
    assert (foundation / "content.md").exists()
    assert "TREE-1" in result.output or "MIGRATION" in result.output


def test_doctor_no_fix_flag_unchanged_behaviour(tmp_path: Path) -> None:
    """Without --fix flag, behaviour is unchanged (check + report, no mutations).

    Note: removing architecture.html triggers BOTH SPEC-DOC-002 (ERROR) and TREE-3
    (WARNING). The exit code is 1 because of the ERROR, but critically: the file must
    NOT be auto-created (no --fix was passed).
    """
    specs = _make_minimal_specs(tmp_path)
    arch = specs / "memory" / "architecture.html"
    arch.unlink()

    result = _runner.invoke(
        app,
        ["specs", "doctor", "--specs-dir", str(specs)],
    )
    # File must NOT have been created (no --fix)
    assert not arch.exists(), "Without --fix, missing files must NOT be created"
    # Should report TREE-3
    assert "TREE-3" in result.output
    # Also reports SPEC-DOC-002 which is an ERROR → exit 1
    assert result.exit_code == 1, (
        f"Expected exit 1 (SPEC-DOC-002 error for missing memory file); "
        f"got {result.exit_code}:\n{result.output}"
    )


def test_doctor_exit_0_on_fully_clean_tree(tmp_path: Path) -> None:
    """A fully clean scaffolded tree produces exit 0 without --fix."""
    specs = _make_minimal_specs(tmp_path)

    result = _runner.invoke(
        app,
        ["specs", "doctor", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert result.exit_code == 0, f"Expected exit 0; got {result.exit_code}:\n{result.output}"
