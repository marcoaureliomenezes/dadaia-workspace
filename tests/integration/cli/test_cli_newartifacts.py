"""Integration tests for `dadaia release new` and `dadaia backlog new`.

Merged per plan-integration.md (10 -> 1): `release new` (SPEC.md + Draft status +
release-id in body + Owner/Opened fields + existing-dir exits non-zero) and
`backlog new` (file + frontmatter). Deleted 4 invalid-slug/missing-specs-dir greps
(unit-ownable) plus redundant field asserts.

(The legacy ``dadaia bug new`` command was retired in v0.1.53 — bugs are event-sourced
JSONL via ``dadaia bugs append``.)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    """Return an empty specs/ directory."""
    s = tmp_path / "specs"
    s.mkdir()
    return s


def test_release_new_and_backlog_new(specs: Path) -> None:
    result = _runner.invoke(
        app,
        ["release", "new", "my-feature-v1", "--specs-dir", str(specs)],
    )
    assert result.exit_code == 0, result.output
    spec_path = specs / "releases" / "my-feature-v1" / "SPEC.md"
    assert spec_path.is_file()
    content = spec_path.read_text(encoding="utf-8")
    assert "Status:** Draft" in content or "Status: Draft" in content
    assert "my-feature-v1" in content
    assert "Owner" in content
    assert "Opened" in content

    existing_result = _runner.invoke(
        app,
        ["release", "new", "my-feature-v1", "--specs-dir", str(specs)],
    )
    assert existing_result.exit_code != 0
    assert "already exists" in existing_result.output.lower() or "already exists" in (
        existing_result.stderr or ""
    )

    backlog_result = _runner.invoke(
        app,
        ["backlog", "new", "cool-idea", "--specs-dir", str(specs)],
    )
    assert backlog_result.exit_code == 0, backlog_result.output
    target = specs / "backlog" / "cool-idea.md"
    assert target.is_file()
    backlog_content = target.read_text(encoding="utf-8")
    assert "title:" in backlog_content
    assert "status: idea" in backlog_content
    assert "opened:" in backlog_content
