"""PLAN Validation Dependency Table lint (SPEC-DOC-041).

`specs release open` writes a `## Validation Dependency Table` into every PLAN.md and the
release-definition skill tells the author to fill it — but after the workflow engine was
demolished nothing validated it any more, and `core.markdown_table.split_row` (written
precisely to stop that lint's round-24 false diagnostic) was left called only by its own
test. Bug ``plan-dependency-lint-unwired``.

The round-24 lesson is the whole reason this module reads cells through ``split_row``
rather than ``line.split("|")``: the column exists to hold shell commands, and a pipe
inside an inline code span is not a cell boundary. A gate that reports "every row must
contain all five non-empty cells" about a fully populated row is worse than no gate,
because the author can only converge on a diagnosis that is true.
"""

from __future__ import annotations

from dadaia_workspace.core.markdown_table import split_row

#: The section this lint measures. A PLAN without it is simply not measured.
SECTION = "## Validation Dependency Table"

#: The five columns the scaffolded header declares, in order.
COLUMNS: tuple[str, ...] = (
    "Workstream",
    "Produces by end",
    "Direct validation",
    "Validation dependencies",
    "Deferred integration evidence",
)


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(set(cell.strip()) <= {"-", ":"} and cell.strip() for cell in cells)


def _is_header(cells: list[str]) -> bool:
    return [cell.strip() for cell in cells] == list(COLUMNS)


def _placeholder(cell: str) -> bool:
    """A scaffold stub still wearing its parentheses is a prompt, not an answer."""
    text = cell.strip()
    return text.startswith("(") and text.endswith(")")


def dependency_table_issues(plan_text: str, *, phase: str | None = None) -> list[str]:
    """Human-readable problems with the PLAN's dependency table; empty when sound.

    Each message names the offending row and column so a second attempt written only
    from the message would pass (recipe R-27).

    ``phase`` gates the PLACEHOLDER finding only. A freshly opened release must be
    doctor-clean — the scaffolder and the doctor have to agree on the fresh state (bug
    ``fresh-release-scaffold-emits-spec-doctor-warnings-042``) — so an untouched stub is
    the legitimate authoring state and is reported only once the release is
    implementation-bound, exactly as SPEC-DOC-004 already treats a Draft status.
    Structural damage is reported in every phase: no phase makes a broken table correct.
    """
    implementation_bound = (phase or "").upper() in ("IMPLEMENTATION", "CLOSURE")
    if SECTION not in plan_text:
        return []

    body = plan_text.split(SECTION, 1)[1]
    issues: list[str] = []
    data_rows = 0

    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            break
        if not line.startswith("|"):
            continue
        cells = split_row(line)
        if _is_separator(cells) or _is_header(cells):
            continue

        data_rows += 1
        label = cells[0].strip() if cells else "(unnamed row)"
        if len(cells) != len(COLUMNS):
            issues.append(
                f"row {label!r} has {len(cells)} cell(s); the table declares "
                f"{len(COLUMNS)} columns ({', '.join(COLUMNS)}). A pipe inside an inline "
                "code span does NOT split a cell — escape a literal pipe as `\\|`."
            )
            continue
        for column, cell in zip(COLUMNS, cells, strict=True):
            if not cell.strip():
                issues.append(f"row {label!r} leaves the {column!r} column empty.")
            elif _placeholder(cell) and implementation_bound:
                issues.append(
                    f"row {label!r} still carries the scaffold placeholder "
                    f"{cell.strip()!r} in the {column!r} column."
                )

    if data_rows == 0 and implementation_bound:
        issues.append(f"{SECTION} has no rows: the section was scaffolded and never filled in.")
    return issues
