"""Integration self-test AND real-repo wiring for tests/scripts/check_skill_orphans.py.

Two fake-tree test cases:
  1. Orphan detected — seeded tree has one wired skill and one orphan;
     script must exit 1 and name only the orphan in stderr.
  2. All wired — after wiring the orphan into the fake agent;
     script must exit 0 with no output on stderr or stdout.

Plus the real-repo WIRING case (v0.4.3 T-043-25 / FR18b, Verdict 3): the script had
correctness coverage (the two cases above) but was never actually invoked against this
repo's own tree by any suite, CI job, or doctor command — "wired, not deleted" per the
qa-engineer verdict. `test_real_repo_orphans_match_known_exemption_or_none` runs it with
no `DADAIA_WORKSPACE_ROOT` override (the script's own default resolves to the real repo
root), so it is now part of the normal gating pytest run and regresses on any NEW orphan.

Intent: CONTRACT — bug skill-orphans-unwired-agent-frontmatter
Owner: software-engineer
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "check_skill_orphans.py"
_REPO_ROOT = _SCRIPT.parent.parent.parent

# Pre-existing orphans, cited by the registered bug (T-043-25/FR18b discovery), now
# WIRED by ai-engineer (Arm-B rider on bug skill-orphans-unwired-agent-frontmatter):
# dadaia-gitflow, dadaia-test-stewardship, and harness-primitives are all referenced
# from agent frontmatter `skills:` lists. The exemption set is empty — any orphan
# found now is a genuinely NEW, unregistered drift, never a silent hole (mirroring the
# `_BESPOKE_EXEMPT` pattern in tests/unit/helpers/test_no_local_helper_copies.py).
_KNOWN_ORPHANS_BUG_SKILL_ORPHANS_UNWIRED_AGENT_FRONTMATTER: frozenset[str] = frozenset()


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


def test_orphan_detected_then_wired_exits_clean(tmp_path: Path) -> None:
    """Two subprocess runs: orphan present -> exit 1 naming it; wired -> exit 0 silent."""
    orphan_ws = tmp_path / "orphan-case"
    _seed_workspace(orphan_ws, agent_skills=["__wired_skill"])
    result = _run_script(orphan_ws)
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

    wired_ws = tmp_path / "wired-case"
    _seed_workspace(wired_ws, agent_skills=["__wired_skill", "__orphan_skill"])
    result2 = _run_script(wired_ws)
    assert result2.returncode == 0, (
        f"Expected exit code 0 (no orphans), got {result2.returncode}.\n"
        f"stdout: {result2.stdout!r}\nstderr: {result2.stderr!r}"
    )
    assert result2.stderr.strip() == "", (
        f"Expected empty stderr on clean run.\nstderr: {result2.stderr!r}"
    )
    assert result2.stdout.strip() == "", (
        f"Expected empty stdout on clean run.\nstderr: {result2.stdout!r}"
    )


def test_real_repo_orphans_match_known_exemption_or_none() -> None:
    """WIRE (T-043-25/FR18b Verdict 3): run the script against the REAL repo tree.

    No ``DADAIA_WORKSPACE_ROOT`` override — the script's own default resolution
    (``Path(__file__).resolve().parent.parent.parent`` from its own location under
    ``tests/scripts/``) lands on this checkout's repo root, exactly as a doctor/CI
    invocation would run it. The known-orphan exemption
    (bug skill-orphans-unwired-agent-frontmatter) is now empty — ai-engineer wired all
    3 into agent frontmatter `skills:` lists — so the tree must be fully clean: any
    orphan found is a genuinely NEW, unregistered drift, never a silent hole.
    """
    result = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        env={"PATH": str(Path(sys.executable).parent)},
    )
    found = frozenset(line.strip() for line in result.stderr.splitlines() if line.strip())

    unexpected = found - _KNOWN_ORPHANS_BUG_SKILL_ORPHANS_UNWIRED_AGENT_FRONTMATTER
    assert not unexpected, (
        f"NEW skill orphan(s) not covered by the registered bug "
        f"skill-orphans-unwired-agent-frontmatter: {sorted(unexpected)}. Wire the "
        "skill into an agent's `skills:` frontmatter or register a fresh bug — never "
        "silently widen this exemption."
    )
    assert found == frozenset(), (
        f"Some orphans are still exempted but not actually wired — "
        f"update the exemption set to match reality: found={sorted(found)}"
    )
    assert result.returncode == 0, (
        f"No orphans found but script still exits non-zero: {result.stderr!r}"
    )
