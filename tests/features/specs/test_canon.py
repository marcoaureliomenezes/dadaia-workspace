"""``canon`` — the ONE canon predicate shared by TREE-8 and the pre-push gate."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.gitflow import DEFAULT, merge_frontmatter, read_gitflow
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.features.specs import canon
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
    """A job file under a candidate's `tasks/` is canon; a stray `tasks/` file is not; a
    closed candidate's `TASKS.md` still is."""
    assert canon_violations(
        [
            "releases/0.5.0/rc-9/tasks/job2.md",
            "releases/0.5.0/rc-8/TASKS.md",
            "releases/0.5.0/rc-9/tasks/notes.txt",
            "releases/0.5.0/rc-9/tasks/job2/extra.md",
        ]
    ) == ["releases/0.5.0/rc-9/tasks/notes.txt", "releases/0.5.0/rc-9/tasks/job2/extra.md"]


# --- the stubs and the schema loader ask their owners ---------------------------------

_PACKAGE = Path(canon.__file__).resolve().parents[2]


def _fresh(tmp_path: Path) -> Path:
    canon.scaffold(tmp_path, project_name="P")
    return tmp_path


def test_a_fresh_backlog_stub_is_the_stores_empty_render(tmp_path: Path) -> None:
    store = load_owner("dd-backlog-definition", "_backlog_store")
    stub = (_fresh(tmp_path) / "backlog" / "BACKLOG.json").read_text(encoding="utf-8")
    assert stub == store.render([])


def test_a_fresh_constitution_gitflow_block_is_the_one_merge_frontmatter_writes(
    tmp_path: Path,
) -> None:
    specs = _fresh(tmp_path)
    scaffolded = (specs / "constitution.md").read_text(encoding="utf-8")
    merge_frontmatter(specs, gitflow=DEFAULT)
    merged = (specs / "constitution.md").read_text(encoding="utf-8")
    assert read_gitflow(specs, scaffolded) == (DEFAULT, None)
    assert read_gitflow(specs, merged) == (DEFAULT, None)
    assert merged.split("---\n", 2)[2] == scaffolded.split("---\n", 2)[2]


def test_canon_holds_no_backlog_or_gitflow_literal() -> None:
    source = Path(canon.__file__).read_text(encoding="utf-8")
    assert '"active": []' not in source
    assert "backlog-v1" not in source
    assert "{principal:" not in source


def test_the_package_outside_the_skills_holds_no_second_schema_loader() -> None:
    holders = [
        p.relative_to(_PACKAGE).as_posix()
        for p in _PACKAGE.rglob("*.py")
        if "public" not in p.relative_to(_PACKAGE).parts
        and "def load_schema" in p.read_text(encoding="utf-8")
    ]
    assert holders == []


def test_a_fresh_specs_init_writes_these_stub_bytes(tmp_path: Path) -> None:
    specs = _fresh(tmp_path)
    constitution = (specs / "constitution.md").read_bytes()
    assert constitution.startswith(
        b"---\nspecs_pattern_version: 13\n"
        b"gitflow: {principal: main, integration: develop, work: feature/}\n---\n"
    )
    assert (specs / "backlog" / "BACKLOG.json").read_bytes() == (
        b'{"schema": "backlog-v1", "active": []}\n'
    )
