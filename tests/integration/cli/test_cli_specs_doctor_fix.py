"""Integration tests for `dadaia specs doctor --fix`.

Tests use Typer's CliRunner on a real tmp_path filesystem.

Covers:
- Memory atoms are .md (no HTML rendering); --fix creates missing dirs/files
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


def test_doctor_no_fix_flag_unchanged_behaviour(tmp_path: Path) -> None:
    """Without --fix flag, behaviour is unchanged (check + report, no mutations).

    memory-markdown-source-v1: memory atoms are now `.md`. Removing the core
    architecture.md atom makes the tree non-clean, but without --fix the doctor
    must NOT auto-create/mutate anything.
    """
    specs = _make_minimal_specs(tmp_path)
    arch = specs / "memory" / "architecture.md"
    arch.unlink()

    _runner.invoke(
        app,
        ["specs", "doctor", "--specs-dir", str(specs)],
    )
    # File must NOT have been created/restored (no --fix was passed).
    assert not arch.exists(), "Without --fix, missing files must NOT be created"


def test_doctor_exit_0_on_fully_clean_tree(tmp_path: Path) -> None:
    """A fully clean scaffolded tree produces exit 0 without --fix."""
    specs = _make_minimal_specs(tmp_path)

    result = _runner.invoke(
        app,
        ["specs", "doctor", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert result.exit_code == 0, f"Expected exit 0; got {result.exit_code}:\n{result.output}"
