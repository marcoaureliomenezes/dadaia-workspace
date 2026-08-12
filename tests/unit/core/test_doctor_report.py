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


class TestControlCharacterEscaping:
    """FR3 item 2 (CWE-117): a producer's ``text`` must never be able to forge a second
    physical line through an embedded control character. Fixed at the ONE rendering
    authority, ``DoctorLine.render()`` — through which ``DoctorReport.rendered()`` and
    every golden already pass.
    """

    def test_embedded_newline_cannot_forge_a_second_physical_line(self) -> None:
        line = DoctorLine(DoctorStatus.OK, "x\n[ok] forged")
        rendered = line.render()
        assert "\n" not in rendered
        assert rendered.count("\n") == 0
        # exactly one physical line
        assert len(rendered.splitlines()) == 1
        assert rendered == "[ok] x\\n[ok] forged"

    def test_embedded_carriage_return_is_escaped(self) -> None:
        rendered = DoctorLine(DoctorStatus.WARN, "a\rb").render()
        assert "\r" not in rendered
        assert rendered == "[warn] a\\rb"

    def test_embedded_escape_char_is_escaped(self) -> None:
        rendered = DoctorLine(DoctorStatus.ERROR, "a\x1bb").render()
        assert "\x1b" not in rendered
        assert rendered == "[error] a\\x1bb"

    def test_full_c0_range_is_escaped(self) -> None:
        """Prefer escaping the full C0 range (0x00-0x1F), not just \\n/\\r/ESC."""
        for code in range(0x20):
            ch = chr(code)
            rendered = DoctorLine(DoctorStatus.INFO, f"a{ch}b").render()
            assert ch not in rendered, f"control char 0x{code:02x} survived escaping"
            assert len(rendered.splitlines()) == 1

    def test_clean_text_is_a_no_op(self) -> None:
        """Escaping must be a NO-OP on clean text — committed goldens carry no control
        characters, so this change must never move a clean golden line."""
        assert DoctorLine(DoctorStatus.OK, "public-privacy").render() == "[ok] public-privacy"
        assert (
            DoctorLine(DoctorStatus.ERROR, "x: contains 'y'").render() == "[error] x: contains 'y'"
        )
        assert (
            DoctorLine(DoctorStatus.NOT_APPLICABLE, "path/with/slashes.md — note").render()
            == "[not-applicable] path/with/slashes.md — note"
        )

    def test_doctor_report_rendered_never_yields_extra_lines(self) -> None:
        """``DoctorReport.rendered()`` returns exactly one string per DoctorLine, even
        when a line's text carries embedded newlines."""
        report = DoctorReport(
            lines=(
                DoctorLine(DoctorStatus.OK, "clean"),
                DoctorLine(DoctorStatus.ERROR, "forged\n[ok] injected"),
            )
        )
        rendered = report.rendered()
        assert len(rendered) == 2
        assert all(len(line.splitlines()) == 1 for line in rendered)
