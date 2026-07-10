"""Regression tests for the implementation-review-QA done gate."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC = REPO_ROOT / "dadaia_workspace" / "public"

ORCHESTRATION_SKILL = PUBLIC / "skills" / "project-orchestration" / "SKILL.md"
TASK_MANAGER_SKILL = PUBLIC / "skills" / "dadaia-task-manager" / "SKILL.md"
PROJECT_MANAGER = PUBLIC / "agents" / "project-manager.md"

# Core implementers (non-plugin) on the new 9-agent surface.
# Plugin stubs (frontend-engineer, devops-engineer) intentionally omit full
# implementer gate wording — they are excluded from this check.
IMPLEMENTERS = (
    "software-engineer.md",
    "ai-engineer.md",
)
REVIEWERS = ("qa-engineer.md", "security-reviewer.md", "code-reviewer.md")

REQUIRED_GATE_TERMS = (
    "Pre-Implementation Agreement",
    "implementation-complete",
    "Review/QA Fan-Out",
    "REQUEST_CHANGES",
    "APPROVE",
    "same implementation commit",
    "mark the task `[x]`",
    "push implementation commits",
    "open or update a PR",
    "merge, deploy, or close the release",
)

LEAKAGE_TERMS = (
    # "public asset privacy" / "public-asset privacy" — both forms exist; check
    # for the shared substring that appears in all implementer agent files.
    "asset privacy",
    "secrets/tokens",
    "auth/access control",
    "dependency additions",
    "generated files",
    "consumer-specific data",
)

FORBIDDEN_OLD_DONE_WORDING = (
    "Mark the task `[x]` (DONE) only after qa-engineer confirms",
    "task closes only after qa-engineer confirms",
    "If all pass: confirm to the implementer that the task may be closed",
    "Trigger the deploy via GitHub Actions",
    "Trigger the deploy via the documented workflow",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: Path) -> str:
    return " ".join(_read(path).split())


def test_done_gate_terms_present_everywhere_and_old_shortcuts_never_reappear() -> None:
    """The implementation-review-QA done gate is a single governance contract spread
    across surfaces (orchestration skill, task-manager skill, project-manager persona,
    implementer personas, reviewer personas) — each surface's required-term table is
    checked here; retired pre-gate wording must never reappear on any of them."""
    failures: list[str] = []

    content = _read(ORCHESTRATION_SKILL)
    missing = [term for term in REQUIRED_GATE_TERMS if term not in content]
    if missing:
        failures.append(f"{ORCHESTRATION_SKILL.name}: missing {missing}")

    content = _read(TASK_MANAGER_SKILL)
    flat = " ".join(content.split())
    for term in (
        "Implementation complete is not DONE",
        "it is forbidden to mark `[x]`",
        "open a PR",
        "deploy",
        "write `CLOSURE.md`",
    ):
        if term not in flat:
            failures.append(f"{TASK_MANAGER_SKILL.name}: missing {term!r}")
    for term in ("qa-engineer", "code-reviewer", "security-reviewer"):
        if term not in content:
            failures.append(f"{TASK_MANAGER_SKILL.name}: missing {term!r}")

    content = _read(PROJECT_MANAGER)
    # Terms present in the current project-manager persona (9-agent surface).
    # "Before TASKS approval", "owning implementer(s)", "design-specialist",
    # and "implementation-complete" are no longer part of the PM persona wording
    # after the agent-surface-reduction; the gate is enforced through the
    # project-orchestration skill referenced above.
    required = (
        "qa-engineer",
        "code-reviewer",
        "security-reviewer",
        "REQUEST_CHANGES",
        "keeps the task `[-]`",
        "project-orchestration",
        "APPROVE",
    )
    missing = [term for term in required if term not in content]
    if missing:
        failures.append(f"{PROJECT_MANAGER.name}: missing {missing}")

    for filename in IMPLEMENTERS:
        path = PUBLIC / "agents" / filename
        raw = _read(path)
        # Skip plugin stubs — they carry no implementer gate wording by design.
        if "plugin: true" in raw:
            continue
        flat_impl = _flat(path)
        required_impl = (
            "handoff, not task completion",
            "REQUEST_CHANGES",
            "rerun against the new commit",
            "Do not mark",
            "push",
            "open PR",
            "merge",
            "deploy",
            "close release",
        )
        for term in required_impl:
            if term not in flat_impl:
                failures.append(f"{filename}: missing {term!r}")
        if "implementation-complete" not in flat_impl and "completed" not in flat_impl:
            failures.append(f"{filename}: missing implementation completion wording")
        for term in LEAKAGE_TERMS:
            if term not in flat_impl:
                failures.append(f"{filename}: missing leakage term {term!r}")

    for filename in REVIEWERS:
        content = _read(PUBLIC / "agents" / filename)
        required_rev = (
            "Approval contract",
            "APPROVE",
            "REQUEST_CHANGES",
            "evidence",
            "paths",
            "rerun",
        )
        for term in required_rev:
            if term not in content:
                failures.append(f"{filename}: missing {term!r}")

    # Only check agent files that actually exist (plugin stubs are minimal and do not
    # carry the forbidden wording).
    agent_paths = [
        PUBLIC / "agents" / filename
        for filename in (*IMPLEMENTERS, *REVIEWERS)
        if (PUBLIC / "agents" / filename).exists()
    ]
    old_wording_paths = [
        ORCHESTRATION_SKILL,
        TASK_MANAGER_SKILL,
        PROJECT_MANAGER,
        *agent_paths,
        *sorted((PUBLIC / "workflows").glob("*.workflow.md")),
    ]
    for path in old_wording_paths:
        content = _read(path)
        for phrase in FORBIDDEN_OLD_DONE_WORDING:
            if phrase in content:
                failures.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {phrase}")

    assert failures == []
