"""Pure reference implementation of the SDD gate's path-classifier + decision (v0.1.6).

The enforced gate is ``public/scripts/sdd-spec-gate.sh`` (bash, ≤175 lines) which
classifies paths inline for performance — most PreToolUse calls touch ADDITIVE or
UNGATED paths and must not pay a Python-startup cost. This module is the
**executable specification** of that policy: the fail-safe property table (AC-04)
and the activity-class exemption matrix (AC-05) are unit-tested against it, and
qa-engineer (T-016-08) verifies the bash gate mirrors it exactly.

For the MUTATING class the gate is the single acquisition point: it delegates to
:func:`lease.acquire` (O_EXCL CAS). This module does the same, so the Python tests
exercise the real lease code path, not a stand-in.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from dadaia_workspace.core.exceptions import LockHeldError
from dadaia_workspace.features.spec_context import lease

__all__ = ["Decision", "PathClass", "classify_path", "evaluate"]

#: Ordered ADDITIVE prefixes — always allowed (never blocked, never locked).
#: specs/audits/ is ADDITIVE (FR-P1-14/D2): parallel audit sessions write here
#: without a MUTATING lease. Audit dirs use collision-safe naming per FR-P1-16:
#:   specs/audits/<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/
_ADDITIVE_PREFIXES: tuple[str, ...] = (
    "specs/backlog/",
    "specs/bugs/",
    "specs/audits/",
    ".dadaia/reports/",
    ".dadaia/handoff/",
    ".dadaia/tmp/",
)
_MEMORY_PREFIX = "specs/memory/"
_FROZEN_PREFIX = "specs/_archive/"
#: Phases in which product-engineer may write memory atoms (FR-P1-13).
_MEMORY_WRITE_PHASES: frozenset[str] = frozenset({"DEFINITION", "CLOSURE"})


class PathClass(Enum):
    ADDITIVE = "ADDITIVE"
    MEMORY = "MEMORY"
    FROZEN = "FROZEN"
    MUTATING = "MUTATING"
    UNGATED = "UNGATED"


class Decision(Enum):
    ALLOW = "allow"
    BLOCK = "block"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def classify_path(rel_path: str) -> PathClass:
    """Classify a workspace-relative path. Ordered; first match wins (FR-P1-05)."""
    p = rel_path.lstrip("/")
    for prefix in _ADDITIVE_PREFIXES:
        if p.startswith(prefix):
            return PathClass.ADDITIVE
    if p.startswith(_MEMORY_PREFIX):
        return PathClass.MEMORY
    if p.startswith(_FROZEN_PREFIX):
        return PathClass.FROZEN
    if p.startswith("specs/releases/") or p.startswith("repos/"):
        return PathClass.MUTATING
    return PathClass.UNGATED


def evaluate(
    workspace: Path,
    rel_path: str,
    *,
    ctx: str,
    phase: str,
    session_id: str,
    release: str,
    mode: str,
    clock: Callable[[], datetime] = _utcnow,
) -> tuple[Decision, str]:
    """Return the gate decision for one write target — the fail-safe contract.

    Guarantees (AC-04): the return is always one of {ALLOW, BLOCK-with-actionable-
    message}; never an unhandled exception.

    MUTATING paths are BLOCKed on a live foreign lease (yield-iff-live-foreign,
    FR-P1-15): the block message is always actionable (never "bind --mode write",
    never "relaunch"). A relaunched session with a matching ``.ptr`` is recognised
    as the incumbent and RENEWs (never blocks). The flow only stops on a genuinely
    concurrent foreign live session — and even then, additive writes are unblocked.
    """
    cls = classify_path(rel_path)

    if cls in (PathClass.ADDITIVE, PathClass.UNGATED):
        return Decision.ALLOW, ""

    if cls == PathClass.FROZEN:
        return Decision.BLOCK, f"[RULE B] '{rel_path}' is a frozen archive path (read-only)."

    if cls == PathClass.MEMORY:
        if phase in _MEMORY_WRITE_PHASES:
            return Decision.ALLOW, ""
        return Decision.BLOCK, (
            f"[RULE A] memory writes are allowed only in DEFINITION or CLOSURE phase "
            f"(current phase={phase})."
        )

    # MUTATING — the gate is the single acquisition point (O_EXCL CAS in lease).
    try:
        lease.acquire(workspace, ctx, session_id, release, mode, clock=clock)
    except LockHeldError as exc:
        return Decision.BLOCK, str(exc)
    return Decision.ALLOW, ""
