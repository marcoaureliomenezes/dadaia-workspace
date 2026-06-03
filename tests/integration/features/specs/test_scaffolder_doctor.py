"""Integration tests for scaffolded specs and SpecsDoctor."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs.doctor import Severity, SpecsDoctor
from dadaia_workspace.features.specs.scaffolder import scaffold

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow(reason="SpecsDoctor invokes memory atom lint for scaffolded specs"),
]


_REPO_ROOT = Path(__file__).resolve().parents[4]
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"


def test_fresh_scaffold_passes_specs_doctor(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    result = scaffold(
        specs_dir=specs_dir,
        project_name="doctor-test",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )

    assert result.errors == [], f"Scaffold errors: {result.errors}"

    issues = SpecsDoctor(specs_dir).check()
    errors = [issue for issue in issues if issue.severity == Severity.ERROR]
    assert errors == [], "Scaffolded specs/ should pass doctor with 0 errors. Got:\n" + "\n".join(
        f"  {issue.code}: {issue.description}" for issue in errors
    )
