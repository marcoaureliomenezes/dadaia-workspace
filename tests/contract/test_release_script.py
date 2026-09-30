"""Intent: CONTRACT — AC2.1–AC2.6, AC1.9 (release 0.5.0 candidate 2, ADR 0041 `measured_by`);
AC5.2, AC5.3 (release 0.5.0 candidate 4, the Authorities table).

`release.py phase IMPLEMENTATION` admits a candidate only when PLAN.md carries the As-is
review table — structure only — and the skeleton `dd-release-definition` teaches passes
it, so the teaching and the gate cannot drift. Size: SMALL.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = pytest.mark.contract

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"
_SKILL = _PUBLIC / "skills" / "dd-release-definition" / "SKILL.md"
_SCRIPTS = _PUBLIC / "skills" / "dd-release-implementation" / "scripts"
_HEADER = "| unit | today | bugs | verdict | why |\n|---|---|---|---|---|\n"
_ROW = "| `core/x.py` `run` | does x | 0 | {verdict} | reason |\n"
_AUTH_HEADER = "| question | authority | consults | deleted |\n|---|---|---|---|\n"
_AUTHORITIES = (
    "\n### 1.1 Authorities\n\n" + _AUTH_HEADER + "| who writes x | `core/x.run` | cli | `y` |\n"
)
_GOOD = (
    "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="UPDATE") + _AUTHORITIES
    + "\n## 2. Strategy\n"
)  # fmt: skip


@pytest.fixture
def script(tmp_path: Path) -> Path:
    stage_skill_scripts("dd-spec-navigator", tmp_path / "skills" / "dd-spec-navigator" / "scripts")
    return (
        stage_skill_scripts(
            "dd-release-implementation",
            tmp_path / "skills" / "dd-release-implementation" / "scripts",
        )
        / "release.py"
    )


def _specs(tmp_path: Path, plan: str, *, plan_status: str = "Approved") -> Path:
    specs = tmp_path / "specs"
    release = specs / "releases" / "0.5.0"
    (release / "rc-1").mkdir(parents=True)
    for name, body in (("SPEC.md", ""), ("PLAN.md", plan), ("TASKS.md", "- [ ] T-1\n")):
        status = plan_status if name == "PLAN.md" else "Approved"
        (release / "rc-1" / name).write_text(f"# {name}\n\n**Status:** {status}\n\n{body}", "utf-8")
    state: dict[str, object] = {"schema": "release-state-v1", "release": "0.5.0", "phase": "DEFINITION",
             "defined": None, "implemented": None, "shipped": None, "log": []}  # fmt: skip
    (release / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", "utf-8")
    return specs


def _phase(script: Path, specs: Path) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, str(script), "phase", "IMPLEMENTATION", "--sha", "abc1234"]
    return subprocess.run([*argv, "--specs", str(specs)], capture_output=True, text=True)


def _admits(script: Path, tmp_path: Path, plan: str, *, authorities: bool = True) -> None:
    """*authorities*: append a valid §1.1 table to a PLAN whose case is the As-is table."""
    specs = _specs(tmp_path, plan + (_AUTHORITIES if authorities else ""))
    result = _phase(script, specs)
    assert result.returncode == 0, result.stderr
    state = json.loads((specs / "releases/0.5.0/_RELEASE.json").read_text("utf-8"))
    assert (state["phase"], state["defined"]["sha"]) == ("IMPLEMENTATION", "abc1234")
    assert len(state["log"]) == 1


def _refuses(script: Path, tmp_path: Path, plan: str, *needles: str) -> str:
    specs = _specs(tmp_path, plan)
    before = (specs / "releases/0.5.0/_RELEASE.json").read_bytes()
    result = _phase(script, specs)
    assert result.returncode != 0
    assert (specs / "releases/0.5.0/_RELEASE.json").read_bytes() == before
    assert "PLAN.md" in result.stderr
    fixes = [line for line in result.stderr.splitlines() if line.lstrip().startswith("fix:")]
    assert len(fixes) == 1 and "dd-release-definition" in fixes[0] and "As-is review" in fixes[0]
    for needle in needles:
        assert needle in result.stderr
    return result.stderr


def test_a_plan_with_the_table_enters_implementation(script: Path, tmp_path: Path) -> None:
    _admits(script, tmp_path, _GOOD)


def test_an_unnumbered_heading_and_a_lowercase_verdict_pass(script: Path, tmp_path: Path) -> None:
    plan = "## as-is REVIEW\n\n" + _HEADER + _ROW.format(verdict="**`rebuild`**")
    _admits(script, tmp_path, plan)


def test_an_all_add_table_with_empty_cells_passes(script: Path, tmp_path: Path) -> None:
    _admits(script, tmp_path, "## 1. As-is review\n\n" + _HEADER + "| new.py | — |  | ADD |  |\n")


@pytest.mark.parametrize(
    "plan",
    [
        pytest.param("## 1. Strategy\n\nno table\n", id="heading-missing"),
        pytest.param("## 1. As-is review\n\nprose only\n\n## 2. Next\n\n" + _HEADER, id="no-table"),
        pytest.param(
            "## 1. As-is review\n\n| unit | verdict |\n|---|---|\n| a | KEEP |\n", id="wrong-header"
        ),
        pytest.param("## 1. As-is review\n\n" + _HEADER, id="zero-rows"),
    ],
)
def test_a_plan_without_the_table_structure_is_refused(
    script: Path, tmp_path: Path, plan: str
) -> None:
    _refuses(script, tmp_path, plan, "As-is review")


def test_a_verdict_outside_the_vocabulary_names_its_row(script: Path, tmp_path: Path) -> None:
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="SHRINK")
    _refuses(script, tmp_path, plan, "core/x.py", "SHRINK")


def test_an_unapproved_trio_refuses_before_the_table(script: Path, tmp_path: Path) -> None:
    result = _phase(script, _specs(tmp_path, "no table\n", plan_status="Draft"))
    assert result.returncode != 0
    assert "carries status 'Draft'" in result.stderr and "As-is review" not in result.stderr


def test_the_taught_skeleton_passes_the_check(script: Path, tmp_path: Path) -> None:
    """The skeleton `dd-release-definition` shows is the PLAN shape the gate admits."""
    skill = _SKILL.read_text("utf-8")
    fence = re.search(r"```markdown\n(## 1\. As-is review\n.*?)```", skill, re.DOTALL)
    assert fence, "dd-release-definition lost its PLAN §1 skeleton"
    _admits(script, tmp_path, fence.group(1), authorities=False)


def test_new_writes_a_spec_stub_carrying_replaces(script: Path, tmp_path: Path) -> None:
    """AC1.9 — the stub asks for Replaces between Scope and Out of scope; no PLAN born."""
    specs = tmp_path / "specs"
    (specs / "releases").mkdir(parents=True)
    argv = [sys.executable, str(script), "new", "0.9.0", "--specs", str(specs)]
    assert subprocess.run(argv, capture_output=True, text=True).returncode == 0
    stub = (specs / "releases/0.9.0/rc-1/SPEC.md").read_text("utf-8")
    headings = re.findall(r"^## \d+\. (.+)$", stub, re.MULTILINE)
    assert headings.index("Scope") + 1 == headings.index("Replaces")
    assert headings.index("Replaces") + 1 == headings.index("Out of scope")
    assert not (specs / "releases/0.9.0/rc-1/PLAN.md").exists()


@pytest.mark.parametrize(
    "heading",
    ["## 1 As-is review", "## 1) As is review:", "## As-is review (PLAN §1)", "## 2. AS-IS REVIEW"],
)
def test_any_level_2_heading_naming_the_review_passes(
    script: Path, tmp_path: Path, heading: str
) -> None:
    _admits(script, tmp_path, f"{heading}\n\n" + _HEADER + _ROW.format(verdict="KEEP"))


def test_rows_without_outer_pipes_and_escaped_pipes_pass(script: Path, tmp_path: Path) -> None:
    table = (
        "unit | today | bugs | verdict | why\n---|---|---|---|---\n\ta \\| b\t| x | 0 |\tKEEP | y\n"
    )
    _admits(script, tmp_path, "## As-is review\n\n" + table)


def test_the_table_ends_at_its_first_blank_line(script: Path, tmp_path: Path) -> None:
    later = "\n| other | table | 0 | SHRINK | ignored |\n"
    _admits(script, tmp_path, _GOOD.split("\n## 2.")[0] + later)


def test_the_refusal_says_heading_missing_or_table_malformed(script: Path, tmp_path: Path) -> None:
    missing = _refuses(script, tmp_path / "a", "## Strategy\n", "heading")
    malformed = _refuses(script, tmp_path / "b", "## 1. As-is review\n\n" + _HEADER, "header")
    assert "not followed by a table" not in missing and "not followed by a table" in malformed


def test_every_fix_names_an_existing_absolute_path(script: Path, tmp_path: Path) -> None:
    """F1 — fix lines point at files, never at a cwd-relative or section-numbered command."""
    sys.path.insert(0, str(_SCRIPTS))
    try:
        import _release_phase
    finally:
        sys.path.remove(str(_SCRIPTS))
    assert _release_phase.SKILL.is_file() and str(_release_phase.SKILL) in _release_phase.AS_IS_FIX
    fix = [ln for ln in _phase(script, _specs(tmp_path, "", plan_status="Draft")).stderr.splitlines()
           if ln.lstrip().startswith("fix:")][0]  # fmt: skip
    assert Path(fix.split(" in ", 1)[1].strip()).is_file()


def test_a_sentence_naming_the_columns_above_the_table_passes(script: Path, tmp_path: Path) -> None:
    prose = "## 1. As-is review\n\nColumns are `unit | today` and more.\n\n"
    _admits(script, tmp_path, prose + _HEADER + _ROW.format(verdict="KEEP"))


def test_a_plan_giving_each_question_one_authority_enters_implementation(
    script: Path, tmp_path: Path
) -> None:
    """AC5.2 fixture pair, good twin: one authority per question, a question repeated
    with the SAME authority is still one authority."""
    rows = "| who writes x | `a` | b |  |\n| who reads y | `c` |  | `d` |\n| who writes x | `a` | e |  |\n"
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="KEEP")
    _admits(
        script,
        tmp_path,
        plan + "\n### 1.1 Authorities\n\n" + _AUTH_HEADER + rows,
        authorities=False,
    )


def test_a_question_with_two_authorities_is_refused(script: Path, tmp_path: Path) -> None:
    """AC5.2 fixture pair, refused twin: the same question names two authorities."""
    rows = "| who writes x | `a` | b |  |\n| Who writes x | `z` |  |  |\n"
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="KEEP")
    stderr = _refuses(
        script, tmp_path, plan + "\n### 1.1 Authorities\n\n" + _AUTH_HEADER + rows,
        "'who writes x'", "two authorities",
    )  # fmt: skip
    assert "`a`" in stderr and "`z`" in stderr


@pytest.mark.parametrize(
    ("authorities", "needle"),
    [
        pytest.param("", "Authorities", id="no-table"),
        pytest.param("\n### 1.1 Authorities\n\nprose\n", "question | authority", id="no-header"),
        pytest.param("\n### 1.1 Authorities\n\n" + _AUTH_HEADER, "question | authority", id="zero-rows"),
        pytest.param(
            "\n### 1.1 Authorities\n\n" + _AUTH_HEADER + "| who writes x |  | b |  |\n",
            "empty authority", id="empty-authority",
        ),
    ],
)  # fmt: skip
def test_a_plan_without_a_well_formed_authorities_table_is_refused(
    script: Path, tmp_path: Path, authorities: str, needle: str
) -> None:
    """AC5.2: missing table, header or rows, or an empty authority — one fix line each."""
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="KEEP") + authorities
    _refuses(script, tmp_path, plan, needle)


def test_an_authorities_table_outside_section_1_does_not_count(
    script: Path, tmp_path: Path
) -> None:
    """AC5.2: the table belongs to §1; one under a later section is not the table."""
    plan = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="KEEP") + "\n## 2. Strategy\n"
    _refuses(script, tmp_path, plan + _AUTHORITIES, "Authorities")
