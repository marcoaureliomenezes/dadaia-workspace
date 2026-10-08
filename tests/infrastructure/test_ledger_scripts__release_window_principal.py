"""release-check-parses-the-gitflow-in-the-skill#doctor: the doctor closes the CLOSURE
window on the principal `core.gitflow` reads, in every form the constitution may state it.

size: MEDIUM — a real git repo and the real release script via the doctor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.ledger_scripts import script_findings
from tests.public.skills.dd_release_implementation.scripts.test_release import (
    _git,
    _memory_repo,
    _side_branch_until,
    script,  # noqa: F401  (the staged-skill fixture)
)

pytestmark = pytest.mark.medium

_YAML = "---\ngitflow:\n  principal: trunk\n  integration: develop\n  work: feature/\n---\n"
_NONE = "---\nconstitution_version: 1.0.0\n---\n"


@pytest.mark.parametrize(("constitution", "principal"), [(_YAML, "trunk"), (_NONE, "main")])
def test_the_window_is_closed_on_the_principal_core_reads(
    script: Path,  # noqa: F811
    tmp_path: Path,
    constitution: str,
    principal: str,
) -> None:
    root, specs, base = _memory_repo(tmp_path, script)
    _git(root, "branch", "-m", principal)
    (specs / "constitution.md").write_text(constitution, encoding="utf-8")
    _side_branch_until(root, specs, base, "--squash")

    found = [f for f in script_findings(specs) if f.code == "LEDGER-RELEASE-SCHEMA"]

    assert found == []
