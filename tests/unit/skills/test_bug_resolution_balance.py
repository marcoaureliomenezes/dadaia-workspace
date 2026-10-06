"""AC4.1-AC4.3 (release 0.5.0 candidate 10, Job 4): `_bugs_balance.render` turns the ledger's
records alone into the `## Bugs` block — the per-surface table, the Laplace trend over days
(Kanoun & Laprie) and the defective-fix rate per rc (Kan). Pure: records in, text out."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from dadaia_workspace.infrastructure.ledger_scripts import load_owner

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_SRC = _PUBLIC / "skills" / "dd-bug-resolution" / "scripts" / "_bugs_balance.py"
_ORDER = ["0.4.5", "0.4.6", "0.4.7", "0.4.8", "0.5.0"]
_START, _END = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 11, tzinfo=UTC)


def _balance() -> ModuleType:
    assert _SRC.is_file(), "_bugs_balance.py is not built yet"
    return load_owner("dd-bug-resolution", "_bugs_balance")


def _bug(surface: str, day: int, found: tuple[str, str] | None, **more: Any) -> dict[str, Any]:
    record: dict[str, Any] = {"surface": surface, "ts": f"2026-01-{day:02d}T00:00:00Z", **more}
    if found:
        record["found_in"] = {"release": found[0], "rc": found[1]}
    return record


_LIVE = [
    _bug("core", 2, ("0.5.0", "rc-1"), caused_by="none"),
    _bug("core", 3, ("0.5.0", "rc-1"), caused_by="a-bug"),
    _bug("core", 4, ("0.5.0", "rc-2"), caused_by=None),
    _bug("tests", 5, ("unknown", "unknown")),
    _bug("unknown", 5, None),
    _bug("cli", 5, ("0.5.0", "unknown"), correlates=["x", "y"]),
    _bug("unknown", 5, ("unknown", "unknown")),
    _bug("cli", 1, ("0.4.5", "rc-1")),
]
_ARCHIVED = [_bug("cli", 5, ("unknown", "unknown"))]
_BLOCK = """\
Bug balance from BUGS.jsonl: 9 records (8 live, 1 archived).
surface  records  recurrences  fix-induced  archived  rcs  correlates  settled
cli      3        2            0            1         0    2           no
core     3        2            1            0         2    0           no
unknown  2        -            0            0         0    0           -
dev-tooling:
tests    1        0            0            0         0    0           yes
Laplace trend (days), window 0.4.6..0.5.0, T = 10 days: u = -1.73, no trend
  counted 4 of 9 records; apart: 3 release unknown, 1 no found_in, 1 outside the window
  records found on an already settled surface: 1
Defective-fix rate per rc (caused_by set over found in the rc):
0.4.5/rc-1  0/1  0%
0.5.0/rc-1  1/2  50%
0.5.0/rc-2  0/1  0%
"""


def test_a_literal_ledger_renders_a_literal_block_and_a_rerun_is_byte_equal() -> None:
    bal = _balance()
    window = bal.Window(_ORDER, _START, _END)

    block = bal.render(_LIVE, _ARCHIVED, window, frozenset({"tests"}))

    assert block == _BLOCK
    assert bal.render(_LIVE, _ARCHIVED, window, frozenset({"tests"})) == block


@pytest.mark.parametrize(
    ("days", "reading"),
    [
        ([1, 2, 3], "u = -1.80, no trend"),
        ([1, 1, 1, 1], "u = -2.77, converging"),
        ([9, 9, 9, 9], "u = 2.77, diverging"),
        ([1, 1, 1, 3, 4, 5, 5], "u = -1.96, converging"),
        ([9, 9, 9, 7, 6, 5, 5], "u = 1.96, diverging"),
        ([], "u = n/a, no data"),
    ],
)
def test_the_laplace_trend_reads_days_against_the_window_length(
    days: list[int], reading: str
) -> None:
    bal = _balance()
    live = [_bug("core", 1 + d, ("0.5.0", "rc-1")) for d in days]

    block = bal.render(live, [], bal.Window(_ORDER, _START, _END), frozenset())

    [trend] = [ln for ln in block.splitlines() if ln.startswith("Laplace")]
    assert trend.endswith(f"T = 10 days: {reading}")


def test_a_record_is_counted_on_a_settled_surface_once_the_previous_one_left_the_bug_window() -> (
    None
):
    bal = _balance()
    order = [f"0.4.{n}" for n in range(1, 8)]  # the trend window is the last four: 0.4.4-0.4.7
    #: (surface, release index), oldest first: a and d and e settle (a gap of 2 or more landing
    #: in the window), b has a gap of 1, c a gap of 2 landing before the window
    found = [("a", 3), ("a", 5), ("b", 4), ("b", 5), ("c", 0), ("c", 2), ("d", 3), ("d", 6)]
    found += [
        ("e", 1),
        ("e", 3),
        ("unknown", 3),
        ("unknown", 6),
    ]  # an unknown surface never settles
    live = [_bug(s, 1 + i, (order[n], "rc-1")) for i, (s, n) in enumerate(found)]

    block = bal.render(live, [], bal.Window(order, _START, _END), frozenset())

    assert "  records found on an already settled surface: 3" in block.splitlines()


def test_the_block_is_set_under_bugs_and_the_section_is_appended_when_absent() -> None:
    bal = _balance()
    doc = "# Q\n\n## Bugs\n\nlead\n```text\nold\n```\ntrail\n\n## Other\n\n```text\nkeep\n```\n"

    assert bal.stored(doc) == "old\n"
    assert bal.replaced(doc, "new\n") == doc.replace("old", "new")
    assert bal.stored("# Q\n\n## Other\n\n```text\nkeep\n```\n") is None
    assert bal.replaced("# Q\n", "new\n") == "# Q\n\n## Bugs\n\n```text\nnew\n```\n"
    assert bal.replaced("", "new\n") == "## Bugs\n\n```text\nnew\n```\n"


def test_the_block_goes_right_after_an_existing_bugs_heading_that_holds_none() -> None:
    bal = _balance()
    doc = "# Q\n\n## Bugs\n\nwritten review\n\n## Other\n"

    assert bal.replaced(doc, "new\n") == (
        "# Q\n\n## Bugs\n\n```text\nnew\n```\n\nwritten review\n\n## Other\n"
    )


def test_the_rates_sort_rcs_by_number_not_by_text() -> None:
    bal = _balance()
    live = [
        _bug("core", 2, ("0.5.0", "rc-10"), caused_by="a-bug"),
        _bug("core", 3, ("0.5.0", "rc-9")),
        _bug("core", 4, ("0.5.0", "rc-2")),
    ]

    block = bal.render(live, [], bal.Window(_ORDER, _START, _END), frozenset())

    assert block.splitlines()[-3:] == [
        "0.5.0/rc-2  0/1  0%",
        "0.5.0/rc-9  0/1  0%",
        "0.5.0/rc-10  1/1  100%",
    ]


def test_replaced_touches_the_first_block_only_and_parts_a_review_that_abuts_the_heading() -> None:
    bal = _balance()
    twice = "## Bugs\n\n```text\na\n```\n\n## Bugs\n\n```text\nb\n```\n"

    assert bal.replaced(twice, "new\n") == twice.replace("a\n", "new\n", 1)
    assert bal.replaced("## Bugs\nwritten review\n", "new\n") == (
        "## Bugs\n\n```text\nnew\n```\n\nwritten review\n"
    )


def test_stored_never_reads_the_block_of_another_section() -> None:
    bal = _balance()
    doc = "# Q\n\n## Bugs\n\nreview\n\n## Notes\n\n```text\nkeep\n```\n"

    assert bal.stored(doc) is None
    assert bal.replaced(doc, "new\n") == doc.replace(
        "## Bugs\n", "## Bugs\n\n```text\nnew\n```\n", 1
    )
