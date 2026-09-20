"""Integration tests for `dadaia release new`.

Intent: CONTRACT — v0.12.0 A3.1, A3.3 (CLI byte-diff coverage lives in the unit test)

`release new` writes SPEC.md with Draft status, the release id in the body and the
Owner/Opened fields, and exits non-zero on an existing directory.

The `backlog new` half retired in 0.4.7 c7 (T-047-65): `BACKLOG.json` has ONE writer,
`dd-backlog-definition/scripts/backlog.py`, covered by
`tests/unit/skills/test_backlog_definition_backlog_script.py`.
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


def test_release_new_writes_a_draft_spec_and_refuses_a_second_one(specs: Path) -> None:
    result = _runner.invoke(app, ["release", "new", "my-feature-v1", "--specs-dir", str(specs)])
    assert result.exit_code == 0, result.output

    spec_path = specs / "releases" / "my-feature-v1" / "SPEC.md"
    assert spec_path.is_file()
    content = spec_path.read_text(encoding="utf-8")
    assert "Status:** Draft" in content or "Status: Draft" in content
    assert "my-feature-v1" in content
    assert "Owner" in content
    assert "Opened" in content

    again = _runner.invoke(app, ["release", "new", "my-feature-v1", "--specs-dir", str(specs)])
    assert again.exit_code != 0
    assert "already exist" in again.output.lower() or "already exist" in (again.stderr or "")
