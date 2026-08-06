"""v0.2.8 (consumer-gate bug class) — audit step prompt contract alignment.

The collapsed audit step prompt is fragment + persona. The project-auditor persona once
instructed a COMPETING output envelope (six-dimension compliance scorecard, drift
inventory, recommended actions) while the Python gate validates the FRAGMENT's
``audit-report-v1`` shape — the worker followed the persona and the gate rejected
(intermittently, per model coin-flip). This file locks the fix: the persona defers to
the fragment's contract, and the fragment pins the required finding keys with an
explicit no-substitutes clause.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[4] / "dadaia_workspace" / "public"


def test_project_auditor_persona_defers_output_contract_to_fragment() -> None:
    body = (_PUBLIC / "personas" / "project-auditor.md").read_text(encoding="utf-8")
    # The old competing envelope instruction is gone…
    assert "an audit report carrying the scope" not in body
    # …and the persona explicitly defers to the step fragment's JSON contract.
    assert "fragment owns the JSON contract" in body
    assert "never emit them as a competing" in body


def test_audit_report_fragment_pins_required_finding_keys() -> None:
    body = (_PUBLIC / "lifecycle_fragments" / "audit" / "audit-report.md").read_text(
        encoding="utf-8"
    )
    assert "Every finding MUST carry exactly the keys `id`, `severity`, `lens`, `summary`," in body
    assert "never emit them as replacement keys" in body
