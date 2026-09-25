"""Intent: CONTRACT — AC2.1–AC2.6, AC1.9 (release 0.5.0 candidate 2, ADR 0041 `measured_by`).

`release.py phase IMPLEMENTATION` admits a candidate only when PLAN.md carries the As-is
review table — structure only — and the skeleton `dd-release-definition` teaches passes
it, so the teaching and the gate cannot drift. Size: SMALL.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_PUBLIC = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public"
_SKILL = _PUBLIC / "skills" / "dd-release-definition" / "SKILL.md"
_SCRIPTS = _PUBLIC / "skills" / "dd-release-implementation" / "scripts"
_SCHEMA = _PUBLIC / "schemas" / "releases" / "release-state-v1.schema.json"
_HEADER = "| unit | today | bugs | verdict | why |\n|---|---|---|---|---|\n"
_ROW = "| `core/x.py` `run` | does x | 0 | {verdict} | reason |\n"
_GOOD = "## 1. As-is review\n\n" + _HEADER + _ROW.format(verdict="UPDATE") + "\n## 2. Strategy\n"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    staged = tmp_path / "skills" / "dd-release-implementation" / "scripts"
    (staged / "schemas").mkdir(parents=True)
    shutil.copytree(_PUBLIC / "skills" / "dd-spec-navigator" / "scripts",
                    tmp_path / "skills" / "dd-spec-navigator" / "scripts")  # fmt: skip
    for module in _SCRIPTS.glob("*.py"):
        shutil.copy2(module, staged / module.name)
    shutil.copy2(_SCHEMA, staged / "schemas" / _SCHEMA.name)
    return staged / "release.py"


def _specs(tmp_path: Path, plan: str, *, plan_status: str = "Approved") -> Path:
    specs = tmp_path / "specs"
    release = specs / "releases" / "0.5.0"
    release.mkdir(parents=True)
    for name, body in (("SPEC.md", ""), ("PLAN.md", plan), ("TASKS.md", "- [ ] T-1\n")):
        status = plan_status if name == "PLAN.md" else "Approved"
        (release / name).write_text(f"# {name}\n\n**Status:** {status}\n\n{body}", "utf-8")
    state: dict[str, object] = {"schema": "release-state-v1", "release": "0.5.0", "phase": "DEFINITION",
             "defined": None, "implemented": None, "shipped": None, "log": []}  # fmt: skip
    (release / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", "utf-8")
    return specs


def _phase(script: Path, specs: Path) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, str(script), "phase", "IMPLEMENTATION", "--sha", "abc1234"]
    return subprocess.run([*argv, "--specs", str(specs)], capture_output=True, text=True)


def _admits(script: Path, tmp_path: Path, plan: str) -> None:
    specs = _specs(tmp_path, plan)
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
    _admits(script, tmp_path, fence.group(1))


def test_new_writes_a_spec_stub_carrying_replaces(script: Path, tmp_path: Path) -> None:
    """AC1.9 — the stub asks for Replaces between Scope and Out of scope; no PLAN born."""
    specs = tmp_path / "specs"
    (specs / "releases").mkdir(parents=True)
    argv = [sys.executable, str(script), "new", "0.9.0", "--specs", str(specs)]
    assert subprocess.run(argv, capture_output=True, text=True).returncode == 0
    stub = (specs / "releases/0.9.0/SPEC.md").read_text("utf-8")
    headings = re.findall(r"^## \d+\. (.+)$", stub, re.MULTILINE)
    assert headings.index("Scope") + 1 == headings.index("Replaces")
    assert headings.index("Replaces") + 1 == headings.index("Out of scope")
    assert not (specs / "releases/0.9.0/PLAN.md").exists()
