"""FR24 (v0.4.3 T-043-39) — a consumed push verdict dies with the push.

Intent: CONTRACT — A24.1, A24.2, A24.3, A24.4, AG.1

``gc_consumed_push_verdicts`` is the POST-push half of the verdict lifecycle
(``push_gate_decision`` is the PRE-push half — see its module docstring for why the two
can never be the same call). These fixtures drive it directly with a synthetic
``.dadaia`` tree (no real git, no real push) and an explicit ``pushed_shas`` set standing
in for "the caller already confirmed these shas landed on the remote" — the one fact this
function trusts without re-deriving (mirrors the module's existing
"CLI is the composition root" seam).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.chokepoints import GcOutcome, gc_consumed_push_verdicts

_SHA_A = "a" * 40
_SHA_B = "b" * 40
_SHA_MERGE = "c" * 40  # stands in for a reconciliation-merge tip sha — opaque to this fn.


def _ledger_path(workspace: Path) -> Path:
    return workspace / ".dadaia" / "logs" / "push-verdict-gc-ledger.jsonl"


def _handoff_dir(workspace: Path, ctx: str = "demo-ctx") -> Path:
    d = workspace / ".dadaia" / "handoff" / ctx
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_handoff(
    path: Path,
    *,
    agent: str = "security-reviewer",
    verdict: str | None = "APPROVED",
    commit_sha: str | None = _SHA_A,
) -> None:
    payload: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": agent,
        "context": "demo-ctx",
        "produced_at": "2026-06-12T12:00:00Z",
        "artifact": {"type": "other"},
    }
    metrics: dict[str, object] = {}
    if commit_sha is not None:
        metrics["commit_sha"] = commit_sha
    payload["metrics"] = metrics
    if verdict is not None:
        payload["verdict"] = verdict
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# A24.1 — a successful push deletes exactly the covering verdict(s); an unrelated
# verdict (different sha) survives.
# ---------------------------------------------------------------------------


def test_matching_verdict_deleted_and_ledgered_unrelated_survives(tmp_path: Path) -> None:
    ctx_dir = _handoff_dir(tmp_path)
    matching = ctx_dir / "sec-approve-a.handoff.json"
    unrelated = ctx_dir / "sec-approve-b.handoff.json"
    _write_handoff(matching, commit_sha=_SHA_A)
    _write_handoff(unrelated, commit_sha=_SHA_B)
    # A malformed sibling in the same directory must never abort the sweep.
    (ctx_dir / "broken.handoff.json").write_text("{ not json", encoding="utf-8")

    outcome = gc_consumed_push_verdicts(tmp_path, [_SHA_A])

    assert not matching.exists()
    assert unrelated.exists()
    assert outcome == GcOutcome(
        deleted=("sec-approve-a.handoff.json",),
        ledgered=("sec-approve-a.handoff.json",),
        append_failed=(),
        lane_guard_refused=(),
    )
    lines = _ledger_path(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["agent"] == "security-reviewer"
    assert record["verdict"] == "APPROVED"
    assert record["commit_sha"] == _SHA_A
    assert record["source"] == "sec-approve-a.handoff.json"
    assert isinstance(record["ts"], str) and record["ts"]


def test_multiple_pushed_shas_each_covering_verdict_deleted(tmp_path: Path) -> None:
    ctx_dir = _handoff_dir(tmp_path)
    first = ctx_dir / "sec-approve-a.handoff.json"
    second = ctx_dir / "sec-approve-b.handoff.json"
    _write_handoff(first, commit_sha=_SHA_A)
    _write_handoff(second, commit_sha=_SHA_B)

    outcome = gc_consumed_push_verdicts(tmp_path, [_SHA_A, _SHA_B])

    assert not first.exists()
    assert not second.exists()
    assert set(outcome.deleted) == {"sec-approve-a.handoff.json", "sec-approve-b.handoff.json"}
    lines = _ledger_path(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


@pytest.mark.parametrize(
    ("agent", "verdict"),
    [
        pytest.param("code-reviewer", "APPROVED", id="wrong-agent"),
        pytest.param("security-reviewer", "REJECTED", id="not-approved"),
    ],
)
def test_non_qualifying_handoff_untouched(tmp_path: Path, agent: str, verdict: str) -> None:
    """Only a security-reviewer APPROVED handoff is ever a candidate (mirrors
    ``iter_security_approvals``'s existing qualification, per A24.1)."""
    ctx_dir = _handoff_dir(tmp_path)
    handoff = ctx_dir / "sec-x.handoff.json"
    _write_handoff(handoff, agent=agent, verdict=verdict, commit_sha=_SHA_A)

    outcome = gc_consumed_push_verdicts(tmp_path, [_SHA_A])

    assert handoff.exists()
    assert outcome == GcOutcome()


# ---------------------------------------------------------------------------
# A24.2 — a failed/refused push deletes nothing. Modeled as: the caller never
# confirms any sha (an empty ``pushed_shas``) when the push it would report failed or
# was refused — every on-disk verdict survives untouched.
# ---------------------------------------------------------------------------


def test_no_confirmed_shas_deletes_nothing(tmp_path: Path) -> None:
    ctx_dir = _handoff_dir(tmp_path)
    handoff = ctx_dir / "sec-approve.handoff.json"
    _write_handoff(handoff, commit_sha=_SHA_A)

    outcome = gc_consumed_push_verdicts(tmp_path, [])

    assert handoff.exists()
    assert outcome == GcOutcome()
    assert not _ledger_path(tmp_path).exists()


# ---------------------------------------------------------------------------
# A24.3 — deletion is best-effort: an I/O error deleting one handoff never aborts the
# sweep of the others, and never raises out of the function.
# ---------------------------------------------------------------------------


def test_unlink_failure_is_best_effort_and_does_not_abort_sweep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx_dir = _handoff_dir(tmp_path)
    protected = ctx_dir / "sec-protected.handoff.json"
    other = ctx_dir / "sec-other.handoff.json"
    _write_handoff(protected, commit_sha=_SHA_A)
    _write_handoff(other, commit_sha=_SHA_B)

    # Portable removal-failure simulation (not ``os.chmod`` on the containing
    # directory): the POSIX read-only-directory permission model is a platform no-op
    # for file deletion on Windows (the read-only attribute NTFS exposes there does not
    # block content deletion the way a POSIX write-permission bit does), so the
    # chmod-based simulation never actually denies the unlink and the best-effort
    # branch goes unexercised. Monkeypatching ``Path.unlink`` to raise for these exact
    # targets — same idiom as the v0.4.2 unreadable-file precedent (monkeypatched
    # ``Path.read_text``) — exercises the identical ``except OSError`` branch
    # identically on every platform; matched by value equality (the production code
    # builds its own ``Path`` instances via ``iterdir()``).
    denied = {protected, other}
    real_unlink = Path.unlink

    def _unlink_denied(self: Path, *args: object, **kwargs: object) -> None:
        if self in denied:
            raise PermissionError(13, "Permission denied", str(self))
        real_unlink(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "unlink", _unlink_denied)

    outcome = gc_consumed_push_verdicts(tmp_path, [_SHA_A, _SHA_B])

    # The ledger line was appended (durable evidence survives even when the
    # best-effort unlink fails) but the file itself could not be removed.
    assert protected.exists()
    assert "sec-protected.handoff.json" in outcome.ledgered
    assert "sec-protected.handoff.json" not in outcome.deleted
    # The OTHER handoff, in the same (now read-only) directory, could not be deleted
    # either — proving one failure never raises out of the sweep before later entries
    # are attempted.
    assert "sec-other.handoff.json" in outcome.ledgered


# ---------------------------------------------------------------------------
# A24.4 — the record outlives the handoff: the ledger line is appended BEFORE the
# handoff is deleted; a FAILED append leaves the handoff in place.
# ---------------------------------------------------------------------------


def test_failed_ledger_append_leaves_handoff_in_place(tmp_path: Path) -> None:
    ctx_dir = _handoff_dir(tmp_path)
    handoff = ctx_dir / "sec-approve.handoff.json"
    _write_handoff(handoff, commit_sha=_SHA_A)
    # Force the append to fail: the ledger PATH itself already exists as a directory,
    # so opening it for append raises IsADirectoryError (an OSError subclass) — no
    # permission-bit trickery needed, and it is portable to a root-run CI shell.
    ledger_path = _ledger_path(tmp_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.mkdir()

    outcome = gc_consumed_push_verdicts(tmp_path, [_SHA_A])

    assert handoff.exists()
    assert outcome == GcOutcome(append_failed=("sec-approve.handoff.json",))


# ---------------------------------------------------------------------------
# AG.1 — resolve the target, refuse anything outside .dadaia/, never follow a
# symlinked directory (FR17/A17.1 doctrine by reference).
# ---------------------------------------------------------------------------


def test_lane_guard_never_follows_a_symlinked_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside-dadaia"
    outside.mkdir()
    decoy = outside / "decoy.handoff.json"
    _write_handoff(decoy, commit_sha=_SHA_A)

    ctx_dir = _handoff_dir(tmp_path)
    (ctx_dir / "linked").symlink_to(outside, target_is_directory=True)

    outcome = gc_consumed_push_verdicts(tmp_path, [_SHA_A])

    # The symlinked directory is never descended into, so the decoy is never even
    # discovered — not deleted, not ledgered, not lane-guard-refused (it never reached
    # the guard at all).
    assert decoy.exists()
    assert outcome == GcOutcome()


def test_lane_guard_refuses_a_target_resolving_outside_dadaia(tmp_path: Path) -> None:
    outside = tmp_path / "outside-dadaia"
    outside.mkdir()
    real = outside / "real.handoff.json"
    _write_handoff(real, commit_sha=_SHA_A)

    ctx_dir = _handoff_dir(tmp_path)
    escape = ctx_dir / "escape.handoff.json"
    escape.symlink_to(real)

    outcome = gc_consumed_push_verdicts(tmp_path, [_SHA_A])

    assert real.exists()
    assert escape.exists()
    assert outcome == GcOutcome(lane_guard_refused=("escape.handoff.json",))
    assert not _ledger_path(tmp_path).exists()


# ---------------------------------------------------------------------------
# Reconciliation-shape pushes — the chokepoint does not distinguish them: a develop
# push whose tip is a reconciliation-merge commit is swept identically to any other
# tip sha (this function only ever sees an opaque sha string).
# ---------------------------------------------------------------------------


def test_reconciliation_shape_tip_sha_swept_identically(tmp_path: Path) -> None:
    ctx_dir = _handoff_dir(tmp_path)
    handoff = ctx_dir / "sec-approve-merge.handoff.json"
    _write_handoff(handoff, commit_sha=_SHA_MERGE)

    outcome = gc_consumed_push_verdicts(tmp_path, [_SHA_MERGE])

    assert not handoff.exists()
    assert outcome.deleted == ("sec-approve-merge.handoff.json",)


# ---------------------------------------------------------------------------
# FR27/A27.1 (T-043-42): the ledger is a ``.dadaia/logs/*.jsonl`` writer too (same
# directory family as reconciler-events.jsonl per this module's own FR24 comment) —
# it rotates through the SAME shared helper, with no separate carve-out. Rotation
# never contradicts A24.4's "append-only" audit property: append-only means the
# ledger is never mutated/edited in place, not that it is retained forever — FR27's
# current+1 retention applies to it exactly like every other appender.
# ---------------------------------------------------------------------------


def test_ledger_rotates_at_the_shared_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import dadaia_workspace.infrastructure.jsonl_log_rotation as rotation

    ledger_path = _ledger_path(tmp_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text('{"seed": true}\n', encoding="utf-8")
    monkeypatch.setattr(rotation, "LOG_ROTATION_MAX_BYTES", 8)

    ctx_dir = _handoff_dir(tmp_path)
    handoff = ctx_dir / "sec-approve.handoff.json"
    _write_handoff(handoff, commit_sha=_SHA_A)

    outcome = gc_consumed_push_verdicts(tmp_path, [_SHA_A])

    assert outcome.deleted == ("sec-approve.handoff.json",)
    rotated = ledger_path.with_name(ledger_path.name + ".1")
    assert rotated.exists()
    assert json.loads(rotated.read_text(encoding="utf-8").strip()) == {"seed": True}
    new_lines = [ln for ln in ledger_path.read_text(encoding="utf-8").splitlines() if ln]
    assert len(new_lines) == 1
    rec = json.loads(new_lines[0])
    assert rec["event"] == "PUSH_VERDICT_CONSUMED"
    assert rec["commit_sha"] == _SHA_A
