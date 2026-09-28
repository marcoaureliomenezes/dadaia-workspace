"""Integration tests for scaffolded specs and SpecsDoctor."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import SpecsDoctor
from dadaia_workspace.features.specs.canon import scaffold

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow(reason="SpecsDoctor invokes memory atom lint for scaffolded specs"),
]


_REPO_ROOT = Path(__file__).resolve().parents[4]
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"


def test_fresh_scaffold_passes_specs_doctor(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    scaffold(
        specs_dir,
        project_name="doctor-test",
        force=False,
        public_dir=_TEMPLATES_DIR.parent,
    )

    issues = SpecsDoctor(specs_dir).check()
    assert issues == [], [i for i in issues]  # sa-placement-rules-contradict-tree8#B5
