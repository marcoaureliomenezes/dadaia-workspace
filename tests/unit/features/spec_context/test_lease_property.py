"""T-016-02 + T-016-14 + T-010-11: fail-safe property table (SPEC §8 AC-04), re-rooted.

Every row's decision is one of {ALLOW, BLOCK}; every BLOCK carries an actionable
message; no row raises an unhandled exception. D1 soul-fold: a MUTATING live-other
conflict BLOCKS with yield-iff-live-foreign (FR-P1-15) when no .ptr match; a
relaunched session with .ptr match RENEWs (ALLOW). All timing uses FakeClock.

T-010-11 fix (WS-R5 / AC-R5-02): the original ADDITIVE rows pinned only the *workspace
root* path ``specs/backlog/x.md`` — the drift-ratifying assertion the 2026-06-10 audit
named (qa defect 1+3). Because the root-whitelist law forbids a root ``specs/``, every
real Spec Context's additive writes are *in-repo* (``repos/<slug>/specs/backlog``); the
root-only row restated the classifier's pre-WS-R1 blind spot as the contract. Each
spec-relative row now runs at BOTH ``location='root'`` and ``location='in_repo'`` across the
default + a non-default slug, so the property holds where additive writes actually occur.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.features.spec_context.gate_policy import Decision, evaluate

BASE = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
CTX = "myctx"

#: Default (self-hosting) slug + a non-default consumer slug. A class verdict depends only
#: on the context-relative remainder, never on which slug carries it (WS-R1 / FR-R1-06).
_DEFAULT_SLUG = "dadaia-workspace"
_NONDEFAULT_SLUG = "rand-engine"


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def _seed(
    workspace: Path, session_id: str, heartbeat: datetime, *, ctx: str = CTX, ttl: int = 1800
) -> None:
    path = lease._record_path(workspace, ctx)
    path.write_text(
        json.dumps(
            {
                "context": ctx,
                "release": "v0.2.0",
                "session_id": session_id,
                "mode": "IMPLEMENTATION",
                "acquired_at": heartbeat.isoformat(),
                "heartbeat": heartbeat.isoformat(),
                "ttl": ttl,
            }
        ),
        encoding="utf-8",
    )


def _at(spec_rel: str, location: str, slug: str) -> str:
    """Render ``spec_rel`` at the workspace root or under ``repos/<slug>/`` (in-repo)."""
    return spec_rel if location == "root" else f"repos/{slug}/{spec_rel}"


# (row_id, spec_rel, phase, seed_fn, expected_decision)
# spec_rel is a *context-relative* path asserted at both root and in-repo; seed_fn(workspace)
# sets up the lease state (keyed on CTX), or None for absent.
_ROWS = [
    ("1_absent_mutating", "specs/releases/v0.2.0/SPEC.md", "SPEC", None, Decision.ALLOW),
    (
        "2_stale_mutating",
        "specs/releases/v0.2.0/SPEC.md",
        "SPEC",
        lambda ws: _seed(ws, "other", BASE - timedelta(seconds=4000)),
        Decision.ALLOW,
    ),
    (
        "3_live_mine_mutating",
        "specs/releases/v0.2.0/SPEC.md",
        "SPEC",
        lambda ws: _seed(ws, "mine", BASE),
        Decision.ALLOW,
    ),
    (
        # D1 soul-fold: foreign live lease → yield-iff-live-foreign BLOCK (FR-P1-15).
        # No .ptr file → session "mine" sees live foreign "other" and is blocked.
        "4_live_other_mutating",
        "specs/releases/v0.2.0/SPEC.md",
        "SPEC",
        lambda ws: _seed(ws, "other", BASE),
        Decision.BLOCK,
    ),
    # ADDITIVE rows: re-rooted (T-010-11). ALLOW at root AND in-repo, lease present or not.
    ("5_absent_additive", "specs/backlog/x.md", "SPEC", None, Decision.ALLOW),
    (
        "6_live_other_additive",
        "specs/backlog/x.md",
        "SPEC",
        lambda ws: _seed(ws, "other", BASE),
        Decision.ALLOW,
    ),
    ("7_any_frozen", "specs/_archive/x.md", "SPEC", None, Decision.BLOCK),
    ("8_memory_non_write_phase", "specs/memory/x.md", "SPEC", None, Decision.BLOCK),
    ("9_memory_definition", "specs/memory/x.md", "DEFINITION", None, Decision.ALLOW),
]


@pytest.mark.parametrize("slug", [_DEFAULT_SLUG, _NONDEFAULT_SLUG], ids=["default", "nondefault"])
@pytest.mark.parametrize("location", ["root", "in_repo"], ids=["root", "in_repo"])
@pytest.mark.parametrize("row", _ROWS, ids=[r[0] for r in _ROWS])
def test_fail_safe_property(row: tuple, location: str, slug: str, tmp_path: Path) -> None:  # type: ignore[type-arg]
    row_id, spec_rel, phase, seed_fn, expected = row
    if seed_fn is not None:
        seed_fn(tmp_path)

    rel_path = _at(spec_rel, location, slug)
    decision, message = evaluate(
        tmp_path,
        rel_path,
        ctx=CTX,
        phase=phase,
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )

    # Property: output is one of the two actionable decisions.
    assert decision in (Decision.ALLOW, Decision.BLOCK)
    assert decision == expected, f"row {row_id}: expected {expected}, got {decision}"

    if decision == Decision.BLOCK:
        assert message, f"row {row_id}: BLOCK must carry an actionable message"

    # D1 soul-fold: a MUTATING live-other conflict BLOCKS with yield-iff-live-foreign
    # message (FR-P1-15). The message is informative and actionable, and per the operator
    # forbidden-law contains NO manual unblock ceremony — neither "bind --mode write",
    # "relaunch", nor "lock steal" — because reclaim-iff-stale frees a dead holder by itself.
    if row_id == "4_live_other_mutating":
        assert decision == Decision.BLOCK
        assert message, "yield-iff-live-foreign BLOCK must carry an actionable message"
        for forbidden in ("bind --mode write", "relaunch", "lock steal"):
            assert forbidden not in message, (
                f"forbidden-law: BLOCK message must not contain {forbidden!r}"
            )


# ---------------------------------------------------------------------------
# T-010-11 (AC-R5-02): multi-context property — additive writes never cross-touch a lease.
# The {1, 2 contexts} fixture dimension is meaningful here: it proves the additive ALLOW is
# lease-free not only for the *bound* context but across a second live context's lease.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contexts", [("ctx-a",), ("ctx-a", "ctx-b")], ids=["one_ctx", "two_ctx"])
@pytest.mark.parametrize("location", ["root", "in_repo"], ids=["root", "in_repo"])
def test_additive_write_never_touches_any_lease(
    contexts: tuple[str, ...], location: str, tmp_path: Path
) -> None:
    """An ADDITIVE write under ``ctx-a`` leaves every seeded context lease byte-untouched.

    Seeds a live foreign holder for each context in ``contexts`` (the 2-context case adds a
    second, unrelated lease that must also be unaffected), then drives an additive
    ``specs/backlog`` write for ``ctx-a`` at root and in-repo. The property: ALLOW, and NO
    lease record changed — the lease-theft surface stays closed across contexts (FR-R1-01).
    """
    holders = {ctx: f"holder-{ctx}" for ctx in contexts}
    for ctx, holder in holders.items():
        _seed(tmp_path, holder, BASE, ctx=ctx)
    before = {
        ctx: lease._record_path(tmp_path, ctx).read_text(encoding="utf-8") for ctx in contexts
    }

    rel_path = _at("specs/backlog/x.md", location, _DEFAULT_SLUG)
    decision, message = evaluate(
        tmp_path,
        rel_path,
        ctx="ctx-a",
        phase="SPEC",
        session_id="foreign-additive",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE + timedelta(seconds=130)),  # past TTL — the incident precondition
    )
    assert decision == Decision.ALLOW
    assert message == "", "ADDITIVE ALLOW carries no message"
    for ctx in contexts:
        after = lease._record_path(tmp_path, ctx).read_text(encoding="utf-8")
        assert after == before[ctx], (
            f"additive write must not change context {ctx!r}'s lease (no cross-context steal)"
        )


# ---------------------------------------------------------------------------
# T-016-14: soul-fold property rows (D1) — stable-identity renewal + yield block
# ---------------------------------------------------------------------------


def test_mutating_stable_identity_match_live_foreign_renews(tmp_path: Path) -> None:
    """D1 soul-fold row: MUTATING + stable-identity-match + live-foreign-lock → RENEW (ALLOW).

    When a .ptr file matches the caller's session_id, acquire() RENEWs regardless
    of whether the lock record shows a different (foreign-looking) session_id. This
    is the relaunched-session scenario: the session is recognised as the incumbent.
    """
    # Seed lock record with "foreign-looking" session_id (simulating a relaunch that
    # caused the session env var to diverge from the record).
    _seed(tmp_path, "old-session-id", BASE)
    # Write .ptr for "mine" — signals that "mine" is the incumbent for this context.
    ptr = lease._ptr_path(tmp_path, CTX)
    ptr.write_text("mine", encoding="utf-8")

    decision, _msg = evaluate(
        tmp_path,
        "specs/releases/v0.2.0/SPEC.md",
        ctx=CTX,
        phase="SPEC",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.ALLOW, (
        "Stable-identity match (.ptr == session_id) must RENEW even when lock record "
        "shows a foreign-looking session_id (D1 soul-fold, FR-P1-15)"
    )


def test_mutating_no_ptr_match_live_foreign_yields(tmp_path: Path) -> None:
    """D1 soul-fold row: MUTATING + no-ptr-match + live-foreign-lock → yield BLOCK (ALLOW escape).

    When no .ptr matches and the lock record has a live foreign session_id,
    acquire() raises LockHeldError with yield-iff-live-foreign message. The block
    is always escapable (via additive writes; steal only as conditional emergency).
    """
    # Seed a live foreign lock record with no .ptr for "mine".
    _seed(tmp_path, "genuinely-other-session", BASE)

    decision, message = evaluate(
        tmp_path,
        "specs/releases/v0.2.0/SPEC.md",
        ctx=CTX,
        phase="SPEC",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.BLOCK, (
        "No-.ptr-match + live-foreign lease must BLOCK with yield message (D1, FR-P1-15)"
    )
    assert message, "Yield block must carry an informative, actionable message"
    assert "bind --mode write" not in message, (
        "Yield message must never instruct to bind --mode write"
    )
    assert "relaunch" not in message, "Yield message must never instruct to relaunch"


def test_mutating_unexpected_lease_error_fails_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-04 fail-safe: an unexpected lease-subsystem error must ALLOW, never raise.

    The 'never fail-dead' contract must hold for direct API callers, not only the
    shell gate. If lease.acquire raises something other than LockHeldError (e.g.
    OSError from a corrupt/unreadable lock store), evaluate() heals-and-allows.
    """

    def _boom(*_args: object, **_kwargs: object) -> tuple[str, dict[str, object]]:
        raise OSError("simulated unreadable lock store")

    monkeypatch.setattr(lease, "acquire", _boom)

    decision, message = evaluate(
        tmp_path,
        "specs/releases/v0.2.0/SPEC.md",
        ctx=CTX,
        phase="SPEC",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.ALLOW, (
        "Unexpected lease error must fail OPEN (heal-and-allow), never freeze the flow"
    )
