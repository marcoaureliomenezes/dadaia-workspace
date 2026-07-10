"""Unit tests for the DoctorService EFF-1 efficiency-audit staleness check (v0.1.60 FR7).

EFF-1 rides the EXISTING workspace-doctor ``DoctorIssue`` abstraction (Rulings 10/11): a
``DoctorIssue(code="EFF-1", fixable=False, description=<staleness age + clearing command>)``,
NOT a ``[warn]`` token, and the bare ``dadaia doctor`` exit stays 0 (the service never raises
on issues). 4-case matrix over ``.dadaia/states/last_efficiency_audit.json``:

  * *absent*    ⇒ NO issue (fresh-workspace happy path unchanged — this is what keeps every
                  existing `dadaia doctor` happy-path test green).
  * *fresh*     (≤ ``EFFICIENCY_AUDIT_STALE_DAYS``) ⇒ no issue.
  * *stale*     (> threshold) ⇒ EFF-1.
  * *malformed* (invalid JSON / missing field / unparseable timestamp) ⇒ EFF-1 "malformed
                marker", NEVER a crash.

RED-first: before FR7 there was no ``DoctorService`` staleness check at all. Mutation-sanity
AC-11(e): making ``check()`` skip ``_check_efficiency_audit`` makes
:func:`test_stale_marker_emits_eff1_through_check` FAIL — the discriminating proof the wiring
is real. The stale/malformed assertions go through the full ``check()`` aggregator (not the
private helper) so that sabotage is falsifiable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("fcntl")

from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context.doctor import (  # noqa: E402
    EFFICIENCY_AUDIT_STALE_DAYS,
    DoctorService,
)
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402


def _init_workspace(root: Path) -> None:
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text('{"schema_version": "2", "contexts": []}')
    (root / "repos").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# agents")


def _doctor(root: Path) -> DoctorService:
    return DoctorService(FakeContextStore(), FakeGitClient(), root)


def _write_marker(root: Path, content: str) -> None:
    (root / ".dadaia" / "states" / "last_efficiency_audit.json").write_text(
        content, encoding="utf-8"
    )


def _marker_json(recorded: datetime) -> str:
    return json.dumps(
        {
            "schema_version": "1",
            "last_efficiency_audit": recorded.isoformat().replace("+00:00", "Z"),
            "by": "ai-engineer",
            "report": ".dadaia/reports/x/efficiency.html",
        }
    )


def _eff1(root: Path) -> list[str]:
    return [i.description for i in _doctor(root).check() if i.code == "EFF-1"]


@pytest.mark.parametrize(
    "marker_content",
    [
        pytest.param(None, id="absent-marker-no-eff1"),
        pytest.param(lambda: _marker_json(datetime.now(tz=UTC)), id="fresh-marker-no-eff1"),
        pytest.param(
            lambda: _marker_json(datetime.now(tz=UTC) - timedelta(days=29)),
            id="boundary-at-threshold-no-eff1",
        ),
    ],
)
def test_no_eff1_matrix(tmp_path: Path, marker_content) -> None:  # type: ignore[no-untyped-def]
    """Absent, fresh, and at-threshold (≤30d) markers all emit no EFF-1."""
    _init_workspace(tmp_path)
    if marker_content is not None:
        _write_marker(tmp_path, marker_content())
    assert _eff1(tmp_path) == []


def test_stale_marker_emits_eff1_and_is_manual_not_fixable(tmp_path: Path) -> None:
    """*stale* (> 30d) ⇒ EFF-1 with the staleness age + clearing command (AC-11(e) target),
    and the issue is a manual (non-auto-fixable) issue — rendered '[manual]' by the CLI."""
    _init_workspace(tmp_path)
    _write_marker(tmp_path, _marker_json(datetime.now(tz=UTC) - timedelta(days=45)))
    descriptions = _eff1(tmp_path)
    assert len(descriptions) == 1, descriptions
    desc = descriptions[0]
    assert "45 day" in desc
    assert f"threshold {EFFICIENCY_AUDIT_STALE_DAYS}d" in desc
    assert "dadaia reports mark-efficiency-audit" in desc

    eff1_issues = [i for i in _doctor(tmp_path).check() if i.code == "EFF-1"]
    assert eff1_issues and all(i.fixable is False for i in eff1_issues)


@pytest.mark.parametrize(
    "marker_content",
    [
        pytest.param("{not valid json", id="invalid-json"),
        pytest.param(
            json.dumps({"schema_version": "1", "by": "x"}), id="missing-last-efficiency-audit-field"
        ),
        pytest.param(
            json.dumps({"schema_version": "1", "last_efficiency_audit": "not-a-date"}),
            id="unparseable-timestamp",
        ),
    ],
)
def test_malformed_marker_matrix(tmp_path: Path, marker_content: str) -> None:
    """Every malformed-marker shape ⇒ EFF-1 'malformed marker', NEVER a crash."""
    _init_workspace(tmp_path)
    _write_marker(tmp_path, marker_content)
    descriptions = _eff1(tmp_path)
    assert len(descriptions) == 1 and "malformed" in descriptions[0]
