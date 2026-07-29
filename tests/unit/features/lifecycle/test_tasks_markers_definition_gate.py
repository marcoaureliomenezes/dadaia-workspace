"""release-definition must not approve a TASKS.md that implementation will reject.

Bug ``r10-approved-task-markers-rejected-by-implementation`` (consumer-side validator,
R10/R-01, live Codex): ``release-definition`` completed and approved a TASKS.md whose
tasks were written ``TASK-WS1 / TASK-WS2 / TASK-WS3``. ``implementation-reviews`` then
refused to start — "no recognizable task markers" — because its parser accepts ids
matching ``T-?[0-9]`` (``- [ ] T-1 - title`` and two other grammars) and nothing else.

The release was APPROVED and UNRUNNABLE at the same time. That is the producer/validator
drift this codebase keeps paying for: two sides holding private opinions about one
artifact. The definition gate now answers with the implementation's own regexes, so the
two cannot drift — a shared predicate, not a second copy of the rule.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.lifecycle.pipeline import _TASK_MARKER_LINE_RES

pytestmark = pytest.mark.unit

_ACCEPTED = [
    "- [ ] T-1 - do the thing",
    "- [ ] **T01 - do the thing**",
    "### [ ] T1 - do the thing",
    "[ ] T-2",
]

#: What the live worker actually wrote on R10/R-01.
_REJECTED = [
    "- [ ] TASK-WS1 - stand up the workspace",
    "- [ ] WS-1 - stand up the workspace",
    "### TASK-WS2 - build it",
]


def _recognized(line: str) -> bool:
    return any(pattern.match(line) is not None for pattern in _TASK_MARKER_LINE_RES)


@pytest.mark.parametrize("line", _ACCEPTED)
def test_the_documented_grammars_are_recognized(line: str) -> None:
    assert _recognized(line), f"a documented task form stopped parsing: {line!r}"


@pytest.mark.parametrize("line", _REJECTED)
def test_the_form_the_live_worker_wrote_is_not_recognized(line: str) -> None:
    """Pins the exact shape that broke the chain, so the fix is aimed at a real case."""
    assert not _recognized(line), (
        f"{line!r} now parses — if the grammar was deliberately widened, this test should "
        "be updated deliberately, not deleted"
    )


def _gate(text: str):
    import types

    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )

    stub = types.SimpleNamespace(
        _context="ctx", _release_id="v0.1.0", _current_run_id="rd", _default_kind=None
    )
    return ReleaseDefinitionWorkflow._unreadable_task_markers_block(stub, text)


def test_the_definition_gate_blocks_the_form_that_broke_the_chain() -> None:
    blocked = _gate("# TASKS\n\n- [ ] TASK-WS1 - stand up the workspace\n- [ ] TASK-WS2 - build\n")
    assert blocked is not None, "the definition approved a TASKS.md implementation refuses"
    assert "TASK-WS1" in str(blocked.detail) or "TASK-WS1" in blocked.reason
    assert "T-?<digits>" in blocked.reason, "the block must state the accepted grammar"
    assert blocked.operator_command, "a block without a remedy is a dead end"


def test_the_definition_gate_accepts_a_well_formed_tasks_file() -> None:
    assert _gate("# TASKS\n\n- [ ] T-1 - do the thing\n- [x] T-2 - done\n") is None


def test_a_tasks_file_with_no_checkboxes_is_left_to_the_artifact_gates() -> None:
    """Narrow on purpose: this check answers one question, not every TASKS.md defect."""
    assert _gate("# TASKS\n\nProse only, no checklist at all.\n") is None


def _through_the_wired_gate(text: str, tmp_path):
    """Exercise the WIRING, not just the predicate.

    The first version of these tests called the static helper directly — so deleting its
    call site left them all green. Mutation caught that; this goes through
    ``_validate_tasks_command_hygiene``, which is what the workflow actually runs.
    """
    import types

    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        ReleaseDefinitionWorkflow,
    )

    release = "v0.1.0"
    tasks = tmp_path / "releases" / release / "TASKS.md"
    tasks.parent.mkdir(parents=True, exist_ok=True)
    tasks.write_text(text, encoding="utf-8")
    stub = types.SimpleNamespace(
        _selector=types.SimpleNamespace(spec_context=types.SimpleNamespace(specs_dir=tmp_path)),
        _release_id=release,
        _context="ctx",
        _current_run_id="rd",
        _default_kind=None,
    )
    stub._unreadable_task_markers_block = lambda text: (
        ReleaseDefinitionWorkflow._unreadable_task_markers_block(stub, text)
    )
    return ReleaseDefinitionWorkflow._validate_tasks_command_hygiene(stub)


def test_the_wired_gate_blocks_unparseable_markers(tmp_path) -> None:
    blocked = _through_the_wired_gate(
        "# TASKS\n\n- [ ] TASK-WS1 - stand up the workspace\n", tmp_path
    )
    assert blocked is not None, "the marker check is not wired into the gate the workflow runs"
    assert blocked.detail.get("gate") == "task-marker-parity-v1"


def test_the_wired_gate_passes_a_well_formed_tasks_file(tmp_path) -> None:
    assert _through_the_wired_gate("# TASKS\n\n- [ ] T-1 - do the thing\n", tmp_path) is None
