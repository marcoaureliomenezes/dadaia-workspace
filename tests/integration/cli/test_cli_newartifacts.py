"""Integration tests for `dadaia release new` and `dadaia backlog new`.

Intent: CONTRACT — v0.12.0 A3.1, A3.3 (CLI byte-diff coverage lives in the unit test)

`release new` (SPEC.md + Draft status + release-id in body + Owner/Opened fields +
existing-dir exits non-zero, unchanged by SPEC v0.12.0) and `backlog new` (now authors
an ACTIVE subsection into BACKLOG.md — the `[ok] created:` / `[error]` CLI contract is
preserved, SPEC FR3).

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
    assert "[ok] created:" in backlog_result.output

    target = specs / "backlog" / "BACKLOG.md"
    assert target.is_file()
    backlog_content = target.read_text(encoding="utf-8")
    assert "## ACTIVE" in backlog_content
    assert "## LEDGER" in backlog_content
    assert "### cool-idea" in backlog_content
    assert "- **Title:** cool-idea" in backlog_content
    assert "- **Status:** idea" in backlog_content
    assert "- **Opened:**" in backlog_content

    # A3.3: the slug-uniqueness refusal (not file-level no-clobber) — same CLI exit
    # code class / `[error]` contract as the retired file-level check.
    dup_result = _runner.invoke(
        app,
        ["backlog", "new", "cool-idea", "--specs-dir", str(specs)],
    )
    assert dup_result.exit_code != 0
    assert "[error]" in (dup_result.output + (dup_result.stderr or ""))
