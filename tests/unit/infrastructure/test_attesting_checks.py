"""RED tests — attesting checks can never vanish silently (Class 3).

Bug class: an attesting check (first seen in the since-deleted rule-corpus check) emitted
``[ok]`` only when it FOUND objects and nothing at all when the checked universe was empty — a vanished check is
indistinguishable from a green one. The contract now: an ATTESTING check always speaks:
pass, fail, or an explicit ``[not-applicable] check:<id>`` line.
"""

from __future__ import annotations

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus, attest


def test_attest_stamps_not_applicable_on_empty_result() -> None:
    stamped = attest("symlink-target", [])
    assert [line.render() for line in stamped] == [
        "[not-applicable] check:symlink-target — no applicable objects"
    ]


def test_attest_passes_through_nonempty_results() -> None:
    lines = [DoctorLine(DoctorStatus.OK, "symlink-target:.claude/agents")]
    assert attest("symlink-target", lines) == lines
