"""``specs_canon`` — the ONE canon predicate shared by TREE-8 and the pre-push gate.

Intent: CONTRACT — v0.5.0 specs-canon closure, operator ruling 2026-08-28.
"""

from __future__ import annotations

from dadaia_workspace.features.specs.specs_canon import (
    canon_violations,
    is_canon_path,
    verdict_violations,
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
    "memory/TECHSTACK.md",
    "memory/product/index.md",
    "memory/product/catalog.json",
    "memory/product/sdd/specs-doctor.md",
    "releases/AGENTS.md",
    "releases/_ideas/AGENTS.md",
    "releases/_ideas/0.6.0/SPEC.md",
    "releases/_archive/releases_histo.jsonl",
    "releases/_archive/0.4.0/SPEC.md",
    "releases/_archive/0.4.0/nested/anything.txt",
    "releases/0.5.0/RELEASE.json",
    "releases/0.5.0/SPEC.md",
    "releases/0.5.0/PLAN.md",
    "releases/0.5.0/TASKS.md",
    "releases/0.5.0/verdicts/" + "a" * 40 + ".handoff.json",
    "backlog/AGENTS.md",
    "backlog/BACKLOG.json",
    "backlog/_archive/backlog_histo.jsonl",
    "backlog/_archive/consumed_backlog_histo.jsonl",
    "bugs/AGENTS.md",
    "bugs/BUGS.jsonl",
    "bugs/_archive/bugs_histo.jsonl",
    "audits/AGENTS.md",
    "audits/_archive/audits_histo.jsonl",
    "audits/20260827-canon-v6-first-audit/AUDIT.md",
    "audits/20260827-canon-v6-first-audit/FINDINGS.jsonl",
    "ADRs/AGENTS.md",
    "ADRs/decisions.jsonl",
    "ADRs/_superseded/superseded.jsonl",
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
    "releases/0.5.0/verdicts/not-a-sha.handoff.json",
    "memory/product/index.txt",
    "memory/product/orphan.md",
)


def test_every_canon_member_is_conformant() -> None:
    violations = [path for path in _CANON_PATHS if not is_canon_path(path)]
    assert violations == [], f"canon members wrongly rejected: {violations}"


def test_every_known_non_canon_path_is_rejected() -> None:
    accepted = [path for path in _NON_CANON_PATHS if is_canon_path(path)]
    assert accepted == [], f"non-canon paths wrongly accepted: {accepted}"


def test_canon_violations_is_order_preserving_and_filters_only_bad_paths() -> None:
    mixed = ["AGENTS.md", ".gitkeep", "backlog/BACKLOG.json", "SPEC.md"]
    assert canon_violations(mixed) == [".gitkeep", "SPEC.md"]


def test_canon_violations_over_a_fully_conformant_set_is_empty() -> None:
    assert canon_violations(_CANON_PATHS) == []


def test_canon_violations_over_a_fully_nonconformant_set_is_everything() -> None:
    assert canon_violations(_NON_CANON_PATHS) == list(_NON_CANON_PATHS)


# --------------------------------------------------------------------------- verdicts


def test_verdict_matching_head_is_not_a_violation() -> None:
    head = "b" * 40
    paths = [f"releases/0.5.0/verdicts/{head}.handoff.json"]
    assert verdict_violations(paths, head_sha=head, parent_sha=None) == []


def test_verdict_matching_parent_is_not_a_violation() -> None:
    head = "b" * 40
    parent = "c" * 40
    paths = [f"releases/0.5.0/verdicts/{parent}.handoff.json"]
    assert verdict_violations(paths, head_sha=head, parent_sha=parent) == []


def test_verdict_matching_neither_head_nor_parent_is_stale() -> None:
    head = "b" * 40
    parent = "c" * 40
    stale = "d" * 40
    path = f"releases/0.5.0/verdicts/{stale}.handoff.json"
    assert verdict_violations([path], head_sha=head, parent_sha=parent) == [path]


def test_at_most_one_matching_verdict_extras_are_violations() -> None:
    head = "b" * 40
    parent = "c" * 40
    head_path = f"releases/0.5.0/verdicts/{head}.handoff.json"
    parent_path = f"releases/0.5.0/verdicts/{parent}.handoff.json"
    result = verdict_violations([head_path, parent_path], head_sha=head, parent_sha=parent)
    # exactly one of the two matching verdicts survives as clean; the other is flagged.
    assert len(result) == 1
    assert result[0] in (head_path, parent_path)


def test_verdict_violations_ignores_non_verdict_shaped_paths() -> None:
    assert verdict_violations(["AGENTS.md", "backlog/BACKLOG.json"], head_sha="x", parent_sha=None) == []


def test_verdict_violations_with_no_parent_only_checks_head() -> None:
    head = "e" * 40
    other = "f" * 40
    path = f"releases/0.5.0/verdicts/{other}.handoff.json"
    assert verdict_violations([path], head_sha=head, parent_sha=None) == [path]
