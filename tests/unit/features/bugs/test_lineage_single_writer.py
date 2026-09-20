"""Lineage is declared at ``dadaia bugs resolve`` and nowhere else (0.4.7 FR1): the
``dadaia bugs update --set caused_by=…`` arm is not merely validated, it is REFUSED —
one writer, so ``BugService._validate_caused_by`` at ``transition`` is the ONE
validation site and cannot be bypassed.

Intent: CONTRACT — FR1 (audit C10, the two-writer finding). Size: SMALL — real
``tmp_path`` filesystem, no subprocess/network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.bugs.service import BugService

from ._bug_record_helpers import bug_record_store


def _service(tmp_path: Path) -> BugService:
    service = BugService(bug_record_store(tmp_path))
    service.register(
        bug_id="a",
        ts="2026-08-27T00:00:00Z",
        reported_by="dd-software-engineer",
        title="t",
        severity="HIGH",
        surface="bugs",
        component="c",
        context="dadaia-workspace",
        symptom="s",
        repro="r",
        expected="e",
    )
    return service


@pytest.mark.parametrize("value", ["not-a-bug", "none", "a"])
def test_apply_update_refuses_caused_by_whatever_its_value(tmp_path: Path, value: str) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError) as excinfo:
        service.apply_update("a", {"caused_by": value})

    message = str(excinfo.value)
    assert "caused_by" in message
    assert "fix: .dadaia/.venv/bin/dadaia bugs resolve a --caused-by <bug-id|none>" in message


def test_apply_update_refusal_leaves_the_record_untouched(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError):
        service.apply_update("a", {"audited": "x", "caused_by": "a"})

    (record,) = service.status(include_closed=True)
    assert record.caused_by is None
    assert record.audited is None
