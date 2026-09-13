"""The ONE doctor rule record and section collector (release 0.4.7 FR5, T-047-02).

Before this module the workspace had THREE doctors — ``dadaia doctor`` (zones),
``dadaia specs doctor`` (the SPEC-DOC rules) and ``dadaia backlog doctor`` (BL-*) —
each with its own command, option parsing, finding type, rendering grammar, exit rule
and compliance notion (two had none). That is the structural cause of the doctor bug
family: a record class nobody's doctor read (``archived-release-state-invalid-and-
unparseable-doctor-silent``), a CLI surface the subject registry could not anchor
(``backlog-subject-registry-lacks-top-level-doctor-cli-anchor``), and three renderings
that could each claim health independently.

One record type (:class:`Rule`), one normalized finding (:class:`SectionFinding`), one
collector (:func:`run_section`). A feature keeps its own module and its own issue type
and contributes a ``RULES`` tuple plus a ``render`` adapter at the seam; the CLI
composition root is the only place the three sections meet.

Compliance is one formula for all three sections: a section declares how many units it
scored (``total_units`` — entries, rules, records) and every non-canonical finding
names the unit it disqualifies; the numerator is the units nothing disqualified.

Pure module — no I/O, no dependencies outside the stdlib.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

__all__ = [
    "Rule",
    "SectionFinding",
    "SectionReport",
    "merge_sections",
    "render_finding",
    "run_section",
    "total_compliance",
    "total_line",
]


@dataclass(frozen=True)
class SectionFinding:
    """One finding, normalized for rendering and scoring.

    ``verdict`` is the finding's OWN word — ``error``/``warning``/``info`` for the
    specs and ledgers sections, ``slop``/``expired``/``missing``/``operator``/``canon``
    for the workspace scan. There is no mapping table between the two vocabularies:
    each section prints what it classified.
    """

    code: str
    verdict: str
    message: str
    #: A canonical finding counts toward the numerator and is not printed (the workspace
    #: scan classifies every entry it walks, including the compliant ones).
    canonical: bool
    #: An error-class finding makes the run exit 1.
    error: bool
    #: The compliance unit this finding disqualifies (entry path, rule code, record
    #: slug). ``None`` = a finding outside the scored set (a workspace invariant is not
    #: an entry).
    unit: str | None = None
    #: The ONE executable remediation (0.4.7 FR2). Mandatory on an error-class finding:
    #: an exit-1 finding with nothing to run is a Stall. Stamped from the emitting
    #: rule's ``fix_help`` by :func:`run_section` when the section left it empty.
    fix: str = ""


@dataclass(frozen=True)
class Rule[C, I]:
    """One doctor rule family: the codes it emits, the section it belongs to, how to run
    it over that section's context ``C``, and how to fix one of its issues ``I``."""

    codes: tuple[str, ...]
    section: str
    run: Callable[[C], list[I]]
    fix: Callable[[C, I], None] | None = None
    fix_help: str | None = None


@dataclass(frozen=True)
class SectionReport:
    """One section's rendered findings and its score line's numbers."""

    name: str
    unit: str
    findings: tuple[SectionFinding, ...]
    canonical: int
    total: int

    @property
    def percent(self) -> int:
        return (100 * self.canonical) // self.total if self.total else 100

    @property
    def printable(self) -> tuple[SectionFinding, ...]:
        return tuple(f for f in self.findings if not f.canonical)

    @property
    def failed(self) -> bool:
        return any(f.error for f in self.findings)

    def score_line(self) -> str:
        return (
            f"compliance({self.name}): {self.canonical}/{self.total} "
            f"{self.unit} canonical ({self.percent}%)"
        )


def run_section[C, I](
    name: str,
    unit: str,
    rules: Sequence[Rule[C, I]],
    context: C,
    render: Callable[[Rule[C, I], I], SectionFinding],
    total_units: int | None = None,
) -> SectionReport:
    """Run every rule of one section over its context and score it.

    ``render`` is the section's adapter at the seam: it translates the feature's own
    issue type into a :class:`SectionFinding` and names the compliance unit.
    A section that KNOWS its denominator (rules run, records read) passes
    ``total_units``; its numerator is that count minus the units a non-canonical
    finding disqualified. A section that CLASSIFIES every unit as it goes (the
    workspace scan emits one finding per entry it walked, compliant ones included)
    passes ``None``: every finding is a unit, and the canonical ones are the numerator.
    """
    findings: list[SectionFinding] = []
    for rule in rules:
        for issue in rule.run(context):
            findings.append(_with_fix(render(rule, issue), rule))
    scored = [f for f in findings if f.unit is not None]
    if total_units is None:
        canonical = sum(1 for f in scored if f.canonical)
        total_units = len(scored)
    else:
        canonical = max(total_units - len({f.unit for f in scored if not f.canonical}), 0)
    return SectionReport(
        name=name,
        unit=unit,
        findings=tuple(findings),
        canonical=canonical,
        total=total_units,
    )


def merge_sections(reports: Sequence[SectionReport]) -> SectionReport:
    """Fold the parts of ONE section contributed by different features into one report.

    A section is not a feature: `ledgers` is scored over the backlog document's records
    AND every other committed governance record, contributed by two features that may
    not import each other. Merging their reports at the composition root keeps one
    section, one grammar and one score line without any cross-feature reach-in — the
    numerators and denominators simply add, exactly as :func:`total_line` adds sections.
    """
    first = reports[0]
    return SectionReport(
        name=first.name,
        unit=first.unit,
        findings=tuple(f for report in reports for f in report.findings),
        canonical=sum(report.canonical for report in reports),
        total=sum(report.total for report in reports),
    )


def total_compliance(reports: Sequence[SectionReport]) -> SectionReport:
    """The run's total, as ONE report: the sections' numbers summed and scored by the
    same :attr:`SectionReport.percent` every section line uses.

    The human `compliance(total)` line and the `--json` total payload are two renderings
    of this one object. A second formula on either side is exactly how they came to
    disagree at a denominator that rounds up (1055/1056: floor 99, round 100).
    """
    return replace(merge_sections(reports), name="total", unit="checks")


def total_line(reports: Sequence[SectionReport]) -> str:
    """The run's final line."""
    return total_compliance(reports).score_line()


def _with_fix[C, I](finding: SectionFinding, rule: Rule[C, I]) -> SectionFinding:
    """Stamp the emitting rule's ``fix_help`` onto *finding*; refuse an unfixable error.

    0.4.7 FR2 — every BLOCK carries one executable fix. A doctor run exits 1 on an
    error-class finding, so an error-class rule with no ``fix_help`` would stop the
    operator with nothing to run. That is a rule-authoring defect, caught here at the
    one seam every finding passes through rather than by review.
    """
    fix = finding.fix or rule.fix_help or ""
    if finding.error and not fix:
        raise ValueError(
            f"doctor rule {'/'.join(rule.codes)} emits an error-class finding "
            f"({finding.code}) with no fix_help — an exit-1 finding must name one "
            "executable remediation (0.4.7 FR2)."
        )
    return replace(finding, fix=fix)


def render_finding(finding: SectionFinding) -> str:
    """One finding, rendered: its line, plus the ``fix:`` line when it fails the run."""
    line = f"{finding.code} {finding.verdict} {finding.message}"
    return f"{line}\nfix: {finding.fix}" if finding.error and finding.fix else line
