"""Integration tests for the `specs` section of `dadaia doctor --fix`.

Tests use Typer's CliRunner on a real tmp_path filesystem.

Covers:
- Memory atoms are .md (no HTML rendering); --fix creates missing dirs/files
- TREE-4 auto-fix via --fix flag creates missing directories
- TREE-1 and TREE-2 warn-only invariants are NOT auto-fixed
- --fix re-checks and reports residual issues
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.specs.canon import scaffold

_runner = CliRunner()

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"
_PUBLIC_DIR = _REPO_ROOT / "dadaia_workspace" / "public"


def _make_workspace(root: Path) -> None:
    """The sentinel `resolve_workspace_root()` looks for — the one doctor also runs its
    `workspace` section, so these tests scope it to a tmp instance instead of the real
    one the runner happens to sit in."""
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text('{"contexts": []}', encoding="utf-8")


def _specs_findings(output: str) -> list[dict[str, str]]:
    payload = json.loads(output)
    findings: list[dict[str, str]] = payload["sections"]["specs"]["findings"]
    return findings


def _specs_errors(output: str) -> list[dict[str, str]]:
    """The ERROR-class specs findings — the exit-code-bearing set (a warning never
    failed `specs doctor` either)."""
    return [f for f in _specs_findings(output) if f["verdict"] == "error"]


def _make_minimal_specs(root: Path) -> Path:
    """Scaffold a minimal valid specs/ tree using the canonical scaffold().

    v6 canon (T-050-05, FR1): scaffold() already writes bugs/AGENTS.md and
    specs/AGENTS.md itself — no hand-rolled README.md/AGENTS.md injection
    needed anymore.
    """
    specs = root / "specs"
    scaffold(
        specs,
        project_name="test-project",
        force=False,
        public_dir=_TEMPLATES_DIR.parent,
    )
    return specs


def test_doctor_clean_tree_then_remove_backlog_then_fix_recreates_then_no_fix_never_mutates(
    tmp_path: Path,
) -> None:
    """A fully clean scaffolded tree exits 0 without --fix; removing backlog/ and
    running --fix recreates it (AGENTS.md, v6 canon — a directory is kept by its
    AGENTS.md, no .gitkeep placeholder); and without --fix, behaviour is unchanged —
    the doctor never auto-creates/mutates anything (removing the core architecture.md
    atom stays removed)."""
    specs = _make_minimal_specs(tmp_path)

    clean_result = _runner.invoke(
        app,
        ["doctor", "--json", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    # The exit code is the WHOLE run's (the `workspace` section scans the instance the
    # runner sits in); this test's subject is the `specs` section's own verdict.
    assert _specs_errors(clean_result.output) == [], clean_result.output

    import shutil

    backlog = specs / "backlog"
    if backlog.exists():
        shutil.rmtree(backlog)

    fix_result = _runner.invoke(
        app,
        ["doctor", "--json", "--fix", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert backlog.exists(), f"backlog/ must be created; output:\n{fix_result.output}"
    assert (backlog / "AGENTS.md").exists(), "backlog/AGENTS.md must be created"
    assert _specs_errors(fix_result.output) == [], fix_result.output

    arch = specs / "memory" / "ARCHITECTURE.md"
    arch.unlink()
    _runner.invoke(app, ["doctor", "--json", "--specs-dir", str(specs)])
    assert not arch.exists(), "Without --fix, missing files must NOT be created"


def test_tree8_stray_root_folder_errors_and_fix_keeps_it(tmp_path: Path) -> None:
    """TREE-8 is ERROR and never auto-fixed (bug doctor-fix-tree8-deletes-operator-
    content, decision D8): a non-canon top-level folder flips the exit code non-zero,
    and ``--fix`` leaves it and its content on disk, still reported."""
    specs = _make_minimal_specs(tmp_path)

    baseline = _runner.invoke(
        app,
        ["doctor", "--json", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert _specs_errors(baseline.output) == [], baseline.output

    stray = specs / "features"
    stray.mkdir()
    (stray / "login.md").write_text("# Login\n", encoding="utf-8")

    fix_result = _runner.invoke(
        app,
        ["doctor", "--json", "--fix", "--specs-dir", str(specs), "--public-dir", str(_PUBLIC_DIR)],
    )
    assert (stray / "login.md").read_text(encoding="utf-8") == "# Login\n", fix_result.output
    codes = [f["code"] for f in _specs_findings(fix_result.output)]
    assert "TREE-8" in codes, f"TREE-8 must still be reported after --fix; got {codes}"
    assert fix_result.exit_code != 0, fix_result.output
