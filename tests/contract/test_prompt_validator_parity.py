"""No Python validator may demand what no fragment teaches.

This is the defect class that produced bugs in series, one per validator, for weeks:

* ``**Consumes:**`` — Python parsed it to write the consumed_backlog ledger and drive the
  closure removal; no fragment ever told the SPEC author to write the line. Live releases
  consumed nothing, then (once the check landed) blocked instead.
* contract bindings — ``plan-create`` required them, ``tasks-create`` FORBADE inventing
  them, and the TASKS review REQUIRED them; a PLAN approved without them trapped the author
  between two rules.
* ``-p no:cacheprovider`` — a deterministic TASKS lint rejected the command the author was
  never told to write.

Each was found only by a live worker failing, fixed one at a time. The pattern is
structural, not incidental: a rule enforced in Python and absent from the prompt is a bug
with a delay fuse. This test is the parity check, so the next one cannot ship.

It is deliberately a SMALL, explicit table rather than a clever scan: each row is a token
Python enforces plus the fragment that must teach it. Adding a validator means adding a
row — which is exactly the moment to remember the prompt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

_ROOT = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_FRAGMENTS = _ROOT / "public" / "lifecycle_fragments"

#: (token Python enforces, module enforcing it, fragment that must teach it, why it matters)
_PARITY: tuple[tuple[str, str, str, str], ...] = (
    (
        "**Consumes:**",
        "features/backlog/consumes.py",
        "release_definition/spec-create.md",
        "Python parses this line to write the consumed_backlog ledger and remove the items "
        "at closure; a SPEC without it consumes nothing",
    ),
    (
        "**Consumes:**",
        "features/backlog/consumes.py",
        "release_definition/spec-review.md",
        "an authoring rule with no reviewer check drifts back out",
    ),
    (
        "no:cacheprovider",
        "features/lifecycle/workflows/release_definition.py",
        "release_definition/tasks-create.md",
        "a deterministic TASKS lint rejects any pytest command without it",
    ),
    (
        "Validation Dependency Table",
        "features/lifecycle/workflows/release_definition.py",
        "release_definition/plan-create.md",
        "a Python lint blocks the step when the PLAN omits this section",
    ),
)


@pytest.mark.parametrize(
    ("token", "enforcer", "fragment", "why"),
    _PARITY,
    ids=[f"{row[0]}->{Path(row[2]).name}" for row in _PARITY],
)
def test_every_enforced_token_is_taught_by_its_fragment(
    token: str, enforcer: str, fragment: str, why: str
) -> None:
    enforcer_path = _ROOT / enforcer
    fragment_path = _FRAGMENTS / fragment
    assert enforcer_path.is_file(), f"enforcer moved: {enforcer}"
    assert fragment_path.is_file(), f"fragment moved: {fragment}"

    assert token in enforcer_path.read_text(encoding="utf-8"), (
        f"{enforcer} no longer mentions {token!r} — if the rule was dropped, drop this row "
        "too; if it was renamed, rename both sides together"
    )
    assert token in fragment_path.read_text(encoding="utf-8"), (
        f"{fragment} does not teach {token!r}, but {enforcer} enforces it. {why}. A worker "
        "cannot satisfy a rule nobody told it about: teach it in the fragment, or stop "
        "enforcing it in Python."
    )


def test_the_parity_table_is_not_empty() -> None:
    """A parity table that quietly empties out is the same as having no check at all."""
    assert len(_PARITY) >= 4
