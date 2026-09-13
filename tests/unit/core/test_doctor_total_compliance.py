"""One percent formula for the human total line and the `--json` total (0.4.7 FR5).

Intent: CONTRACT — T-047-02 / review F1: `dadaia doctor`'s human `compliance(total)`
line and its `--json` `compliance.percent` are rendered from ONE scorer, so they can
never disagree at a denominator that rounds up (1055/1056 floors to 99, rounds to 100).
Size: SMALL — pure function calls over hand-built SectionReports; no I/O, no runner.
"""

from __future__ import annotations

import json
import re

from dadaia_workspace.cli.commands.doctor import _json_payload
from dadaia_workspace.core.doctor_rules import SectionReport, total_compliance, total_line

_PERCENT_RE = re.compile(r"\((\d+)%\)$")


def _reports() -> list[SectionReport]:
    """A run whose summed score is 1055/1056 — the instance's live denominator with one
    non-canonical entry: floor says 99 %, round says 100 %."""
    return [
        SectionReport(name="workspace", unit="entries", findings=(), canonical=214, total=215),
        SectionReport(name="specs", unit="rules", findings=(), canonical=41, total=41),
        SectionReport(name="ledgers", unit="records", findings=(), canonical=800, total=800),
    ]


def test_total_compliance_floors_like_every_section_line() -> None:
    total = total_compliance(_reports())
    assert (total.canonical, total.total, total.percent) == (1055, 1056, 99)
    assert total.score_line() == "compliance(total): 1055/1056 checks canonical (99%)"


def test_json_total_percent_equals_the_human_total_line() -> None:
    reports = _reports()
    payload = json.loads(_json_payload(reports, [], str, None))
    human = _PERCENT_RE.search(total_line(reports))
    assert human is not None
    assert payload["compliance"]["percent"] == int(human.group(1)) == 99


def test_json_section_percent_comes_from_the_section_report() -> None:
    reports = _reports()
    payload = json.loads(_json_payload(reports, [], str, None))
    assert payload["sections"]["workspace"]["compliance"]["percent"] == reports[0].percent == 99
