"""Shared file-based rendezvous + lock-history journal for two-actor lease e2e.

T-010-06 / WS-R2 FR-R2-05 / AC-R2-04 (release v0.1.10). The two-actor concurrency
e2e spawns **real OS processes** that drive the real lease/gate surfaces. Coordinating
those processes without ever sleeping a fixed duration (slop-test discipline: no blind
``time.sleep``, no infinite poll) requires two primitives, both gathered here so the
test file stays about *invariants* and the harness conventions stay in one place:

1. **File rendezvous** (:func:`wait_for_file`): a process signals progress by creating a
   flag file; the coordinator waits for it with a **bounded deadline**. Every wait has a
   hard timeout — a hung child fails the test loudly instead of hanging the suite.

2. **Lock-file history journal** (:func:`LockJournal`): the invariants in AC-R2-04 are
   asserted on the *history* of the lease record (every version that ever existed), not
   on a subprocess return value. The journal snapshots the raw lock-file bytes at each
   step so a test can prove e.g. "no captured version ever named the foreign session".

TTL injection for the "holder busy past TTL" scenarios is **not** a 130-second real
sleep. The real holder process acquires with a deliberately short ``ttl`` (the same
``ttl`` keyword the unit tests use, :data:`SHORT_TTL_SECONDS`) and then stays genuinely
busy (its PID alive) for a little longer than that TTL. The record therefore goes
TTL-stale in real wall-clock time while the holder process is demonstrably alive — which
is exactly the no-steal precondition (TTL-stale + pid-alive ⇒ block, never takeover).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "POLL_INTERVAL",
    "SHORT_TTL_SECONDS",
    "LockJournal",
    "lock_record_path",
    "read_lock_record",
    "wait_for_file",
    "wait_until",
]

#: Injected lease TTL for the "holder busy past TTL" scenarios. Short enough that the
#: e2e completes in a couple of seconds, long enough that the holder reliably finishes
#: acquiring and signalling before it ages out. This is the same ``ttl`` keyword the
#: lease unit tests inject — the sanctioned, non-sleep TTL-injection seam.
SHORT_TTL_SECONDS: int = 2

#: Cooperative poll interval for bounded waits (never a blind fixed sleep of the whole
#: duration — we poll a *condition* and stop the instant it holds).
POLL_INTERVAL: float = 0.02


def lock_record_path(workspace: Path, ctx: str) -> Path:
    """Absolute path of the single lease record file for ``ctx`` in ``workspace``."""
    return workspace / ".dadaia" / "states" / "ctx_locks" / f"{ctx}.lock.json"


def read_lock_record(workspace: Path, ctx: str) -> dict[str, object] | None:
    """Read and parse the lease record, or ``None`` when absent/unparseable.

    A pure read used by the journal and by post-hoc assertions; it intentionally does
    not import ``lease`` so the journal stays a passive observer of the on-disk truth.
    """
    path = lock_record_path(workspace, ctx)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def wait_for_file(flag: Path, *, deadline_s: float, what: str) -> None:
    """Block until ``flag`` exists, or fail with a clear message at ``deadline_s``.

    Bounded poll — never an infinite wait. Raises ``AssertionError`` (so it surfaces as a
    test failure, not a hang) if the deadline elapses before the flag appears.
    """
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        if flag.exists():
            return
        time.sleep(POLL_INTERVAL)
    raise AssertionError(
        f"rendezvous timed out after {deadline_s:.1f}s waiting for {what} (flag={flag})"
    )


def wait_until(predicate: Callable[[], bool], *, deadline_s: float, what: str) -> None:
    """Block until ``predicate()`` is true, or fail at ``deadline_s``.

    Bounded poll on an arbitrary condition (e.g. "the lock record's heartbeat has aged
    past the injected TTL"). Never an infinite wait.
    """
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(POLL_INTERVAL)
    raise AssertionError(f"condition timed out after {deadline_s:.1f}s waiting for {what}")


@dataclass
class LockJournal:
    """Append-only journal of every observed version of a lease record.

    The AC-R2-04 invariants are asserted on the *history* of the lock file — "a live
    holder never loses the lease", "an ADDITIVE write never appears in the lock record",
    "B's session id never appears". The journal captures the raw record at each step so
    those statements can be checked against every version that ever existed, not just the
    final one.
    """

    workspace: Path
    ctx: str
    versions: list[dict[str, object] | None] = field(default_factory=list)

    def capture(self) -> dict[str, object] | None:
        """Snapshot the current lock record and append it to the history."""
        rec = read_lock_record(self.workspace, self.ctx)
        self.versions.append(rec)
        return rec

    def holders(self) -> list[str | None]:
        """The ``session_id`` of every captured version (``None`` for absent records)."""
        out: list[str | None] = []
        for rec in self.versions:
            if rec is None:
                out.append(None)
            else:
                sid = rec.get("session_id")
                out.append(sid if isinstance(sid, str) else None)
        return out

    def names_session(self, session_id: str) -> bool:
        """True if any captured version ever named ``session_id`` as the holder."""
        return session_id in self.holders()
