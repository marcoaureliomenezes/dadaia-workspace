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
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"


def _make_minimal_specs(root: Path) -> Path:
    """Scaffold a minimal valid specs/ tree using the canonical scaffold().

    v6 canon (T-050-05, FR1): scaffold() already writes bugs/AGENTS.md,
    bugs/_archive/.gitkeep and specs/AGENTS.md itself — no hand-rolled
    README.md/AGENTS.md injection needed anymore.
    """
    specs = root / "specs"
    result = scaffold(
        specs_dir=specs,
        project_name="test-project",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], f"Scaffold errors: {result.errors}"
    return specs


def test_doctor_clean_tree_then_remove_backlog_then_fix_recreates_then_no_fix_never_mutates(
    tmp_path: Path,
) -> None:
    """A fully clean scaffolded tree exits 0 without --fix; removing backlog/ and
    running --fix recreates it (AGENTS.md + .gitkeep, v6 canon); and without --fix,
    behaviour is unchanged — the doctor never auto-creates/mutates anything (removing
    the core architecture.md atom stays removed)."""
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
    assert (backlog / "AGENTS.md").exists(), "backlog/AGENTS.md must be created"
    assert (backlog / ".gitkeep").exists(), "backlog/.gitkeep must be created"
    assert fix_result.exit_code == 0, (
        f"Expected exit 0; got {fix_result.exit_code}:\n{fix_result.output}"
    )

    arch = specs / "memory" / "architecture.md"
    arch.unlink()
    _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(specs)])
    assert not arch.exists(), "Without --fix, missing files must NOT be created"


def test_tree8_stray_root_folder_warns_but_exit_code_stays_unchanged(tmp_path: Path) -> None:
    """A1.2 exit-code fixture: TREE-8 compliance is WARN-only (D15) — a stray,
    non-canon top-level folder under specs/ is reported, but never flips exit code
    away from what the rest of the tree would already produce."""
    specs = _make_minimal_specs(tmp_path)

    baseline = _runner.invoke(
        app,
        ["specs", "doctor", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert baseline.exit_code == 0, f"Expected exit 0; got {baseline.exit_code}:\n{baseline.output}"

    (specs / "scratch-legacy-folder").mkdir()

    stray_result = _runner.invoke(
        app,
        ["specs", "doctor", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert "TREE-8" in stray_result.output, (
        f"Expected TREE-8 to fire on the stray folder; output:\n{stray_result.output}"
    )
    assert stray_result.exit_code == baseline.exit_code == 0, (
        "TREE-8 WARNING must never change the exit code (D15, A1.2) — got "
        f"{stray_result.exit_code}:\n{stray_result.output}"
    )
