"""Intent: CONTRACT — the specs doctor's ledger invariants SPEC-DOC-024/026/030/041.

Bugs: spec-doc-030-audit-dir-rule-contradicts-dadaia-6-8-canon (audit dirs are
``<YYYYMMDD>-<slug>``), doctor-reads-phantom-specs-archive-releases-root (archived
releases live under ``specs/releases/_archive/``), sa-promote-has-no-verb#B25-6 (an open task in
CLOSURE is release.py's refusal, never a doctor code),
sa-spec-doc-033-duplicates-bugs-check#B8 (archive-overdue is one WARNING, fix
``bugs.py archive``).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import SpecsDoctor
from dadaia_workspace.features.specs.rules import RULES


@pytest.fixture(autouse=True)
def _skip_memory_lint_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

    monkeypatch.setattr(MemoryValidator, "check_lint1_memory_atoms", lambda self: [])


def _tree(root: Path, release_id: str = "0.1.10", phase: str = "IMPLEMENTATION") -> Path:
    specs = root / "specs"
    rel = specs / "releases" / release_id
    (rel / "rc-1").mkdir(parents=True)
    (specs / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    state = {"schema": "release-state-v1", "release": release_id, "phase": phase}
    state |= {"defined": None, "implemented": None, "shipped": None, "log": []}
    (rel / "_RELEASE.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
    for name in ("SPEC", "PLAN"):
        (rel / "rc-1" / f"{name}.md").write_text(f"# {name}\n\n**Status:** Approved\n", "utf-8")
    (rel / "rc-1" / "TASKS.md").write_text(
        "# Tasks\n\n**Status:** Approved\n\n- [-] T1 something\n- [ ] T2 other\n", encoding="utf-8"
    )
    return specs


def _archive(name: str) -> Callable[[Path], None]:
    def plant(specs: Path) -> None:
        rel = specs / "releases" / "_archive" / name
        rel.mkdir(parents=True)
        (rel / "SPEC.md").write_text("# Spec\n\n**Status:** Approved\n", encoding="utf-8")

    return plant


def _audits(*names: str) -> Callable[[Path], None]:
    def plant(specs: Path) -> None:
        for name in names:
            (specs / "audits" / name).mkdir(parents=True)

    return plant


def _draft_tasks(specs: Path) -> None:
    tasks = specs / "releases" / "0.1.10" / "rc-1" / "TASKS.md"
    tasks.write_text(tasks.read_text("utf-8").replace("Approved", "Draft"), encoding="utf-8")


def _nothing(specs: Path) -> None:
    pass


_CASES = [
    pytest.param(
        "0.1.10",
        "IMPLEMENTATION",
        _draft_tasks,
        "SPEC-DOC-024",
        "error",
        id="024-draft-tasks-in-impl",
    ),
    pytest.param("0.1.10", "IMPLEMENTATION", _nothing, "SPEC-DOC-024", None, id="024-coherent"),
    pytest.param(
        "0.1.10", "CLOSURE", _nothing, "SPEC-DOC-024", None, id="024-open-task-in-closure-B25-6"
    ),
    pytest.param(
        "0.1.10",
        "IMPLEMENTATION",
        _archive("0.1.10"),
        "SPEC-DOC-026",
        "error",
        id="026-dup-id-in-archive",
    ),
    pytest.param(
        "0.1.10", "IMPLEMENTATION", _archive("v0.1.9"), "SPEC-DOC-026", None, id="026-distinct-ids"
    ),
    pytest.param(
        "0.1.10",
        "IMPLEMENTATION",
        _audits("2026-07-01T000000Z"),
        "SPEC-DOC-030",
        "warning",
        id="030-bad-name",
    ),
    pytest.param(
        "0.1.10",
        "IMPLEMENTATION",
        _audits("20260827-canon-v6-first-audit"),
        "SPEC-DOC-030",
        None,
        id="030-yyyymmdd-slug-canon",
    ),
    pytest.param(
        "0.1.10",
        "IMPLEMENTATION",
        _audits(
            "2026-06-09T075056Z",
            "2026-06-10T010550Z",
            "2026-06-10T052944Z",
            "2026-06-10T140553Z",
            "_archive",
        ),
        "SPEC-DOC-030",
        None,
        id="030-grandfathered",
    ),
    pytest.param(
        "0.1.10", "IMPLEMENTATION", _nothing, "SPEC-DOC-030", None, id="030-no-audits-dir"
    ),
]


@pytest.mark.parametrize(("release_id", "phase", "plant", "code", "verdict"), _CASES)
def test_ledger_invariant(
    tmp_path: Path,
    release_id: str,
    phase: str,
    plant: Callable[[Path], None],
    code: str,
    verdict: str | None,
) -> None:
    specs = _tree(tmp_path, release_id, phase)
    plant(specs)
    verdicts = {i.verdict for i in SpecsDoctor(specs).check() if i.code == code}
    assert verdicts == ({verdict} if verdict else set())


def test_doc041_archive_overdue_is_one_warning_fixed_by_bugs_archive(tmp_path: Path) -> None:
    """sa-spec-doc-033-duplicates-bugs-check#B8."""
    specs = _tree(tmp_path)
    (specs / "bugs").mkdir()
    closed = {"id": "old", "status": "resolved", "closed_at": "2026-01-01T00:00:00Z"}
    (specs / "bugs" / "BUGS.jsonl").write_text(json.dumps(closed) + "\nnot json {\n")
    [doc041] = [i for i in SpecsDoctor(specs).check() if i.code == "SPEC-DOC-041"]
    [rule] = [r for r in RULES if "SPEC-DOC-041" in r.codes]
    assert doc041.verdict == "warning" and "bugs.py archive" in str(rule.fix_help)
