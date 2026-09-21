"""Intent: CONTRACT — FR1 (0.4.7 c9); size: SMALL (repo-pure reads, no subprocess
unless `skills-ref` is installed).

The skills the project distributes standalone conform to the Agent Skills spec. The
set is READ from the behavior map's `standalone_skills` key — the one data source; no
literal roster lives in this file.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC = _REPO_ROOT / "dadaia_workspace" / "public"
_SKILLS_DIR = _PUBLIC / "skills"
_MAP = _PUBLIC / "entities" / "behavior-map.json"

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_SKILL_MD_LINE_CEILING = 500
_DESCRIPTION_CEILING = 1024
_COMPATIBILITY_CEILING = 500

# A body line that names one of these roots in an imperative "open" step hard-requires
# a workspace unless it is qualified as workspace-only.
_WORKSPACE_ROOTS = ("specs/", ".dadaia/")
_QUALIFIER = "inside a dadaia workspace"


def _standalone_skills() -> list[str]:
    data = json.loads(_MAP.read_text(encoding="utf-8"))
    names = data.get("standalone_skills")
    assert isinstance(names, list) and names, (
        "`standalone_skills` is missing or empty in "
        "dadaia_workspace/public/entities/behavior-map.json — it is the one data "
        "source for the distributed skill set"
    )
    return [str(name) for name in names]


def _frontmatter(path: Path) -> dict[str, object]:
    match = _FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    assert match, f"{path.relative_to(_REPO_ROOT)}: no YAML frontmatter block"
    loaded = yaml.safe_load(match.group(1))
    assert isinstance(loaded, dict), f"{path.relative_to(_REPO_ROOT)}: frontmatter is not a mapping"
    return loaded


def _body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    return text[match.end() :] if match else text


@pytest.fixture(params=_standalone_skills())
def skill_dir(request: pytest.FixtureRequest) -> Path:
    directory = _SKILLS_DIR / str(request.param)
    assert (directory / "SKILL.md").is_file(), (
        f"`standalone_skills` names {request.param!r} but "
        f"{directory.relative_to(_REPO_ROOT)}/SKILL.md does not exist"
    )
    return directory


def test_frontmatter_name_matches_the_directory(skill_dir: Path) -> None:
    """Agent Skills spec: `name` is the directory name, 1-64 chars, lowercase-hyphen."""
    name = _frontmatter(skill_dir / "SKILL.md").get("name")
    assert name == skill_dir.name, f"{skill_dir.name}: frontmatter name is {name!r}"
    assert isinstance(name, str) and 1 <= len(name) <= 64, f"{skill_dir.name}: name length"
    assert _NAME_RE.match(name), f"{skill_dir.name}: name is not lowercase-hyphen"


def test_frontmatter_description_is_within_the_spec_bounds(skill_dir: Path) -> None:
    """Agent Skills spec: `description` is present and at most 1,024 characters."""
    description = _frontmatter(skill_dir / "SKILL.md").get("description")
    assert isinstance(description, str), f"{skill_dir.name}: description missing"
    assert 1 <= len(description.strip()) <= _DESCRIPTION_CEILING, (
        f"{skill_dir.name}: description is {len(description.strip())} chars"
    )


def test_frontmatter_declares_compatibility(skill_dir: Path) -> None:
    """A standalone consumer learns from the frontmatter where the full lifecycle lives."""
    compatibility = _frontmatter(skill_dir / "SKILL.md").get("compatibility")
    assert isinstance(compatibility, str) and compatibility.strip(), (
        f"{skill_dir.name}: frontmatter carries no `compatibility:` line"
    )
    assert len(compatibility) <= _COMPATIBILITY_CEILING, (
        f"{skill_dir.name}: compatibility is {len(compatibility)} chars"
    )
    assert "dadaia-workspace" in compatibility, (
        f"{skill_dir.name}: compatibility does not name dadaia-workspace as the "
        "home of the full lifecycle"
    )


def test_skill_md_is_within_the_line_ceiling(skill_dir: Path) -> None:
    """Agent Skills spec: a SKILL.md stays under 500 lines."""
    lines = len((skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines())
    assert lines <= _SKILL_MD_LINE_CEILING, f"{skill_dir.name}: SKILL.md is {lines} lines"


def test_no_body_line_hard_requires_a_workspace_path(skill_dir: Path) -> None:
    """A step that opens a workspace-only path says so — the skill still reads outside
    a dadaia workspace."""
    offenders = [
        line.strip()
        for line in _body(skill_dir / "SKILL.md").splitlines()
        if re.search(r"\bOpen `(" + "|".join(re.escape(r) for r in _WORKSPACE_ROOTS) + ")", line)
        and _QUALIFIER not in line.lower()
    ]
    assert offenders == [], (
        f"{skill_dir.name}: body step hard-requires a workspace path — prefix it "
        f'"Inside a dadaia workspace, open …":\n  ' + "\n  ".join(offenders)
    )


def test_skills_ref_validates_the_directory(skill_dir: Path) -> None:
    """The upstream validator agrees, when it is installed."""
    executable = shutil.which("skills-ref")
    if executable is None:
        pytest.skip("skills-ref is not installed")
    result = subprocess.run(  # noqa: S603
        [executable, "validate", str(skill_dir)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"{skill_dir.name}: {result.stdout}\n{result.stderr}"
