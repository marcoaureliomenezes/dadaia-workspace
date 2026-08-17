"""Subprocess integration tests for lint-memory-atoms.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow(reason="executes lint-memory-atoms.py as a subprocess"),
]


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts" / "lint-memory-atoms.py"


def _valid_frontmatter(slug: str = "test-atom") -> str:
    fields: dict[str, Any] = {
        "slug": slug,
        "title": "Test Atom",
        "category": "product",
        "tldr": "A short description.",
        "summary": "One to two sentence summary.",
        "tags": ["test"],
        "last_updated": "2026-06-01",
        "release_origin": "memory-markdown-source-v1",
    }
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"{key}: {value!r}")
    lines.extend(["---", ""])
    return "\n".join(lines) + "\n"


def _make_atom(
    tmp_path: Path,
    *,
    slug: str = "test-atom",
    body: str = "## Propósito\n\nThis is the body.\n",
) -> Path:
    md_path = tmp_path / f"{slug}.md"
    md_path.write_text(_valid_frontmatter(slug) + body, encoding="utf-8")
    return md_path


def test_subprocess_clean_exits_zero_bad_atom_exits_one(tmp_path: Path) -> None:
    """Two subprocess runs: clean atom -> exit 0; a Changelog-section atom -> exit 1."""
    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()
    _make_atom(clean_dir)
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "--memory-dir", str(clean_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Expected exit 0.\nstdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )

    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    _make_atom(
        bad_dir,
        body="## Propósito\n\nOK.\n\n## Changelog\n\nHistory.\n",
    )
    result2 = subprocess.run(
        [sys.executable, str(_SCRIPT), "--memory-dir", str(bad_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result2.returncode == 1, (
        f"Expected exit 1.\nstdout: {result2.stdout!r}\nstderr: {result2.stderr!r}"
    )
