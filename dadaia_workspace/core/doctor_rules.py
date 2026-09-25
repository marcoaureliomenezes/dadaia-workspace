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

Pure module — no I/O; its one internal edge is ``core.cli_line``, the CLI spelling.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import PurePath

from dadaia_workspace.core.cli_line import fix_line

__all__ = [
    "Rule",
    "SectionFinding",
    "SectionReport",
    "merge_sections",
    "render_finding",
    "rule_fix",
    "run_section",
]


@dataclass(frozen=True)
class SectionFinding:
    """One finding, normalized for rendering.

    ``verdict`` is the finding's OWN word — ``error``/``warning``/``info`` for the
    specs and ledgers sections, ``slop``/``expired``/``missing``/``operator``/``canon``
    for the workspace scan. There is no mapping table between the two vocabularies:
    each section prints what it classified.
    """

    code: str
    verdict: str
    message: str
    #: A canonical finding is not printed (the workspace scan classifies every entry it
    #: walks, including the compliant ones).
    canonical: bool
    #: An error-class finding makes the run exit 1.
    error: bool
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
    #: A shell line, or a workspace-CLI argv tuple that :func:`rule_fix` renders with
    #: ``fix_line`` from the doctored workspace's root (ADR 0045).
    fix_help: str | tuple[str, ...] | None = None


@dataclass(frozen=True)
class SectionReport:
    """One section's rendered findings."""

    name: str
    findings: tuple[SectionFinding, ...]

    @property
    def printable(self) -> tuple[SectionFinding, ...]:
        return tuple(f for f in self.findings if not f.canonical)

    @property
    def failed(self) -> bool:
        return any(f.error for f in self.findings)


def run_section[C, I](
    name: str,
    rules: Sequence[Rule[C, I]],
    context: C,
    render: Callable[[Rule[C, I], I], SectionFinding],
    root: PurePath | None,
) -> SectionReport:
    """Run every rule of one section over its context.

    ``render`` is the section's adapter at the seam: it translates the feature's own
    issue type into a :class:`SectionFinding`. *root* is the workspace a CLI remedy runs
    from (``None`` when no instance surrounds the run: the running CLI).
    """
    findings: list[SectionFinding] = []
    for rule in rules:
        for issue in rule.run(context):
            findings.append(_with_fix(render(rule, issue), rule, root))
    return SectionReport(name=name, findings=tuple(findings))


def merge_sections(reports: Sequence[SectionReport]) -> SectionReport:
    """Fold the parts of ONE section contributed by different features into one report:
    a section is not a feature, and two features that may not import each other still
    print under one name."""
    return SectionReport(
        name=reports[0].name,
        findings=tuple(f for report in reports for f in report.findings),
    )


def rule_fix[C, I](rule: Rule[C, I], root: PurePath | None) -> str:
    """*rule*'s remedy as one runnable line — the ONE render site of a rule's fix."""
    if isinstance(rule.fix_help, tuple):
        return fix_line(root, *rule.fix_help)
    return rule.fix_help or ""


def _with_fix[C, I](
    finding: SectionFinding, rule: Rule[C, I], root: PurePath | None
) -> SectionFinding:
    """Stamp the emitting rule's ``fix_help`` onto *finding*.

    0.4.7 FR2 — every BLOCK carries one executable fix. That every error-class rule
    carries a ``fix_help`` is proven statically, before the operator ever runs the
    doctor, by ``tests/contract/test_every_block_carries_a_fix.py``; raising here would
    turn a rule-authoring defect into a traceback, which is a refusal with no message
    at all.
    """
    return replace(finding, fix=finding.fix or rule_fix(rule, root))


def render_finding(finding: SectionFinding) -> str:
    """One finding, rendered: its line, plus the ``fix:`` line when it fails the run or
    is itself guidance (an ``info`` finding such as the onboarding next step)."""
    line = f"{finding.code} {finding.verdict} {finding.message}"
    shows_fix = finding.error or finding.verdict == "info"
    return f"{line}\nfix: {finding.fix}" if shows_fix and finding.fix else line
