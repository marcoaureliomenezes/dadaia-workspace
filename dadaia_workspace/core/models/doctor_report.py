"""Typed doctor report — the single severity/verdict authority for diagnostic surfaces.

Bug class (public-doctor-exits-zero-despite-error): diagnostic severity used to travel
as a string prefix (``"[error] ..."``) in a ``list[str]``, and every consumer re-derived
it by ``startswith`` against a CLOSED prefix list frozen at its own birth. A producer
emitting a vocabulary the consumer never learned fell into a decorative ``else`` branch
— printed, styled plain, and treated as harmless. The default was fail-open.

This module inverts that by construction:

- A producer cannot emit a line without choosing a :class:`DoctorStatus` member.
- Every member's blocking-ness is decided HERE, at declaration, in ``_BLOCKING`` —
  adding a status without deciding whether it blocks is unrepresentable.
- Consumers never parse: the verdict is :attr:`DoctorReport.blocking`, one authority.

``DoctorLine.render()`` reproduces the legacy wire format byte-for-byte (``[status] text``)
so golden byte-locks and human-facing output are unchanged by the migration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["DoctorLine", "DoctorReport", "DoctorStatus", "attest"]


class DoctorStatus(StrEnum):
    """Every status a doctor/check surface may emit. Value == legacy prefix token."""

    OK = "ok"
    DRIFT = "drift"
    MISSING = "missing"
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    FOREIGN = "foreign"
    EXTRA = "extra"
    LEAK = "leak"
    UNSUPPORTED = "unsupported"
    NOT_APPLICABLE = "not-applicable"
    SKIP = "skip"
    PRUNE = "prune"
    RM = "rm"

    @property
    def blocking(self) -> bool:
        """True iff this status must fail the run (exit non-zero)."""
        return self in _BLOCKING


#: The complete blocking policy, decided at declaration time — the ONE place severity
#: maps to a verdict. ``FOREIGN`` is deliberately non-blocking (Ruling 16: a
#: hand-authored consumer AGENTS.md/CLAUDE.md pair is legitimate operator authorship).
#: ``EXTRA`` blocks: unowned residue on a managed surface is drift, not decoration.
#: A contract test pins this exact set — changing it is a reviewed diff, never an accident.
_BLOCKING: frozenset[DoctorStatus] = frozenset(
    {
        DoctorStatus.ERROR,
        DoctorStatus.MISSING,
        DoctorStatus.DRIFT,
        DoctorStatus.LEAK,
        DoctorStatus.EXTRA,
    }
)


@dataclass(frozen=True)
class DoctorLine:
    """One diagnostic finding: a status chosen by the producer plus its message."""

    status: DoctorStatus
    text: str

    def render(self) -> str:
        """Legacy wire format, byte-identical to the historical string lines."""
        return f"[{self.status}] {self.text}"


@dataclass(frozen=True)
class DoctorReport:
    """An assembled diagnosis. The verdict lives here and nowhere else."""

    lines: tuple[DoctorLine, ...]

    @property
    def blocking(self) -> bool:
        """True iff any line's status blocks — the single exit-code authority."""
        return any(line.status.blocking for line in self.lines)

    def rendered(self) -> list[str]:
        """All lines in the legacy wire format (goldens, tests, display)."""
        return [line.render() for line in self.lines]


def attest(check_id: str, lines: list[DoctorLine]) -> list[DoctorLine]:
    """An ATTESTING check always speaks — silence is unrepresentable.

    Bug class (the vanished ``rule-corpus`` check): a check that emits ``[ok]`` only
    when it finds applicable objects disappears from the report the day its universe
    empties — indistinguishable from green. Wrap every attesting check's result: an
    empty result becomes an explicit ``[not-applicable] check:<id>`` line, so a golden
    diff shows the check going quiet instead of the check going missing.

    Issues-only checks (silence == healthy BY CONTRACT, e.g. drift scanners) are not
    wrapped — their healthy state is the absence of findings, not a positive claim.
    """
    if lines:
        return lines
    return [DoctorLine(DoctorStatus.NOT_APPLICABLE, f"check:{check_id} — no applicable objects")]
