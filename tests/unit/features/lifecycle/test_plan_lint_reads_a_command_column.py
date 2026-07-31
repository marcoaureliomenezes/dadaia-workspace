"""The validation column asks for a command, so it must survive holding one.

Bug ``r24-live-definition-draft-fails-validation-table`` (validator R24 / F-26, R-01,
R-02 — three FAILs, one cause). ``PLAN.md`` below is the live artifact from the round-24
``f26`` canary workspace, written by a Codex worker doing exactly what the fragment asks:
naming a *direct validation command* per workstream. One of those commands is an ``rg``
invocation with alternation, so the cell contains ``|``. The lint split the row on every
pipe, counted seven cells, and blocked with:

    every validation dependency row must contain all five non-empty cells

Not one cell was empty. The worker had no way to act on that, rewrote the same table,
and the release sat at ``definition_draft`` — F-26, R-01 and R-02 all failed on it.

Two things are asserted here, and the second matters as much as the first: a correct
table passes, and a table that is *actually* wrong is told what is wrong about it. The
deadlock was not caused by strictness; it was caused by a diagnostic that named the
wrong defect, which no retry loop can recover from.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.features.lifecycle.test_release_definition_workflow import (
    _wf_with_plan,
)

pytestmark = pytest.mark.unit

_LIVE_PLAN = (
    "# PLAN: Add Python greeting CLI with docs and test\n\n"
    "**Status:** Draft\n\n"
    "## Validation Dependency Table\n\n"
    "| Workstream | Produces by end | Direct validation | Validation dependencies "
    "| Deferred integration evidence |\n"
    "|---|---|---|---|---|\n"
    "| WS-1 | CLI command `greet` implemented with required `name` arg "
    "| Manual CLI execution `python -m canary greet Ada` | None | None |\n"
    "| WS-2 | README contains `greet` usage and `Hello, Ada!` sample output section "
    '| `rg -n "\\bgreet\\b|python -m canary greet|Hello, Ada!" README.md` '
    "| WS-1 | Snapshot of updated docs section in review diff |\n"
    "| WS-3 | Test module validates formatting helper and CLI sample output contract "
    "| `pytest tests/test_greet.py -p no:cacheprovider` "
    "| WS-1 | Full pytest output evidence captured in implementation session |\n"
)


def test_the_live_plan_that_deadlocked_the_release_now_passes(tmp_path: Path) -> None:
    workflow = _wf_with_plan(tmp_path, _LIVE_PLAN)

    assert workflow._validate_plan_dependency_table() is None, (  # noqa: SLF001
        "this is the artifact the live worker produced; blocking it left the release "
        "with no reachable next move"
    )


def test_a_short_row_is_told_it_is_short_not_that_it_is_empty(tmp_path: Path) -> None:
    short = _LIVE_PLAN.replace(
        "| WS-1 | CLI command `greet` implemented with required `name` arg "
        "| Manual CLI execution `python -m canary greet Ada` | None | None |",
        "| WS-1 | CLI command | Manual CLI execution | None |",
    )
    workflow = _wf_with_plan(tmp_path, short)

    block = workflow._validate_plan_dependency_table()  # noqa: SLF001

    assert block is not None
    assert "4 cells" in block.reason and "expected 5" in block.reason
    assert "WS-1" in block.reason, "the author has to know which row to go and fix"


def test_an_empty_cell_is_named_by_its_column(tmp_path: Path) -> None:
    """The check the gate was built for still binds, and now says where to look."""
    blank = _LIVE_PLAN.replace(
        "| Manual CLI execution `python -m canary greet Ada` | None | None |",
        "|  | None | None |",
    )
    workflow = _wf_with_plan(tmp_path, blank)

    block = workflow._validate_plan_dependency_table()  # noqa: SLF001

    assert block is not None
    assert "Direct validation" in block.reason
    assert "WS-1" in block.reason
