"""Integration tests for scaffolded specs and SpecsDoctor."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import SpecsDoctor
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
    # v6 canon (T-050-05, FR1): backlog/AGENTS.md is a NEW, expected scaffold member
    # (README.md retired into it), but doctor_governance.py's SPEC-DOC-035
    # single-source check (`_BACKLOG_SINGLE_SOURCE_FILES`) does not yet allowlist
    # "AGENTS.md" — that check is outside T-050-05's write set (doctor_governance.py),
    # so this one WARNING is a known, recorded gap until whichever task extends the
    # allowlist. WARN-only; never blocks (D15).
    known_gaps = {
        (i.code, i.path)
        for i in issues
        if i.code == "SPEC-DOC-035" and (i.path or "").endswith("backlog/AGENTS.md")
    }
    unexpected = [i for i in issues if (i.code, i.path) not in known_gaps]
    assert unexpected == [], (
        "Scaffolded specs/ should pass doctor with 0 unexpected issues. Got:\n"
        + "\n".join(
            f"  {issue.severity.value} {issue.code}: {issue.description}" for issue in unexpected
        )
    )
    assert len(known_gaps) == 1, (
        "Expected exactly one known SPEC-DOC-035 gap (backlog/AGENTS.md); "
        f"got {known_gaps} — doctor_governance.py may have been fixed, tighten this test."
    )
