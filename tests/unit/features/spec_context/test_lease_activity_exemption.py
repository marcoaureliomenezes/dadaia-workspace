"""T-016-02 + T-010-11 (WS-R5/AC-R5-02): activity-class exemption matrix, re-rooted.

4 path classes (MUTATING, ADDITIVE, MEMORY, FROZEN) × 4 lease states
(absent, live-mine, live-other, expired) × **2 path locations** (workspace-root and
in-repo ``repos/<slug>/``) × **2 slugs** (default + non-default). Plus the two named
RULE A exemption tests (FR-P1-13).

T-010-11 fix: the original matrix asserted every class only against a *workspace-root*
path (``specs/backlog/x.md``), which the 2026-06-10 audit (qa defect 1+3) flagged as a
drift-ratifying test — it restated the classifier's pre-WS-R1 workspace-root-only blind
spot as the contract. The root-whitelist law forbids a root ``specs/``, so *every real*
Spec Context artifact lives under ``repos/<slug>/specs/``; asserting only the root form
certified a class taxonomy that was dead for every compliant workspace. The matrix is now
parametrized over ``{root, in-repo} × {default, non-default slug}`` so ADDITIVE/MEMORY/
FROZEN behavior is proven where it actually fires. All timing uses FakeClock; phase fixed
to SPEC for the matrix so MEMORY rows block (the ALLOW phases are the named tests).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.kernel_tunables import LEASE_TTL_SECONDS
from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.features.spec_context.gate_policy import Decision, evaluate

BASE = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
CTX = "myctx"

#: Default (self-hosting) slug + a non-default consumer slug. A class verdict depends only
#: on the context-relative remainder, never on which slug carries it (WS-R1 / FR-R1-06).
_DEFAULT_SLUG = "dadaia-workspace"
_NONDEFAULT_SLUG = "rand-engine"

#: Context-relative remainder per class. The same remainder is asserted at the workspace
#: root AND under ``repos/<slug>/`` (the in-repo form), so the re-rooted taxonomy is proven.
_SPEC_REL = {
    "mutating": "specs/releases/v0.2.0/SPEC.md",
    "additive": "specs/backlog/x.md",
    "memory": "specs/memory/x.md",
    "frozen": "specs/_archive/x.md",
}


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def _rel_path(path_class: str, location: str, slug: str) -> str:
    """Build the write path for ``path_class`` at ``location`` ('root' | 'in_repo')."""
    spec_rel = _SPEC_REL[path_class]
    if location == "root":
        return spec_rel
    return f"repos/{slug}/{spec_rel}"


def _seed(
    workspace: Path, session_id: str, heartbeat: datetime, *, ctx: str, ttl: int = LEASE_TTL_SECONDS
) -> None:
    lease._record_path(workspace, ctx).write_text(
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


def _apply_state(workspace: Path, state: str, *, ctx: str) -> None:
    if state == "absent":
        return
    if state == "live_mine":
        _seed(workspace, "mine", BASE, ctx=ctx)
    elif state == "live_other":
        _seed(workspace, "other", BASE, ctx=ctx)
    elif state == "expired":
        _seed(workspace, "other", BASE - timedelta(seconds=LEASE_TTL_SECONDS + 60), ctx=ctx)


# 16 cells: (path_class, lease_state) -> expected. Phase=SPEC throughout. The verdict is
# *location-invariant*: an in-repo ADDITIVE write is ALLOW exactly like a root one, an
# in-repo MEMORY write BLOCKs (outside DEFINITION/CLOSURE) exactly like a root one, etc.
#
# v0.1.76 NO-LOCKS DOCTRINE: the lease record on disk is now COMPLETELY INERT to the
# gate's MUTATING verdict — ``gate_policy.evaluate`` no longer reads ``ctx_locks/`` at
# all (it upserts advisory PRESENCE instead, which never blocks). A foreign lease
# ("live_other") therefore ALLOWs exactly like every other lease state; the seeded lease
# record here is legacy-residue fixture data that the gate simply never looks at.
_EXPECTED = {
    ("mutating", "absent"): Decision.ALLOW,
    ("mutating", "live_mine"): Decision.ALLOW,
    # v0.1.76: a foreign lease residue is inert — NEVER blocks (doctrine successor to the
    # deleted yield-iff-live-foreign BLOCK, D1 soul-fold / FR-P1-15).
    ("mutating", "live_other"): Decision.ALLOW,
    ("mutating", "expired"): Decision.ALLOW,
    ("additive", "absent"): Decision.ALLOW,
    ("additive", "live_mine"): Decision.ALLOW,
    ("additive", "live_other"): Decision.ALLOW,
    ("additive", "expired"): Decision.ALLOW,
    ("memory", "absent"): Decision.BLOCK,
    ("memory", "live_mine"): Decision.BLOCK,
    ("memory", "live_other"): Decision.BLOCK,
    ("memory", "expired"): Decision.BLOCK,
    ("frozen", "absent"): Decision.BLOCK,
    ("frozen", "live_mine"): Decision.BLOCK,
    ("frozen", "live_other"): Decision.BLOCK,
    ("frozen", "expired"): Decision.BLOCK,
}


@pytest.mark.parametrize("slug", [_DEFAULT_SLUG, _NONDEFAULT_SLUG], ids=["default", "nondefault"])
@pytest.mark.parametrize("location", ["root", "in_repo"], ids=["root", "in_repo"])
@pytest.mark.parametrize(
    ("path_class", "lease_state"),
    list(_EXPECTED.keys()),
    ids=[f"{c}_{s}_{_EXPECTED[(c, s)].value}" for (c, s) in _EXPECTED],
)
def test_exemption_matrix(
    path_class: str, lease_state: str, location: str, slug: str, tmp_path: Path
) -> None:
    """Class × lease-state × location × slug — the re-rooted exemption contract.

    AC-R5-02 / FR-R1-06: the in-repo variant of every class is asserted here, replacing the
    root-only ADDITIVE assumption the audit named (was ``test_lease_activity_exemption.py:27``
    / 16-cell root-only ``_PATHS``).
    """
    _apply_state(tmp_path, lease_state, ctx=CTX)
    rel_path = _rel_path(path_class, location, slug)
    decision, _msg = evaluate(
        tmp_path,
        rel_path,
        ctx=CTX,
        phase="SPEC",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == _EXPECTED[(path_class, lease_state)], (
        f"{path_class}/{lease_state} at {location} (slug={slug}) -> {decision}"
    )


@pytest.mark.parametrize("slug", [_DEFAULT_SLUG, _NONDEFAULT_SLUG], ids=["default", "nondefault"])
@pytest.mark.parametrize("location", ["root", "in_repo"], ids=["root", "in_repo"])
def test_additive_takes_no_lease_at_either_location(
    location: str, slug: str, tmp_path: Path
) -> None:
    """ADDITIVE ⇒ ALLOW with NO lease interaction, at the root AND in-repo (lease-theft guard).

    This is the precise behavior the original root-only assertion under-tested: an in-repo
    ``specs/backlog`` write must not read, write, or steal the lease (FR-R1-01). Asserted on
    the lease record's *absence*, not the return value.
    """
    rel_path = _rel_path("additive", location, slug)
    decision, _msg = evaluate(
        tmp_path,
        rel_path,
        ctx=CTX,
        phase="SPEC",
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.ALLOW
    assert not lease._record_path(tmp_path, CTX).exists(), (
        f"ADDITIVE write at {location} (slug={slug}) must take NO lease"
    )


@pytest.mark.parametrize("location", ["root", "in_repo"], ids=["root", "in_repo"])
@pytest.mark.parametrize(
    ("case", "phase", "rel_path_fn"),
    [
        pytest.param(
            "memory-definition",
            "DEFINITION",
            lambda location: _rel_path("memory", location, _DEFAULT_SLUG),
            id="memory-definition-allow",
        ),
        pytest.param(
            "memory-closure",
            "CLOSURE",
            lambda location: _rel_path("memory", location, _DEFAULT_SLUG),
            id="memory-closure-allow",
        ),
        pytest.param(
            "audits-additive",
            "SPEC",
            lambda location: (
                "specs/audits/2026-01-01T000000Z-abc12345/audit.md"
                if location == "root"
                else f"repos/{_DEFAULT_SLUG}/specs/audits/2026-01-01T000000Z-abc12345/audit.md"
            ),
            id="audits-path-additive-allow",
        ),
    ],
)
def test_memory_phase_and_audits_allow_matrix(  # type: ignore[no-untyped-def]
    case: str, phase: str, rel_path_fn, location: str, tmp_path: Path
) -> None:
    """MEMORY ALLOWs in DEFINITION/CLOSURE phase (both locations); T-016-13 AC-14 +
    FR-R1-01: specs/audits/** is ADDITIVE — always ALLOW, root or in-repo, with
    collision-safe naming (specs/audits/<UTC>-<session_id_8chars>/) and no lease check."""
    decision, _msg = evaluate(
        tmp_path,
        rel_path_fn(location),
        ctx=CTX,
        phase=phase,
        session_id="mine",
        release="v0.2.0",
        mode="IMPLEMENTATION",
        clock=fixed(BASE),
    )
    assert decision == Decision.ALLOW
