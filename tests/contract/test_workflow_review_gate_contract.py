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


def test_project_orchestration_defines_full_done_gate() -> None:
    content = _read(ORCHESTRATION_SKILL)
    missing = [term for term in REQUIRED_GATE_TERMS if term not in content]
    assert missing == []


def test_task_manager_blocks_done_until_review_approval() -> None:
    content = _read(TASK_MANAGER_SKILL)
    assert "Implementação completa não é DONE" in content
    assert "qa-engineer" in content
    assert "code-reviewer" in content
    assert "security-reviewer" in content
    assert "Antes dessas aprovações, é proibido marcar `[x]`" in content
    assert "abrir PR" in content
    assert "fazer\ndeploy" in content
    assert "escrever `CLOSURE.md`" in content


def test_project_manager_enforces_pre_and_post_implementation_gates() -> None:
    content = _read(PROJECT_MANAGER)
    # Terms present in the current project-manager persona (9-agent surface).
    # "Before TASKS approval", "owning implementer(s)", "design-specialist",
    # and "implementation-complete" are no longer part of the PM persona wording
    # after the agent-surface-reduction; the gate is enforced through the
    # project-orchestration skill referenced below.
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
    assert missing == []


def test_implementer_personas_treat_completion_as_handoff() -> None:
    failures: list[str] = []
    for filename in IMPLEMENTERS:
        path = PUBLIC / "agents" / filename
        raw = _read(path)
        # Skip plugin stubs — they carry no implementer gate wording by design.
        if "plugin: true" in raw:
            continue
        content = _flat(path)
        required = (
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
        for term in required:
            if term not in content:
                failures.append(f"{filename}: missing {term!r}")
        if "implementation-complete" not in content and "completed" not in content:
            failures.append(f"{filename}: missing implementation completion wording")
        for term in LEAKAGE_TERMS:
            if term not in content:
                failures.append(f"{filename}: missing leakage term {term!r}")

    assert failures == []


def test_reviewer_personas_define_approve_reject_contracts() -> None:
    failures: list[str] = []
    for filename in REVIEWERS:
        content = _read(PUBLIC / "agents" / filename)
        required = (
            "Approval contract",
            "APPROVE",
            "REQUEST_CHANGES",
            "evidence",
            "paths",
            "rerun",
        )
        for term in required:
            if term not in content:
                failures.append(f"{filename}: missing {term!r}")

    assert failures == []


def test_old_done_gate_shortcuts_do_not_reappear() -> None:
    # Only check agent files that actually exist (plugin stubs are minimal and
    # do not carry the forbidden wording).
    agent_paths = [
        PUBLIC / "agents" / filename
        for filename in (*IMPLEMENTERS, *REVIEWERS)
        if (PUBLIC / "agents" / filename).exists()
    ]
    paths = [
        ORCHESTRATION_SKILL,
        TASK_MANAGER_SKILL,
        PROJECT_MANAGER,
        *agent_paths,
        *sorted((PUBLIC / "workflows").glob("*.workflow.md")),
    ]
    failures: list[str] = []
    for path in paths:
        content = _read(path)
        for phrase in FORBIDDEN_OLD_DONE_WORDING:
            if phrase in content:
                failures.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {phrase}")

    assert failures == []
