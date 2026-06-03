"""Integration tests for memory atom scaffolds and lint."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_artifacts.memory import memory_product_add

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow(reason="executes lint-memory-atoms.py against generated memory atoms"),
]


_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCAFFOLD_MEMORY = _REPO_ROOT / "dadaia_workspace" / "public" / "scaffold" / "memory"
_LINT_SCRIPT = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts" / "lint-memory-atoms.py"


def _run_lint(memory_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_LINT_SCRIPT), "--memory-dir", str(memory_dir)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_memory_product_add_generates_atom_accepted_by_lint(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()

    result = memory_product_add(specs, "my-feature")
    proc = _run_lint(specs / "memory")

    assert result.created_feature is True
    assert (specs / "memory" / "product" / "my-feature.md").is_file()
    assert proc.returncode != 1, (
        "Generated memory atom must not produce lint errors.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


def test_canonical_memory_scaffold_assets_exist_with_frontmatter() -> None:
    expected = [
        _SCAFFOLD_MEMORY / "architecture.md",
        _SCAFFOLD_MEMORY / "tech-stack.md",
        _SCAFFOLD_MEMORY / "product" / "index.md",
        _SCAFFOLD_MEMORY / "product" / "feature.md",
    ]

    for path in expected:
        assert path.is_file(), f"Missing memory scaffold asset: {path}"
        assert path.read_text(encoding="utf-8").startswith("---\n"), (
            f"Memory scaffold asset must start with YAML frontmatter: {path}"
        )


def test_canonical_memory_scaffold_atoms_are_accepted_by_lint(tmp_path: Path) -> None:
    memory_dir = tmp_path / "memory"
    (memory_dir / "product").mkdir(parents=True)
    shutil.copy(_SCAFFOLD_MEMORY / "architecture.md", memory_dir / "architecture.md")
    shutil.copy(_SCAFFOLD_MEMORY / "tech-stack.md", memory_dir / "tech-stack.md")

    proc = _run_lint(memory_dir)

    assert proc.returncode != 1, (
        "Canonical memory scaffold atoms must not produce lint errors.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
