"""A23 retention live-run-safety for workflow-step payloads (v0.1.30 / T-30-D-07).

These SAFETY tests are landed BEFORE the retention producer changes, per the
operator-approved Wave-D order. They pin the destructive contract for the workflow-step
data plane under ``.dadaia/runs/lifecycle/<run_id>/steps/``:

- ``preserves_live_run_step_payloads`` — a LIVE run's step payloads are NEVER reclaimed,
  even past TTL.
- ``reclaims_consumed_all_past_ttl`` — only ``consumed_all`` + ``delete_after_consumed``
  payloads past the consumed TTL are reclaimed; promoted / not-yet-consumed survive.
- promoted / current-release evidence survives even when consumed.

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


def test_preserves_live_run_step_payloads(tmp_path: Path) -> None:
    """A live run's step payloads are NEVER reclaimed, even when past TTL."""
    ref = _step_payload(
        tmp_path, "live-run", "qa-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    # The live-claim set claims the run's steps dir (what the container injects for a
    # non-terminal run).
    live = frozenset({".dadaia/runs/lifecycle/live-run/steps"})

    result = _sweep(tmp_path, live=live, reclaim_allow=frozenset({ref})).sweep(apply=True)

    assert (tmp_path / ref).is_file(), "live-run step payload must survive"
    assert ref not in set(result.reclaimed_paths)


# --- consumed_all past TTL is reclaimed; others survive ---------------------------


def test_reclaims_consumed_all_past_ttl(tmp_path: Path) -> None:
    """Only consumed_all delete-after-consumed payloads past TTL are reclaimed."""
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


def test_promoted_evidence_survives_even_when_eligible_by_ttl(tmp_path: Path) -> None:
    """A promote-to-evidence payload is never in the allow set ⇒ never reclaimed."""
    promoted = _step_payload(
        tmp_path, "done-run", "qa-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    # Empty allow set models "nothing is cleanup-eligible" (e.g. all promoted / unconsumed).
    result = _sweep(tmp_path, reclaim_allow=frozenset()).sweep(apply=True)

    assert (tmp_path / promoted).is_file(), "promoted evidence survives"
    assert promoted not in set(result.reclaimed_paths)


def test_within_ttl_consumed_payload_is_not_reclaimed(tmp_path: Path) -> None:
    """Even an allow-listed payload within TTL is spared (TTL still gates)."""
    fresh = _step_payload(tmp_path, "done-run", "spec-attempt-0", age=dt.timedelta(seconds=10))
    result = _sweep(tmp_path, reclaim_allow=frozenset({fresh})).sweep(apply=True)

    assert (tmp_path / fresh).is_file(), "within-TTL payload survives despite being eligible"
    assert fresh not in set(result.reclaimed_paths)


def test_dry_run_reports_eligible_but_deletes_nothing(tmp_path: Path) -> None:
    eligible = _step_payload(
        tmp_path, "done-run", "spec-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    result = _sweep(tmp_path, reclaim_allow=frozenset({eligible})).sweep()  # default dry-run

    assert result.applied is False
    assert (tmp_path / eligible).is_file()
    assert eligible in set(result.reclaimed_paths)


def test_empty_run_dir_pruned_after_reclaim(tmp_path: Path) -> None:
    eligible = _step_payload(
        tmp_path, "done-run", "spec-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    _sweep(tmp_path, reclaim_allow=frozenset({eligible})).sweep(apply=True)

    # The now-empty steps/ and run dir are pruned (idempotency / no rediscovery).
    assert not (tmp_path / ".dadaia/runs/lifecycle/done-run/steps").exists()


def test_back_compat_no_protector_keeps_ttl_behavior(tmp_path: Path) -> None:
    """With no step-payload protector wired, runs-zone TTL behavior is unchanged."""
    ref = _step_payload(
        tmp_path, "old-run", "spec-attempt-0", age=dt.timedelta(seconds=_TMP_TTL + 99)
    )
    result = _sweep(tmp_path, reclaim_allow=None).sweep(apply=True)

    # Legacy behavior: past-TTL runs entry reclaimed by mtime TTL alone.
    assert not (tmp_path / ref).is_file()
    assert any("old-run" in p for p in result.reclaimed_paths)
