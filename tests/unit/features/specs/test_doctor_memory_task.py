"""SPEC-DOC-047: memory is closure procedure, never a TASKS.md task.

Bug memory-gate-requires-closure-phase-that-spec-doc-024-forbids-before-last-task: the
gate allows ``specs/memory`` writes only in DEFINITION/CLOSURE, SPEC-DOC-024 refuses
CLOSURE with an open task, so a task whose write set names ``specs/memory`` can be
executed in no phase. The contradiction is refused where it is born — the TASKS.md.

Intent: CONTRACT — Arm B regression seam. Size: SMALL.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import SpecsDoctor

from .test_doctor_ledger_invariants import _by_code, _make_clean_specs_tree, _write_tasks

_RELEASE = "0.9.9"


@pytest.fixture(autouse=True)
def _no_memory_lint_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

    monkeypatch.setattr(MemoryValidator, "check_lint1_memory_atoms", lambda self: [])


def test_a_task_whose_write_set_names_specs_memory_is_refused(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _write_tasks(
        specs,
        _RELEASE,
        "- [x] T-999-01 — code.\n"
        "  Write set: dadaia_workspace/core/x.py.\n"
        "- [ ] T-999-02 — FR9 + CLOSURE: memory atoms.\n"
        "  Owner: product-engineer.\n"
        "  Write set: specs/memory/**, specs/releases/0.9.9/_RELEASE.json (phase only).\n",
    )

    issues = _by_code(SpecsDoctor(specs).check(), "SPEC-DOC-047")

    assert len(issues) == 1
    assert "T-999-02" in issues[0].description
    assert issues[0].path.endswith("TASKS.md")


def test_tasks_without_a_memory_write_set_are_silent(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path, _RELEASE)
    _write_tasks(
        specs,
        _RELEASE,
        "- [-] T-999-01 — code.\n  Write set: dadaia_workspace/core/x.py, tests/unit/x.py.\n"
        "- [ ] T-999-02 — docs mentioning specs/memory in prose, not as a write set.\n"
        "  Write set: dadaia_workspace/public/skills/dd-x/SKILL.md.\n",
    )

    assert _by_code(SpecsDoctor(specs).check(), "SPEC-DOC-047") == []
