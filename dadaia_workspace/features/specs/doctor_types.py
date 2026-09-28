"""The specs doctor's severity and its one finding factory — pure, no I/O."""

from __future__ import annotations

from enum import StrEnum

from dadaia_workspace.core.doctor_rules import SectionFinding


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


def specs_finding(
    code: str,
    severity: Severity,
    description: str,
    path: str | None = None,
    fixable: bool = False,
    fix: str = "",
) -> SectionFinding:
    """One specs-doctor finding: its location closes the message and rides ``extra`` as
    ``path`` — the target ``doctor --fix`` repairs. ``fix`` is its own remedy when the
    doctor cannot repair it (the rule's ``fix_help`` otherwise)."""
    location = f" ({path})" if path else ""
    extra = (("path", path),) if path else ()
    return SectionFinding(
        code,
        severity.value,
        description + location,
        False,
        severity is Severity.ERROR,
        fix,
        fixable,
        extra,
    )


def finding_path(finding: SectionFinding) -> str | None:
    """The file a specs finding names, or ``None``."""
    return dict(finding.extra).get("path")
