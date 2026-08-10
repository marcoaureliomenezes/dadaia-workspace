"""Contract tests for the typed doctor report — the frozen blocking table.

The blocking policy is the heart of the fail-closed design: every status decides its
verdict at declaration. This table is PINNED — a change to it must show up as a diff in
this file (a reviewed decision), never as an accidental side effect elsewhere.
"""

from __future__ import annotations

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorReport, DoctorStatus

#: The frozen verdict table. FOREIGN is non-blocking by Ruling 16 (hand-authored
#: consumer guardrail pairs are legitimate); EXTRA blocks (residue on a managed
#: surface is drift). Changing ANY entry is a policy decision — update this test
#: deliberately, in its own reviewed diff.
_EXPECTED_BLOCKING: dict[DoctorStatus, bool] = {
    DoctorStatus.OK: False,
    DoctorStatus.DRIFT: True,
    DoctorStatus.MISSING: True,
    DoctorStatus.ERROR: True,
    DoctorStatus.WARN: False,
    DoctorStatus.INFO: False,
    DoctorStatus.FOREIGN: False,
    DoctorStatus.EXTRA: True,
    DoctorStatus.LEAK: True,
    DoctorStatus.UNSUPPORTED: False,
    DoctorStatus.NOT_APPLICABLE: False,
    DoctorStatus.SKIP: False,
    DoctorStatus.PRUNE: False,
    DoctorStatus.RM: False,
}


def test_blocking_table_is_total_and_pinned() -> None:
    """EVERY status has a pinned verdict — no member may exist without one."""
    assert set(_EXPECTED_BLOCKING) == set(DoctorStatus), (
        "a DoctorStatus member is missing from the pinned verdict table — decide its "
        "blocking-ness HERE, in a reviewed diff, before shipping it"
    )
    for status, expected in _EXPECTED_BLOCKING.items():
        assert status.blocking is expected, (
            f"{status!r}.blocking changed from the pinned table — if deliberate, "
            "update _EXPECTED_BLOCKING in its own reviewed diff"
        )


def test_render_reproduces_legacy_wire_format() -> None:
    """``render()`` is byte-identical to the historical ``[prefix] text`` lines."""
    assert DoctorLine(DoctorStatus.OK, "public-privacy").render() == "[ok] public-privacy"
    assert (
        DoctorLine(DoctorStatus.NOT_APPLICABLE, "git-dirty check (not a git repo)").render()
        == "[not-applicable] git-dirty check (not a git repo)"
    )
    assert DoctorLine(DoctorStatus.ERROR, "x: contains 'y'").render() == "[error] x: contains 'y'"


def test_report_verdict_is_any_blocking_line() -> None:
    ok = DoctorLine(DoctorStatus.OK, "a")
    warn = DoctorLine(DoctorStatus.WARN, "b")
    err = DoctorLine(DoctorStatus.ERROR, "c")
    assert DoctorReport(lines=(ok, warn)).blocking is False
    assert DoctorReport(lines=(ok, err)).blocking is True
    assert DoctorReport(lines=()).blocking is False
    assert DoctorReport(lines=(ok, err)).rendered() == ["[ok] a", "[error] c"]
