"""The Validation Dependency Table the scaffolder asks for must actually be checked.

`specs release open` writes a `## Validation Dependency Table` into every PLAN.md, and
`dadaia-release-definition` tells the author to fill it — but nothing validated it. The
lint that used to lived in the demolished engine, and `core/markdown_table.split_row`,
written specifically to stop that lint's round-24 false diagnostic, was left called only
by its own test (bug plan-dependency-lint-unwired).

The round-24 lesson is baked into these cases: a cell holding a shell command with a `|`
inside a code span is ONE cell, not three. A gate that reports "every row must contain
all five non-empty cells" about a fully populated row is worse than no gate, because a
retry loop can only converge on a true diagnosis.
"""

from __future__ import annotations

from dadaia_workspace.features.specs.doctor_plan_table import dependency_table_issues

_HEADER = (
    "| Workstream | Produces by end | Direct validation | Validation dependencies "
    "| Deferred integration evidence |\n|---|---|---|---|---|\n"
)


def _plan(rows: str) -> str:
    return f"# PLAN\n\n## Validation Dependency Table\n\n{_HEADER}{rows}\n## Next\n"


def test_a_complete_row_passes() -> None:
    rows = "| WS-1 | the parser | `pytest tests/unit` | none | none |\n"

    assert dependency_table_issues(_plan(rows)) == []


def test_a_pipe_inside_a_code_span_is_not_a_cell_boundary() -> None:
    """The round-24 deadlock, verbatim: an honest shell command with a pipe in it."""
    rows = '| WS-1 | the parser | `rg -n "a|b|c" README.md` | none | none |\n'

    assert dependency_table_issues(_plan(rows)) == []


def test_an_empty_cell_is_reported_with_its_column_and_row() -> None:
    rows = "| WS-1 | the parser |  | none | none |\n"

    issues = dependency_table_issues(_plan(rows))

    assert len(issues) == 1
    assert "WS-1" in issues[0]
    assert "Direct validation" in issues[0], issues[0]


def test_a_row_with_the_wrong_number_of_cells_says_how_many_it_found() -> None:
    rows = "| WS-1 | the parser | `pytest` |\n"

    issues = dependency_table_issues(_plan(rows))

    assert len(issues) == 1
    assert "3" in issues[0] and "5" in issues[0], issues[0]


def test_an_unfilled_scaffold_row_is_reported() -> None:
    """The stub the scaffolder writes is a placeholder, not an answer."""
    rows = "| WS-1 | (deliverable of this segment) | (how it is validated in isolation) | none | none |\n"

    issues = dependency_table_issues(_plan(rows), phase="IMPLEMENTATION")

    assert issues, "an untouched scaffold placeholder must not read as a filled table"
    assert "placeholder" in issues[0].lower()


def test_a_plan_without_the_section_is_not_accused() -> None:
    """Only a PLAN that HAS the section is measured against it."""
    assert dependency_table_issues("# PLAN\n\n## Approach\n\ntext\n") == []


def test_a_section_with_no_rows_at_all_is_reported() -> None:
    issues = dependency_table_issues(
        f"# PLAN\n\n## Validation Dependency Table\n\n{_HEADER}\n## Next\n",
        phase="IMPLEMENTATION",
    )

    assert issues
    assert "no rows" in issues[0].lower()


def test_an_untouched_scaffold_does_not_warn_in_an_authoring_phase() -> None:
    """Bug fresh-release-scaffold-emits-spec-doctor-warnings-042, restated.

    A freshly opened release MUST be doctor-clean: the scaffolder and the doctor have to
    agree on the fresh state. The placeholder is the legitimate authoring state, so it is
    only worth reporting once the release is implementation-bound — exactly the rule
    SPEC-DOC-004 already applies to a Draft status. Structural damage (a row with the
    wrong cell count, or a genuinely empty cell) is reported in every phase, because no
    phase makes a broken table correct.
    """
    rows = "| WS-1 | (deliverable of this segment) | (how it is validated in isolation) | none | none |\n"

    assert dependency_table_issues(_plan(rows), phase="SPEC") == []
    assert dependency_table_issues(_plan(rows), phase="IMPLEMENTATION")


def test_structural_damage_is_reported_in_every_phase() -> None:
    broken = "| WS-1 | the parser |\n"

    assert dependency_table_issues(_plan(broken), phase="SPEC")
    assert dependency_table_issues(_plan(broken), phase="IMPLEMENTATION")
