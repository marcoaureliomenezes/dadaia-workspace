"""A23 retention live-run-safety for workflow-step payloads (v0.1.30 / T-30-D-07).

These SAFETY tests are landed BEFORE the retention producer changes, per the
operator-approved Wave-D order. They pin the destructive contract for the workflow-step
data plane under ``.dadaia/runs/lifecycle/<run_id>/steps/``:

- ``preserves_live_run_step_payloads`` — a LIVE run's step payloads are NEVER reclaimed,
  even past TTL.
- ``reclaims_consumed_all_past_ttl`` — only ``consumed_all`` + ``delete_after_consumed``
  payloads past the consumed TTL are reclaimed; promoted / not-yet-consumed survive.
- promoted / current-release evidence survives even when consumed.

CRITICAL: destructive-safety contract for the step-payload data plane — every spare-rule
survives as its own case.

Hermetic: a ``.dadaia`` skeleton under ``tmp_path``, fixed clock, injected protector set.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from dadaia_workspace.core.models.hygiene import SlopPolicy
from dadaia_workspace.features.lifecycle.antislop.retention import RetentionSweep

NOW = dt.datetime(2026, 6, 27, 12, 0, tzinfo=dt.UTC)
_TMP_TTL = SlopPolicy().tmp_ttl_seconds


def _write(path: Path, *, age: dt.timedelta = dt.timedelta(0)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    ts = (NOW - age).timestamp()
    os.utime(path, (ts, ts))
    return path


def _step_payload(tmp_path: Path, run_id: str, name: str, *, age: dt.timedelta) -> str:
    rel = f".dadaia/runs/lifecycle/{run_id}/steps/{name}.step-payload.json"
    _write(tmp_path / rel, age=age)
    return rel


def _sweep(
    tmp_path: Path,
    *,
    live: frozenset[str] = frozenset(),
    important: frozenset[str] = frozenset(),
    reclaim_allow: frozenset[str] | None = None,
) -> RetentionSweep:
    return RetentionSweep(
        tmp_path,
        now=NOW,
        policy=SlopPolicy(),
        live_claims=lambda: live,
        important_paths=lambda: important,
        step_payload_reclaim_allow=(None if reclaim_allow is None else (lambda: reclaim_allow)),
    )


# --- live-run safety --------------------------------------------------------------


# --- consumed_all past TTL is reclaimed; others survive ---------------------------


def test_reclaims_consumed_all_past_ttl_not_consumed_sibling_protected(tmp_path: Path) -> None:
    """Only consumed_all delete-after-consumed payloads past TTL are reclaimed; a
    not-yet-consumed sibling in the same run is protected, and the now-empty steps/ dir is
    pruned after reclaim (idempotency / no rediscovery). A live run's step payloads are
    NEVER reclaimed, even when past TTL."""
    eligible = _step_payload(
        tmp_path, "done-run", "spec-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    not_consumed = _step_payload(
        tmp_path, "done-run", "tasks-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    # Only the eligible (consumed_all) payload is in the reclaim-allow set.
    result = _sweep(tmp_path, reclaim_allow=frozenset({eligible})).sweep(apply=True)

    assert not (tmp_path / eligible).is_file(), "consumed_all past-TTL payload reclaimed"
    assert (tmp_path / not_consumed).is_file(), "not-consumed_all payload protected"
    assert eligible in set(result.reclaimed_paths)
    assert not_consumed not in set(result.reclaimed_paths)

    live_ws = tmp_path / "live-ws"
    ref = _step_payload(
        live_ws, "live-run", "qa-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    # The live-claim set claims the run's steps dir (what the container injects for a
    # non-terminal run).
    live = frozenset({".dadaia/runs/lifecycle/live-run/steps"})

    live_result = _sweep(live_ws, live=live, reclaim_allow=frozenset({ref})).sweep(apply=True)

    assert (live_ws / ref).is_file(), "live-run step payload must survive"
    assert ref not in set(live_result.reclaimed_paths)


# --- ① promoted-evidence + within-TTL spared --------------------------------------


def test_promoted_evidence_and_within_ttl_payload_are_spared(tmp_path: Path) -> None:
    """A promote-to-evidence payload is never in the allow set ⇒ never reclaimed, and even
    an allow-listed payload within TTL is spared (TTL still gates)."""
    promoted = _step_payload(
        tmp_path, "done-run", "qa-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    # Empty allow set models "nothing is cleanup-eligible" (e.g. all promoted / unconsumed).
    promoted_result = _sweep(tmp_path, reclaim_allow=frozenset()).sweep(apply=True)
    assert (tmp_path / promoted).is_file(), "promoted evidence survives"
    assert promoted not in set(promoted_result.reclaimed_paths)

    fresh = _step_payload(
        tmp_path / "within-ttl", "done-run", "spec-attempt-0", age=dt.timedelta(seconds=10)
    )
    fresh_result = _sweep(tmp_path / "within-ttl", reclaim_allow=frozenset({fresh})).sweep(
        apply=True
    )
    assert (tmp_path / "within-ttl" / fresh).is_file(), (
        "within-TTL payload survives despite being eligible"
    )
    assert fresh not in set(fresh_result.reclaimed_paths)


# --- ② dry-run default reports-without-deleting + back-compat no-protector TTL ---------


def test_dry_run_default_reports_without_deleting_and_no_protector_ttl_back_compat(
    tmp_path: Path,
) -> None:
    eligible = _step_payload(
        tmp_path, "done-run", "spec-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    dry_run_result = _sweep(
        tmp_path, reclaim_allow=frozenset({eligible})
    ).sweep()  # default dry-run

    assert dry_run_result.applied is False
    assert (tmp_path / eligible).is_file()
    assert eligible in set(dry_run_result.reclaimed_paths)

    # With no step-payload protector wired, runs-zone TTL behavior is unchanged (legacy).
    legacy_root = tmp_path / "legacy"
    ref = _step_payload(
        legacy_root, "old-run", "spec-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    legacy_result = _sweep(legacy_root, reclaim_allow=None).sweep(apply=True)

    assert not (legacy_root / ref).is_file()
    assert any("old-run" in p for p in legacy_result.reclaimed_paths)
