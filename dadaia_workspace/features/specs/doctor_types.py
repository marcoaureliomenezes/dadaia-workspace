"""Shared leaf types for the SpecsDoctor decomposition (v0.1.55 FR1).

Pure leaf module: imports ONLY stdlib (``collections.abc`` / ``dataclasses`` / ``enum``).
It holds no I/O and no sibling-validator import, so the coordinator can depend on it without
pulling in ``spec_context`` or ``infrastructure``.

``PidProbe`` is re-homed here as a leaf alias (R-1). It is byte-identical to
``spec_context.lease.PidProbe`` (both are the bare callable ``Callable[[int], bool]``), so the
coordinator can type its ``pid_probe`` seam against this leaf and hold NO ``spec_context`` import
edge — the CAP-CRITICAL invariant that keeps ``features-no-cross-feature`` at 13.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

#: The PID-liveness seam type: ``pid -> is_alive``. Identical to ``spec_context.lease.PidProbe``
#: (a bare ``Callable[[int], bool]``); re-homed as a leaf so the coordinator holds no
#: ``spec_context`` import edge (R-1 cap invariant).
PidProbe = Callable[[int], bool]


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
