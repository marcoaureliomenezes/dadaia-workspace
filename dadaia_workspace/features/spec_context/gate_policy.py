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

The PROTECTED class (SEC-01, F-07) is the sole fail-CLOSED path: writes to
``.dadaia/sessions/`` (the CLI-owned lease-identity store) are blocked unconditionally
and evaluated BEFORE any fail-open branch, protecting the ``.ptr`` from forgery
(confused-deputy / CWE-284). The Python hook ``dadaia_workspace.hooks.sdd_gate``
delegates here — PROTECTED flows through without reimplementation in the hook.
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
#: SEC-01 (CWE-284): .dadaia/sessions/ holds CLI-owned runtime session state, incl. the
#: single-session lease identity pointer (.dadaia/sessions/runtime/<ctx>.ptr). Agents must
#: NOT write these via Write/Edit — only the dadaia CLI/bootstrap may (it writes via Python,
#: outside the tool gate). This is the SOLE fail-CLOSED class: it blocks unconditionally,
#: evaluated BEFORE the fail-open branches below.
_PROTECTED_PREFIX = ".dadaia/sessions/"
#: SEC-01 block reason — byte-identical to ``sdd-spec-gate.sh`` so both enforcement paths
#: emit the same message (parity contract, T-018-15/T-018-16).
_PROTECTED_MESSAGE = (
    "[GATE] .dadaia/sessions/ is CLI-owned runtime state, incl. the single-session lease "
    "identity pointer .dadaia/sessions/runtime/<ctx>.ptr. Agents must not write here via "
    "Write/Edit — only the dadaia CLI/bootstrap may. Blocked to protect lease-identity "
    "integrity (the sole deterministic lock); forging the .ptr would let a second session "
    "steal a Spec Context binding (SEC-01 / CWE-284)."
)
#: Phases in which product-engineer may write memory atoms (FR-P1-13).
_MEMORY_WRITE_PHASES: frozenset[str] = frozenset({"DEFINITION", "CLOSURE"})


class PathClass(Enum):
    ADDITIVE = "ADDITIVE"
    MEMORY = "MEMORY"
    FROZEN = "FROZEN"
    MUTATING = "MUTATING"
    PROTECTED = "PROTECTED"
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
    if p.startswith(_PROTECTED_PREFIX):
        return PathClass.PROTECTED
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

    # PROTECTED is the SOLE fail-CLOSED class (SEC-01). It is evaluated FIRST — before any
    # fail-open branch — so an agent write to .dadaia/sessions/ is blocked unconditionally,
    # protecting the lease-identity .ptr from forgery (confused-deputy / CWE-284).
    if cls == PathClass.PROTECTED:
        return Decision.BLOCK, _PROTECTED_MESSAGE

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
        # Genuine live-foreign conflict — BLOCK with the informative yield message.
        return Decision.BLOCK, str(exc)
    except Exception:  # noqa: BLE001 — fail-safe contract (AC-04): never fail-dead
        # Any unexpected lease-subsystem error (OSError, corrupt record, ValueError,
        # …) must NOT freeze the flow. Fail OPEN (heal-and-allow), matching the shell
        # gate's fail-open exit path — the guarantee holds for direct API callers too.
        return Decision.ALLOW, ""
    return Decision.ALLOW, ""
