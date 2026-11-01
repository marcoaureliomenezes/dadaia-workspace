"""The source-root guard reads the candidate's pyproject.toml as UTF-8 and judges nothing else."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure import workspace_guardrail
from tests.helpers.oslib import write_text


def test_a_pyproject_that_is_not_utf8_is_not_the_library_checkout(tmp_path: Path) -> None:
    (tmp_path / "dadaia_workspace" / "public").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_bytes(b'[project]\nname = "dadaia-workspace"\n# caf\xe9\n')

    assert workspace_guardrail._is_source_repo_root(tmp_path) is False


def test_the_library_checkout_is_recognised(tmp_path: Path) -> None:
    (tmp_path / "dadaia_workspace" / "public").mkdir(parents=True)
    write_text(tmp_path / "pyproject.toml", '[project]\nname = "dadaia-workspace"\n')

    assert workspace_guardrail._is_source_repo_root(tmp_path) is True
