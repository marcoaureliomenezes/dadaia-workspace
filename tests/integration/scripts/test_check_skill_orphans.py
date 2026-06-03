"""Integration self-test for tests/scripts/check_skill_orphans.py.

Two test cases:
  1. Orphan detected — seeded tree has one wired skill and one orphan;
     script must exit 1 and name only the orphan in stderr.
  2. All wired — after wiring the orphan into the fake agent;
     script must exit 0 with no output on stderr or stdout.
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "check_skill_orphans.py"


def _seed_workspace(tmp_path: Path, agent_skills: list[str]) -> None:
    """Create a minimal fake dadaia_workspace tree inside tmp_path."""
    skills_dir = tmp_path / "dadaia_workspace" / "public" / "skills"
    agents_dir = tmp_path / "dadaia_workspace" / "public" / "agents"
    skills_dir.mkdir(parents=True)
    agents_dir.mkdir(parents=True)

    # Two skill dirs — always created; wiring varies per test case.
    (skills_dir / "__wired_skill").mkdir()
    (skills_dir / "__wired_skill" / "SKILL.md").write_text("# wired skill\n")
    (skills_dir / "__orphan_skill").mkdir()
    (skills_dir / "__orphan_skill" / "SKILL.md").write_text("# orphan skill\n")

    # One agent file whose skills: list is controlled by the caller.
    skills_yaml = "\n".join(f"  - {s}" for s in agent_skills)
    agent_content = f"---\nname: fake-agent\nskills:\n{skills_yaml}\n---\n# Fake agent\n"
    (agents_dir / "fake-agent.md").write_text(agent_content)


def _run_script(tmp_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SCRIPT)],
        capture_output=True,
        text=True,
        env={"DADAIA_WORKSPACE_ROOT": str(tmp_path), "PATH": str(Path(sys.executable).parent)},
    )


def test_orphan_detected(tmp_path: Path) -> None:
    """Script exits 1 and prints only the orphan skill name to stderr."""
    _seed_workspace(tmp_path, agent_skills=["__wired_skill"])

    result = _run_script(tmp_path)

    assert result.returncode == 1, (
        f"Expected exit code 1 (orphan found), got {result.returncode}.\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert "__orphan_skill" in result.stderr, (
        f"Expected '__orphan_skill' in stderr.\nstderr: {result.stderr!r}"
    )
    assert "__wired_skill" not in result.stderr, (
        f"'__wired_skill' should NOT appear in stderr (it is wired).\nstderr: {result.stderr!r}"
    )


def test_all_wired_exits_clean(tmp_path: Path) -> None:
    """Script exits 0 with no output when every skill is referenced."""
    _seed_workspace(tmp_path, agent_skills=["__wired_skill", "__orphan_skill"])

    result = _run_script(tmp_path)

    assert result.returncode == 0, (
        f"Expected exit code 0 (no orphans), got {result.returncode}.\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert result.stderr.strip() == "", (
        f"Expected empty stderr on clean run.\nstderr: {result.stderr!r}"
    )
    assert result.stdout.strip() == "", (
        f"Expected empty stdout on clean run.\nstderr: {result.stdout!r}"
    )
