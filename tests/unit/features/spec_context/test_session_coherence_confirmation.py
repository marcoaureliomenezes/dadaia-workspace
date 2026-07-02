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
    lease.acquire(tmp_path, "ctxa", "sess_holder", "v1", "IMPLEMENTATION", pid=4321)
    _drift_ptr(tmp_path, "ctxa", "sess_later_read_bind")

    confirmed = lease.session_holds(tmp_path, "ctxa", "sess_holder")
    assert confirmed is True
    message = session_identity.coherence(
        tmp_path, "ctxa", lock_holder="sess_holder", holder_confirmed=confirmed
    )
    assert message is None


def test_unconfirmed_divergence_still_reports(tmp_path: Path) -> None:
    """An evidence-less lock holder + divergent ptr keeps the incoherence message."""
    _drift_ptr(tmp_path, "ctxa", "sess_ptr_only")

    confirmed = lease.session_holds(tmp_path, "ctxa", "sess_forged")
    assert confirmed is False
    message = session_identity.coherence(
        tmp_path, "ctxa", lock_holder="sess_forged", holder_confirmed=confirmed
    )
    assert message is not None
    assert "incoherence" in message


def test_default_keeps_legacy_behavior(tmp_path: Path) -> None:
    """Without the confirmation flag, divergence reports as before (back-compat)."""
    _drift_ptr(tmp_path, "ctxa", "sess_ptr")
    message = session_identity.coherence(tmp_path, "ctxa", lock_holder="sess_lock")
    assert message is not None
