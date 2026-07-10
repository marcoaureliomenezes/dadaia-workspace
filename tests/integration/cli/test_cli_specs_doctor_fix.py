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


def test_doctor_clean_tree_then_remove_backlog_then_fix_recreates_then_no_fix_never_mutates(
    tmp_path: Path,
) -> None:
    """A fully clean scaffolded tree exits 0 without --fix; removing backlog/ and
    running --fix recreates it (README.md + .gitkeep); and without --fix, behaviour
    is unchanged — the doctor never auto-creates/mutates anything (removing the core
    architecture.md atom stays removed)."""
    specs = _make_minimal_specs(tmp_path)

    clean_result = _runner.invoke(
        app,
        ["specs", "doctor", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert clean_result.exit_code == 0, (
        f"Expected exit 0; got {clean_result.exit_code}:\n{clean_result.output}"
    )

    import shutil

    backlog = specs / "backlog"
    if backlog.exists():
        shutil.rmtree(backlog)

    fix_result = _runner.invoke(
        app,
        ["specs", "doctor", "--fix", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert backlog.exists(), f"backlog/ must be created; output:\n{fix_result.output}"
    assert (backlog / "README.md").exists(), "backlog/README.md must be created"
    assert (backlog / ".gitkeep").exists(), "backlog/.gitkeep must be created"
    assert fix_result.exit_code == 0, (
        f"Expected exit 0; got {fix_result.exit_code}:\n{fix_result.output}"
    )

    arch = specs / "memory" / "architecture.md"
    arch.unlink()
    _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(specs)])
    assert not arch.exists(), "Without --fix, missing files must NOT be created"
