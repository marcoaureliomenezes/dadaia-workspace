"""Shared leaf types for the SpecsDoctor decomposition (v0.1.55 FR1).

Pure leaf module: imports ONLY stdlib (``dataclasses`` / ``enum``). It holds no I/O and no
sibling-validator import, so the coordinator can depend on it without pulling in
``spec_context`` or ``infrastructure``.

v0.1.76 T-4: the ``PidProbe`` leaf alias (formerly re-homed here for the SPEC-DOC-029
``pid_probe`` composition-root seam, R-1) is REMOVED — SPEC-DOC-029 is retired (see
``doctor_coherence.py``) and nothing else in the SpecsDoctor decomposition consumed it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class SpecsDoctorIssue:
    code: str
    severity: Severity
    description: str
    path: str | None = None
    fixable: bool = False

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "description": self.description,
            "path": self.path,
        }


@dataclass
class _MemoryMdSummary:
    has_heading: bool
    heading_text: str
    forbidden_h2: list[str]
    frontmatter: dict | None  # type: ignore[type-arg]
    body: str
