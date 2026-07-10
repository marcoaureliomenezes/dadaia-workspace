"""Unit tests for lifecycle hygiene status service.

CRITICAL: v0.1.74 ``canonical_zone_doc`` protection + ``cleanup_candidate_count -
protected_residual_count`` preflight arithmetic — this release's own regression guard, kept
verbatim.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from dadaia_workspace.core.models.hygiene import HygieneZone, SlopPolicy
from dadaia_workspace.features.lifecycle.hygiene import LifecycleHygieneService
from dadaia_workspace.features.workspace_clean.service import WorkspaceCleanService

NOW = dt.datetime(2026, 6, 18, 5, 0, tzinfo=dt.UTC)


def _write(path: Path, *, age: dt.timedelta) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("content", encoding="utf-8")
    timestamp = (NOW - age).timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


# --- ① TTL status + explicit-policy + WorkspaceClean-reconciled param -----------------


def test_status_uses_slop_policy_ttls_default_and_explicit_reconciled_with_workspace_clean(
    tmp_path: Path,
) -> None:
    old_report = _write(
        tmp_path / ".dadaia" / "reports" / "ctx" / "agent" / "old.html",
        age=dt.timedelta(hours=49),
    )
    fresh_report = _write(
        tmp_path / ".dadaia" / "reports" / "ctx" / "agent" / "fresh.html",
        age=dt.timedelta(hours=1),
    )
    old_handoff = _write(
        tmp_path / ".dadaia" / "handoff" / "ctx" / "old.handoff.json",
        age=dt.timedelta(hours=25),
    )
    old_tmp = _write(
        tmp_path / ".dadaia" / "tmp" / "workflow" / "20260618" / "old.txt",
        age=dt.timedelta(hours=25),
    )
    _write(
        tmp_path / ".dadaia" / "tmp" / "workflow" / "20260618" / "fresh.txt",
        age=dt.timedelta(minutes=5),
    )

    counters = LifecycleHygieneService(tmp_path, now=NOW).status()

    assert counters.zone_totals == {
        HygieneZone.REPORTS: 2,
        HygieneZone.HANDOFF: 1,
        HygieneZone.TMP: 2,
    }
    assert counters.expired_totals == {
        HygieneZone.REPORTS: 1,
        HygieneZone.HANDOFF: 1,
        HygieneZone.TMP: 1,
    }
    assert counters.cleanup_candidate_count == 3
    assert old_report.exists()
    assert fresh_report.exists()
    assert old_handoff.exists()
    assert old_tmp.exists()

    # An explicit SlopPolicy overrides the defaults.
    explicit_report = _write(
        tmp_path / ".dadaia" / "reports" / "ctx2" / "agent" / "old.html",
        age=dt.timedelta(seconds=11),
    )
    policy = SlopPolicy(reports_ttl_seconds=10, handoff_ttl_seconds=60, tmp_ttl_seconds=60)
    explicit_counters = LifecycleHygieneService(tmp_path, policy=policy, now=NOW).status()
    assert explicit_counters.expired_totals[HygieneZone.REPORTS] >= 1
    assert explicit_report.exists()

    # WorkspaceCleanService's default TTLs are reconciled with the same SlopPolicy.
    recent_report = _write(
        tmp_path / ".dadaia" / "reports" / "ctx" / "agent" / "recent.html",
        age=dt.timedelta(hours=47),
    )
    result = WorkspaceCleanService(tmp_path, now=NOW).clean(dry_run=True)
    candidate_paths = {candidate.path for candidate in result.candidates}
    assert old_tmp in candidate_paths
    assert old_report in candidate_paths
    assert old_handoff in candidate_paths
    assert recent_report not in candidate_paths


# --- ② unknown top-level dirs ----------------------------------------------------------


def test_status_reports_unknown_top_level_dirs_and_counts_orphan_malformed_handoffs(
    tmp_path: Path,
) -> None:
    (tmp_path / ".dadaia" / "reports").mkdir(parents=True)
    (tmp_path / ".dadaia" / "imgs").mkdir()
    (tmp_path / ".dadaia" / "references").mkdir()

    dirs_counters = LifecycleHygieneService(tmp_path, now=NOW).status()

    assert dirs_counters.unknown_top_level_dirs == ("imgs", "references")

    handoff_root = tmp_path / ".dadaia" / "handoff" / "ctx"
    handoff_root.mkdir(parents=True)
    (handoff_root / "orphan.handoff.json").write_text(
        json.dumps({"artifact": {"path": ".dadaia/reports/ctx/missing.html"}}),
        encoding="utf-8",
    )
    (handoff_root / "malformed-json.handoff.json").write_text("{not json", encoding="utf-8")
    (handoff_root / "bad-artifact.handoff.json").write_text(
        json.dumps({"artifact": {"path": "repos/dadaia-workspace/report.html"}}),
        encoding="utf-8",
    )
    (handoff_root / "traversal-artifact.handoff.json").write_text(
        json.dumps({"artifact": {"path": ".dadaia/reports/../states/secret.txt"}}),
        encoding="utf-8",
    )
    (handoff_root / "handoff-first.handoff.json").write_text(
        json.dumps({"artifact": {"type": "other"}}),
        encoding="utf-8",
    )

    counters = LifecycleHygieneService(tmp_path, now=NOW).status()

    assert counters.orphan_handoff_count == 1
    assert counters.malformed_handoff_count == 3


def test_zone_doc_agents_md_is_canonical_never_unprotected(tmp_path: Path) -> None:
    """v0.1.74 (bug ``public-install-restores-expired-zone-agents-reblocks-preflight``):
    zone-root ``AGENTS.md`` files are the documented scoped-rules mechanism — canonical
    lib projections, NOT ephemeral artifacts. ``public install`` restores them with old
    mtimes, so an unprotected classification re-blocked preflight forever (and
    ``clean --apply`` deleting them made ``public doctor`` drift: an install/clean loop).
    They must be PROTECTED (``canonical_zone_doc``); a genuinely stale sibling stays
    unprotected. README.md / .gitkeep zone docs get the same class treatment."""
    agents_handoff = _write(
        tmp_path / ".dadaia" / "handoff" / "AGENTS.md", age=dt.timedelta(days=30)
    )
    agents_tmp = _write(tmp_path / ".dadaia" / "tmp" / "AGENTS.md", age=dt.timedelta(days=30))
    _write(tmp_path / ".dadaia" / "reports" / "README.md", age=dt.timedelta(days=30))
    stale_sibling = _write(
        tmp_path / ".dadaia" / "handoff" / "ctx" / "stale.handoff.json",
        age=dt.timedelta(days=30),
    )

    service = LifecycleHygieneService(tmp_path, now=NOW)
    result = service.cleanup(dry_run=True)

    by_path = {c.path: c for c in result.candidates}
    for doc in (".dadaia/handoff/AGENTS.md", ".dadaia/tmp/AGENTS.md"):
        assert by_path[doc].protected is True, by_path[doc]
        assert by_path[doc].protection_kind is not None
        assert by_path[doc].protection_kind.value == "canonical_zone_doc"
    assert by_path[".dadaia/handoff/ctx/stale.handoff.json"].protected is False

    # The FR3 preflight arithmetic: only the stale sibling counts as unprotected.
    counters = service.status()
    assert counters.cleanup_candidate_count - counters.protected_residual_count == 1

    # clean --apply never deletes the canonical docs.
    service.cleanup(dry_run=False)
    assert agents_handoff.exists()
    assert agents_tmp.exists()
    assert not stale_sibling.exists()
