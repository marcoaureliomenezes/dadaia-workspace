"""SPEC-DOC-029 holder-confirmation (v0.1.50 FR2 — audit F-4 false forgery).

A live lock-holder whose by-session index entry names the context (acquisition
evidence written in the same CAS as the acquire) is the TRUE holder: a divergent
incumbent ``.ptr`` (e.g. a later read-bind moved it) is drift, not forgery. Only an
evidence-less live holder yields the incoherence message.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease, session_identity

pytestmark = pytest.mark.unit


def _drift_ptr(workspace: Path, ctx: str, to_sid: str) -> None:
    ptr = workspace / ".dadaia" / "sessions" / "runtime" / f"{ctx}.ptr"
    ptr.parent.mkdir(parents=True, exist_ok=True)
    ptr.write_text(to_sid, encoding="utf-8")


def test_confirmed_holder_with_drifted_ptr_is_coherent(tmp_path: Path) -> None:
    """The false-positive fix: a confirmed live holder's drifted ptr is drift, not
    forgery — coherence() returns None (no incoherence report)."""
    lease.acquire(tmp_path, "ctxa", "sess_holder", "v1", "IMPLEMENTATION", pid=4321)
    _drift_ptr(tmp_path, "ctxa", "sess_later_read_bind")

    confirmed = lease.session_holds(tmp_path, "ctxa", "sess_holder")
    assert confirmed is True
    message = session_identity.coherence(
        tmp_path, "ctxa", lock_holder="sess_holder", holder_confirmed=confirmed
    )
    assert message is None


def test_unconfirmed_divergence_and_legacy_default_both_still_report(tmp_path: Path) -> None:
    """An evidence-less lock holder + divergent ptr keeps the incoherence message
    (unconfirmed case), and the same holds without the confirmation flag at all
    (legacy back-compat default)."""
    _drift_ptr(tmp_path, "ctxa", "sess_ptr_only")
    confirmed = lease.session_holds(tmp_path, "ctxa", "sess_forged")
    assert confirmed is False
    message = session_identity.coherence(
        tmp_path, "ctxa", lock_holder="sess_forged", holder_confirmed=confirmed
    )
    assert message is not None
    assert "incoherence" in message

    _drift_ptr(tmp_path, "ctxb", "sess_ptr")
    legacy_message = session_identity.coherence(tmp_path, "ctxb", lock_holder="sess_lock")
    assert legacy_message is not None
