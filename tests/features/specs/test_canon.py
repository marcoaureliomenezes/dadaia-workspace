"""``canon`` — the ONE canon predicate shared by TREE-8 and the pre-push gate."""

from __future__ import annotations

from dadaia_workspace.features.specs.canon import (
    canon_violations,
    is_canon_path,
)

# Every canon-conformant path this task's canon names, one per member — the positive
# fixture both `test_every_canon_member_is_conformant` and the doctor/push-gate tests
# reuse.
_CANON_PATHS: tuple[str, ...] = (
    "AGENTS.md",
    "constitution.md",
    "memory/AGENTS.md",
    "memory/ARCHITECTURE.md",
    "memory/QUALITY.md",
    "memory/product/index.md",
    "memory/product/catalog.json",
    "memory/product/sdd/specs-doctor.md",
    "releases/AGENTS.md",
    "releases/_archive/releases_histo.jsonl",
    "releases/_archive/0.4.0/SPEC.md",
    "releases/_archive/0.4.0/nested/anything.txt",
    "releases/0.5.0/_RELEASE.json",
    "releases/0.5.0/rc-1/SPEC.md",
    "releases/0.5.0/rc-1/PLAN.md",
    "releases/0.5.0/rc-1/TASKS.md",
    "backlog/AGENTS.md",
    "backlog/BACKLOG.json",
    "backlog/_archive/backlog_histo.jsonl",
    "bugs/AGENTS.md",
    "bugs/BUGS.jsonl",
    "bugs/_archive/bugs_histo.jsonl",
    "audits/AGENTS.md",
    "audits/_archive/audits_histo.jsonl",
    "audits/20260827-canon-v6-first-audit/AUDIT.md",
    "audits/20260827-canon-v6-first-audit/FINDINGS.jsonl",
    "ADRs/AGENTS.md",
    "ADRs/decisions.jsonl",
)

# Real-shape drift this task's canon explicitly excludes — one per class of violation
# the predicate must catch.
_NON_CANON_PATHS: tuple[str, ...] = (
    ".gitkeep",
    "memory/.gitkeep",
    "backlog/remote-bugs/some-bug.md",
    "releases/0.5.0/reviews/S1-AR1-ruling.md",
    "ADRs/0001-features-depend-on-ports.md",
    "SPEC.md",
    "foundation/vision.md",
    "backlog/loose-entry.md",
    "bugs/some-bug.md",
    "audits/orphan-file.md",
    "memory/product/index.txt",
    "memory/product/orphan.md",
)


def test_every_canon_member_is_conformant() -> None:
    violations = [path for path in _CANON_PATHS if not is_canon_path(path)]
    assert violations == [], f"canon members wrongly rejected: {violations}"


def test_every_known_non_canon_path_is_rejected() -> None:
    accepted = [path for path in _NON_CANON_PATHS if is_canon_path(path)]
    assert accepted == [], f"non-canon paths wrongly accepted: {accepted}"


def test_canon_violations_keeps_only_the_bad_paths_in_order() -> None:
    mixed = ["AGENTS.md", ".gitkeep", "backlog/BACKLOG.json", "SPEC.md"]
    assert canon_violations(mixed) == [".gitkeep", "SPEC.md"]
    assert canon_violations(_CANON_PATHS) == []
    assert canon_violations(_NON_CANON_PATHS) == list(_NON_CANON_PATHS)


def test_a_job_file_is_canon_beside_a_closed_rcs_tasks_file() -> None:
    """AC1.9 (ADR 0194): `rc-<N>/tasks/<job>.md` is canon; a stray `tasks/` file is not; a
    closed rc's `TASKS.md` still is."""
    assert canon_violations(
        [
            "releases/0.5.0/rc-9/tasks/job2.md",
            "releases/0.5.0/rc-8/TASKS.md",
            "releases/0.5.0/rc-9/tasks/notes.txt",
            "releases/0.5.0/rc-9/tasks/job2/extra.md",
        ]
    ) == ["releases/0.5.0/rc-9/tasks/notes.txt", "releases/0.5.0/rc-9/tasks/job2/extra.md"]
