"""Size: SMALL. A throwaway public dir carries literal fragments; the doctor is driven
through its registry (check + fix) and the validator's own interface.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator
from dadaia_workspace.features.specs.doctor_types import finding_path

_FRAGMENTS = {
    "slop-law": "## Slop — workspace law (fixed)\n- LAW_BULLET\n",
    "slop-code": "### Slop — code (fixed)\n- CODE_BULLET\n",
    "slop-tests": "### Slop — tests (fixed)\n- TESTS_BULLET\n",
}


def _public_dir(tmp_path: Path) -> Path:
    fixed = tmp_path / "public" / "data" / "fixed"
    fixed.mkdir(parents=True)
    for section_id, fragment in _FRAGMENTS.items():
        (fixed / f"{section_id}.md").write_text(fragment, encoding="utf-8")
    return tmp_path / "public"


def _block(section_id: str, body: str) -> str:
    return f"<!-- dadaia:fixed {section_id} -->\n{body}<!-- /dadaia:fixed {section_id} -->\n"


def _specs(tmp_path: Path, *, constitution: str, architecture: str, quality: str) -> Path:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    (specs / "constitution.md").write_text(constitution, encoding="utf-8")
    (specs / "memory" / "ARCHITECTURE.md").write_text(architecture, encoding="utf-8")
    (specs / "memory" / "QUALITY.md").write_text(quality, encoding="utf-8")
    return specs


def _fixed_issues(doctor: SpecsDoctor) -> list[tuple[str, str]]:
    return [
        (i.code, Path(finding_path(i) or "").name)
        for i in doctor.check()
        if i.code.startswith("FIXED-")
    ]


def test_check_reports_missing_and_drifted_blocks_and_stays_silent_on_exact_ones(
    tmp_path: Path,
) -> None:
    """sa-doctor-finding-has-four-shapes: a specs rule emits a SectionFinding directly."""
    public = _public_dir(tmp_path)
    specs = _specs(
        tmp_path,
        constitution="# C\n",
        architecture="# A\n\n" + _block("slop-code", "### Slop — code (fixed)\n- OLD\n"),
        quality="# Q\n\n" + _block("slop-tests", _FRAGMENTS["slop-tests"]),
    )
    issues = MemoryValidator(specs).check_fixed_sections(public)
    assert [(i.code, i.error, i.fixable, finding_path(i)) for i in issues] == [
        ("FIXED-1", True, True, str(specs / "constitution.md")),
        ("FIXED-2", True, True, str(specs / "memory" / "ARCHITECTURE.md")),
    ]
    assert issues[0].message.startswith(
        "constitution.md: fixed law section `slop-law` is missing ("
    )
    assert issues[1].message.startswith(
        "memory/ARCHITECTURE.md: fixed law section `slop-code` differs from the library fragment ("
    )


def test_check_is_a_no_op_for_an_absent_file(tmp_path: Path) -> None:
    public = _public_dir(tmp_path)
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    (specs / "constitution.md").write_text("# C\n", encoding="utf-8")
    issues = MemoryValidator(specs).check_fixed_sections(public)
    assert [(i.code, Path(finding_path(i) or "").name) for i in issues] == [
        ("FIXED-1", "constitution.md")
    ]


def test_check_reports_a_missing_library_fragment_as_a_non_fixable_error(tmp_path: Path) -> None:
    public = tmp_path / "public"
    (public / "data" / "fixed").mkdir(parents=True)
    specs = _specs(tmp_path, constitution="# C\n", architecture="# A\n", quality="# Q\n")
    issues = MemoryValidator(specs).check_fixed_sections(public)
    assert [(i.code, i.verdict, i.fixable) for i in issues] == [("FIXED-1", "error", False)] * 3
    assert all("library fragment" in i.message for i in issues)


def test_fix_inserts_a_missing_block_and_refreshes_a_drifted_one(tmp_path: Path) -> None:
    public = _public_dir(tmp_path)
    specs = _specs(
        tmp_path,
        constitution="# C\n",
        architecture="# A\n\n"
        + _block("slop-code", "### Slop — code (fixed)\n- OLD\n")
        + "\n## Tail\n",
        quality="# Q\n\n" + _block("slop-tests", _FRAGMENTS["slop-tests"]),
    )
    doctor = SpecsDoctor(specs, public_dir=public)
    assert _fixed_issues(doctor) == [("FIXED-1", "constitution.md"), ("FIXED-2", "ARCHITECTURE.md")]

    fixed = doctor.fix()

    assert [i.code for i in fixed if i.code.startswith("FIXED")] == ["FIXED-1", "FIXED-2"]
    assert (specs / "constitution.md").read_text(encoding="utf-8") == (
        "# C\n\n" + _block("slop-law", _FRAGMENTS["slop-law"])
    )
    assert (specs / "memory" / "ARCHITECTURE.md").read_text(encoding="utf-8") == (
        "# A\n\n" + _block("slop-code", _FRAGMENTS["slop-code"]) + "\n## Tail\n"
    )
    assert (specs / "memory" / "QUALITY.md").read_text(encoding="utf-8") == (
        "# Q\n\n" + _block("slop-tests", _FRAGMENTS["slop-tests"])
    )
    assert _fixed_issues(doctor) == []
