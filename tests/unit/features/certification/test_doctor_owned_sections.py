"""`certify`'s doctor check judges the sections it claims to judge.

The check reads `dadaia doctor --json` and passes when `specs` and `ledgers` carry no
findings. Reading them with `if name in sections` made a RENAMED or ABSENT section an
automatic PASS: the payload it never saw could not report a finding, so the verdict
"specs and ledgers sections clean" was a statement about nothing.

Intent: CONTRACT — 0.4.7 candidate 8 review F4. Size: SMALL.
"""

from __future__ import annotations

import json

import pytest

from dadaia_workspace.features.certification.service import _owned_doctor_sections_clean


def _payload(sections: dict[str, object]) -> str:
    return json.dumps({"sections": sections})


def test_both_owned_sections_present_and_empty_is_the_clean_verdict() -> None:
    verdict = _owned_doctor_sections_clean(
        _payload({"specs": {"findings": []}, "ledgers": {"findings": []}, "workspace": {}})
    )

    assert verdict == "specs and ledgers sections clean"


@pytest.mark.parametrize("missing", ["specs", "ledgers"])
def test_a_missing_owned_section_fails_and_names_it(missing: str) -> None:
    sections = {"specs": {"findings": []}, "ledgers": {"findings": []}}
    del sections[missing]

    with pytest.raises(RuntimeError) as err:
        _owned_doctor_sections_clean(_payload(sections))

    assert missing in str(err.value)


def test_a_finding_in_an_owned_section_still_fails() -> None:
    with pytest.raises(RuntimeError, match="doctor not clean"):
        _owned_doctor_sections_clean(
            _payload({"specs": {"findings": ["SPEC-DOC-001"]}, "ledgers": {"findings": []}})
        )
