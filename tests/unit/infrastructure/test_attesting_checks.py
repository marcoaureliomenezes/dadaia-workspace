"""RED tests — attesting checks can never vanish silently (Class 3).

Bug class: ``check_codex_rule_corpus_reachable`` emitted ``[ok]`` only when it FOUND
citations and nothing at all when the checked universe was empty — a vanished check is
indistinguishable from a green one. The contract now: an ATTESTING check always speaks:
pass, fail, or an explicit ``[not-applicable] check:<id>`` line.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus, attest
from dadaia_workspace.infrastructure.codex_doctor import (
    ATTESTING_CHECK_IDS,
    check_codex_rule_corpus_reachable,
)


def test_attest_stamps_not_applicable_on_empty_result() -> None:
    stamped = attest("rule-corpus", [])
    assert [line.render() for line in stamped] == [
        "[not-applicable] check:rule-corpus — no applicable objects"
    ]


def test_attest_passes_through_nonempty_results() -> None:
    lines = [DoctorLine(DoctorStatus.OK, "codex:rule-corpus-reachable (WS-CDX-PROTOCOL)")]
    assert attest("rule-corpus", lines) == lines


def test_rule_corpus_check_speaks_on_empty_universe(tmp_path: Path) -> None:
    """Zero codex artifacts (no .codex/agents) ⇒ the check STILL yields a line.

    This is the exact silence that buried the check when the last by-name rule
    citation was consolidated into DADAIA.md.
    """
    lines = attest("rule-corpus", check_codex_rule_corpus_reachable(tmp_path))
    assert lines, "an attesting check must never contribute zero lines"
    assert all(
        line.status in {DoctorStatus.OK, DoctorStatus.ERROR, DoctorStatus.NOT_APPLICABLE}
        for line in lines
    )


def test_attesting_registry_is_pinned() -> None:
    """The attesting-check roster is a declared, reviewed set — removing an entry is a
    deliberate diff here, never an accidental vanishing."""
    assert ATTESTING_CHECK_IDS == (
        "rule-corpus",
        "trust-boundary",
        "public-privacy",
        "law-projection",
        "entities-derivation",
        "foreign-projections",
    )


def test_golden_never_buries_an_attesting_check() -> None:
    """Regen governance: every attesting check is PRESENT in the committed all-four
    doctor golden — as its positive line or its explicit not-applicable stamp. An
    UPDATE_INSTALL_GOLDENS regen that dropped a check entirely fails here, so
    indiscriminate regeneration cannot bury a verifier."""
    import json

    golden = (Path(__file__).parent / "_golden" / "doctor_all_four_v0158.json").read_text(
        encoding="utf-8"
    )
    lines = json.loads(golden)
    text = "\n".join(lines)
    markers = {
        "rule-corpus": ("codex:rule-corpus", "check:rule-corpus"),
        "trust-boundary": ("codex:trust-boundary", "check:trust-boundary"),
        "public-privacy": ("public-privacy", "check:public-privacy"),
        "law-projection": ("law:", "check:law-projection"),
        "entities-derivation": ("entities-derivation", "check:entities-derivation"),
        "foreign-projections": ("ledger:foreign-scan", "check:foreign-projections"),
    }
    for check_id in ATTESTING_CHECK_IDS:
        assert any(m in text for m in markers[check_id]), (
            f"attesting check '{check_id}' is absent from the doctor golden — a regen "
            "buried a verifier; restore the check or retire it in a reviewed diff"
        )
