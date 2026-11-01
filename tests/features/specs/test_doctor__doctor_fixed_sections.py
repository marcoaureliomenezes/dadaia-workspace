"""Size: SMALL. A throwaway public dir carries literal fragments; the doctor is driven
through its registry (check + fix) and the validator's own interface.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.doctor_rules import run_section
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.doctor_adr import LEDGER_RULES
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator
from dadaia_workspace.features.specs.doctor_types import finding_path
from tests.helpers.oslib import read_text, run, write_text

_FRAGMENTS = {
    "slop-law": "## Slop — workspace law (fixed)\n- LAW_BULLET\n",
    "slop-code": "### Slop — code (fixed)\n- CODE_BULLET\n",
    "slop-tests": "### Slop — tests (fixed)\n- TESTS_BULLET\n",
}


def _public_dir(tmp_path: Path) -> Path:
    fixed = tmp_path / "public" / "data" / "fixed"
    fixed.mkdir(parents=True)
    for section_id, fragment in _FRAGMENTS.items():
        write_text(fixed / f"{section_id}.md", fragment)
    return tmp_path / "public"


def _block(section_id: str, body: str) -> str:
    return f"<!-- dadaia:fixed {section_id} -->\n{body}<!-- /dadaia:fixed {section_id} -->\n"


def _specs(tmp_path: Path, *, constitution: str, architecture: str, quality: str) -> Path:
    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    write_text(specs / "constitution.md", constitution)
    write_text(specs / "memory" / "ARCHITECTURE.md", architecture)
    write_text(specs / "memory" / "QUALITY.md", quality)
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
    """A specs rule emits a SectionFinding directly."""
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
    write_text(specs / "constitution.md", "# C\n")
    issues = MemoryValidator(specs).check_fixed_sections(public)
    assert [(i.code, Path(finding_path(i) or "").name) for i in issues] == [
        ("FIXED-1", "constitution.md")
    ]


_REINSTALL = "Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument"


def test_check_reports_a_missing_library_fragment_as_a_non_fixable_error(tmp_path: Path) -> None:
    public = tmp_path / "public"
    (public / "data" / "fixed").mkdir(parents=True)
    specs = _specs(tmp_path, constitution="# C\n", architecture="# A\n", quality="# Q\n")
    issues = MemoryValidator(specs).check_fixed_sections(public)
    assert [(i.code, i.verdict, i.fixable) for i in issues] == [("FIXED-1", "error", False)] * 3
    assert all("library fragment" in i.message for i in issues)
    assert [i.fix for i in issues] == [_REINSTALL] * 3


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
    assert read_text(specs / "constitution.md") == (
        "# C\n\n" + _block("slop-law", _FRAGMENTS["slop-law"])
    )
    assert read_text(specs / "memory" / "ARCHITECTURE.md") == (
        "# A\n\n" + _block("slop-code", _FRAGMENTS["slop-code"]) + "\n## Tail\n"
    )
    assert read_text(specs / "memory" / "QUALITY.md") == (
        "# Q\n\n" + _block("slop-tests", _FRAGMENTS["slop-tests"])
    )
    assert _fixed_issues(doctor) == []


_STALE = "- 0099 — Stale\n"
_ADR_LIST = "- 0001 — A kept decision\n"


def _adr_specs(tmp_path: Path, *, markers: bool, measured_by: str) -> tuple[Path, Path, Path]:
    """Specs whose fixed blocks are exact; ARCHITECTURE.md carries a stale `adr-list` block."""
    public = _public_dir(tmp_path)
    architecture = "# A\n\n" + _block("slop-code", _FRAGMENTS["slop-code"])
    if markers:
        architecture += "\n" + _block("adr-list", _STALE)
    specs = _specs(
        tmp_path,
        constitution="# C\n\n" + _block("slop-law", _FRAGMENTS["slop-law"]),
        architecture=architecture,
        quality="# Q\n\n" + _block("slop-tests", _FRAGMENTS["slop-tests"]),
    )
    record = {
        "id": "0001",
        "title": "A kept decision",
        "status": "accepted",
        "measured_by": measured_by,
    }
    (specs / "ADRs").mkdir()
    write_text(specs / "ADRs" / "decisions.jsonl", json.dumps(record) + "\n")
    run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "tests").mkdir()
    write_text(tmp_path / "tests" / "test_x.py", "def test_one():\n    pass\n")
    run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    return public, specs, specs / "memory" / "ARCHITECTURE.md"


def test_a_stale_adr_list_block_is_fixed_2_and_fix_regenerates_it(tmp_path: Path) -> None:
    public, specs, architecture = _adr_specs(
        tmp_path, markers=True, measured_by="tests/test_x.py::test_one"
    )
    doctor = SpecsDoctor(specs, public_dir=public)
    assert _fixed_issues(doctor) == [("FIXED-2", "ARCHITECTURE.md")]

    doctor.fix()

    assert read_text(architecture) == (
        "# A\n\n"
        + _block("slop-code", _FRAGMENTS["slop-code"])
        + "\n"
        + _block("adr-list", _ADR_LIST)
    )
    assert _fixed_issues(doctor) == []


def test_a_file_without_the_adr_list_markers_yields_nothing(tmp_path: Path) -> None:
    public, specs, _ = _adr_specs(tmp_path, markers=False, measured_by="tests/test_x.py::test_one")
    assert _fixed_issues(SpecsDoctor(specs, public_dir=public)) == []


def test_an_unresolved_measured_by_refuses_the_regeneration_and_writes_nothing(
    tmp_path: Path,
) -> None:
    public, specs, architecture = _adr_specs(tmp_path, markers=True, measured_by="tests/missing.py")
    before = read_text(architecture)
    doctor = SpecsDoctor(specs, public_dir=public)

    refused = [i for i in doctor.check() if i.code == "FIXED-2"]

    assert len(refused) == 1 and "0001" in refused[0].message
    assert refused[0].fix == (
        "Agent action: set the measured_by of ADR 0001 to a tracked path, a path::name test or"
        " workflow-job id, or a rule code (an in-place `chore(adrs): repair` commit)."
    )
    doctor.fix()
    assert read_text(architecture) == before


def test_a_refused_adr_list_does_not_withhold_the_other_blocks_of_the_file(tmp_path: Path) -> None:
    public, specs, architecture = _adr_specs(tmp_path, markers=True, measured_by="tests/missing.py")
    drifted = read_text(architecture).replace(_FRAGMENTS["slop-code"], "drifted\n")
    write_text(architecture, drifted)
    doctor = SpecsDoctor(specs, public_dir=public)

    doctor.fix()

    assert read_text(architecture) == drifted.replace("drifted\n", _FRAGMENTS["slop-code"])


def test_markers_without_a_ledger_render_an_empty_list(tmp_path: Path) -> None:
    public, specs, architecture = _adr_specs(
        tmp_path, markers=True, measured_by="tests/test_x.py::test_one"
    )
    (specs / "ADRs" / "decisions.jsonl").unlink()
    doctor = SpecsDoctor(specs, public_dir=public)
    assert _fixed_issues(doctor) == [("FIXED-2", "ARCHITECTURE.md")]

    doctor.fix()

    assert read_text(architecture).endswith(_block("adr-list", ""))
    assert _fixed_issues(doctor) == []


def test_a_ledger_that_is_not_utf8_is_one_reencode_finding_and_never_a_crash(
    tmp_path: Path,
) -> None:
    public, specs, _ = _adr_specs(tmp_path, markers=True, measured_by="tests/test_x.py::test_one")
    ledger = specs / "ADRs" / "decisions.jsonl"
    ledger.write_bytes(b"\xff\xfe\n")
    restore = f"Agent action: re-encode line 1 of {ledger.resolve()} as UTF-8 in place; every other line stays"

    found = SpecsDoctor(specs, public_dir=public).check()

    ledgers = run_section("ledgers", LEDGER_RULES, specs, None, specs)
    assert [i.fix for i in ledgers.findings] == [restore]
    assert [i.code for i in found if i.code == "FIXED-2"] == []


def test_a_fragment_that_is_not_utf8_is_one_reinstall_finding_never_a_refused_render(
    tmp_path: Path,
) -> None:
    public = _public_dir(tmp_path)
    (public / "data" / "fixed" / "slop-code.md").write_bytes(b"\xff\xfe\n")
    specs = _specs(
        tmp_path,
        constitution="# C\n",
        architecture="# A\n\n" + _block("slop-code", "old\n"),
        quality="# Q\n",
    )

    found = SpecsDoctor(specs, public_dir=public).check()

    assert [(i.code, i.fix) for i in found if i.code in ("FIXED-2", "SPEC-DOC-002")] == [
        ("SPEC-DOC-002", _REINSTALL)
    ]
